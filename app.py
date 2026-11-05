from datetime import date
from pathlib import Path

import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from src.audit import audit_crm


st.set_page_config(page_title="GTM AI Readiness Auditor", page_icon="📊", layout="wide")

st.title("GTM AI Readiness Auditor")
st.caption("A transparent CRM-data health check for AI-assisted sales, RevOps and account-intelligence workflows.")

st.info(
    "This portfolio project uses configurable heuristic rules, not a universal industry benchmark. "
    "The score is intended to make data-quality trade-offs visible and explainable."
)

sample_path = Path(__file__).parent / "data" / "sample_crm.csv"

with st.sidebar:
    st.header("Data source")
    uploaded = st.file_uploader("Upload a CRM/account CSV", type=["csv"])
    st.caption("No uploaded data is stored by the app code.")

if uploaded is not None:
    data = pd.read_csv(uploaded)
    source_label = uploaded.name
    reference_date = None
else:
    data = pd.read_csv(sample_path)
    source_label = "Bundled synthetic sample"
    # Keep the bundled demo reproducible instead of letting its recency score
    # drift as the real-world calendar advances.
    reference_date = date(2026, 11, 4)

expected_fields = {
    "account_name",
    "domain",
    "industry",
    "country",
    "lifecycle_stage",
    "owner",
    "last_activity_date",
    "source",
}
missing = sorted(expected_fields - set(c.strip().lower() for c in data.columns))
if missing:
    st.warning("Missing expected fields will reduce the completeness score: " + ", ".join(missing))

result = audit_crm(data, today=reference_date)

st.subheader("Readiness snapshot")

if result.overall_score >= 90:
    readiness_band = "Strong foundation"
elif result.overall_score >= 75:
    readiness_band = "Needs cleanup"
elif result.overall_score >= 60:
    readiness_band = "At risk"
else:
    readiness_band = "Not ready"

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Overall readiness",
    f"{result.overall_score:.1f}/100",
    delta=readiness_band,
    delta_color="off",
    border=True,
)
col2.metric("Records", result.summary["records"], border=True)
col3.metric("Duplicate records", result.summary["duplicate_records"], border=True)
col4.metric("Stale records", result.summary["stale_records"], border=True)

st.progress(min(max(result.overall_score / 100, 0.0), 1.0))
if reference_date is not None:
    st.caption(f"Source: {source_label} · Demo reference date: {reference_date.isoformat()}")
else:
    st.caption(f"Source: {source_label}")

st.subheader("Dimension scores")
score_df = pd.DataFrame(
    {
        "Dimension": list(result.dimension_scores.keys()),
        "Score": list(result.dimension_scores.values()),
    }
)
score_chart = go.Figure(
    go.Bar(
        x=score_df["Score"],
        y=score_df["Dimension"],
        orientation="h",
        hovertemplate="%{y}: %{x:.1f}<extra></extra>",
    )
)

score_chart.update_layout(
    height=330,
    margin=dict(l=10, r=20, t=10, b=10),
    showlegend=False,
    dragmode="zoom",
)

score_chart.update_xaxes(
    title="Score (0–100)",
    range=[0, 100],
    minallowed=0,
    maxallowed=100,
    fixedrange=False,
    dtick=20,
)

score_chart.update_yaxes(
    title=None,
    autorange="reversed",
    fixedrange=True,
)

st.plotly_chart(
    score_chart,
    width="stretch",
    config={
        "scrollZoom": True,
        "displaylogo": False,
    },
    alt="Horizontal bar chart showing the five GTM readiness dimension scores on a 0 to 100 scale.",
)

st.caption(
    "Mouse-wheel zoom is enabled, but the score axis is constrained to the valid 0–100 range. "
    "Use Plotly's reset control to return to the full view."
)

st.subheader("What should RevOps fix first — and why?")
st.caption(
    "Priorities are based on downstream operational impact, not only on record count. "
    "P1 issues can directly break entity matching, ownership, routing or account-level reporting."
)

if result.fix_first.empty:
    st.success("No operational priorities were triggered by the current rules.")
else:
    st.dataframe(
        result.fix_first,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Priority": st.column_config.TextColumn(width="small"),
            "Fix first": st.column_config.TextColumn(width="medium"),
            "Affected records": st.column_config.NumberColumn(width="small"),
            "Business risk": st.column_config.TextColumn(width="medium"),
            "Why it matters": st.column_config.TextColumn(width="large"),
            "Recommended action": st.column_config.TextColumn(width="large"),
        },
    )

left, right = st.columns([1, 1])
with left:
    st.subheader("Executive recommendations")
    for recommendation in result.recommendations:
        st.write(f"• {recommendation}")

with right:
    st.subheader("Operational flags")
    st.write(f"**Invalid/nonstandard stages:** {result.summary['records_with_invalid_stage']}")
    st.write(f"**Nonstandard country values:** {result.summary['records_with_nonstandard_country']}")
    st.write(f"**Stale or missing activity:** {result.summary['stale_records']}")
    st.write(f"**Duplicate records:** {result.summary['duplicate_records']}")

st.subheader("Detailed issue register")
if result.issues.empty:
    st.success("No issues were detected by the current rules.")
else:
    st.dataframe(result.issues, use_container_width=True, hide_index=True)

st.subheader("Audited data")
st.dataframe(result.audited_data, use_container_width=True, hide_index=True)

st.download_button(
    "Download audited CSV",
    data=result.audited_data.to_csv(index=False).encode("utf-8"),
    file_name="gtm_audited_accounts.csv",
    mime="text/csv",
)

with st.expander("How the score works"):
    st.markdown(
        """
The overall score is a weighted combination of five transparent dimensions:

- **Completeness — 30%:** presence of core account fields.
- **Duplicate control — 20%:** duplicate domains or account names reduce the score.
- **Standardization — 20%:** domain syntax, lifecycle stages and country values.
- **Recency — 15%:** activity within 90 days scores highest; 91–180 days scores partially; older or missing activity scores zero.
- **Segmentation readiness — 15%:** availability of firmographic and prioritization fields such as employee count, revenue, account tier, fit score and intent signal.

The weights are deliberately simple and documented. A real implementation should adapt them to the organization's GTM process, CRM governance and risk tolerance.
        """
    )
