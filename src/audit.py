from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Dict, List

import pandas as pd


REQUIRED_FIELDS = [
    "account_name",
    "domain",
    "industry",
    "country",
    "lifecycle_stage",
    "owner",
    "last_activity_date",
    "source",
]

SEGMENTATION_FIELDS = [
    "employee_count",
    "annual_revenue_usd",
    "account_tier",
    "fit_score",
    "intent_signal",
]

VALID_STAGES = {
    "prospect",
    "marketing qualified",
    "sales qualified",
    "opportunity",
    "customer",
    "inactive",
}

STANDARD_COUNTRIES = {
    "canada",
    "united states",
    "united kingdom",
    "germany",
    "france",
    "netherlands",
    "poland",
    "ukraine",
    "australia",
    "singapore",
}

DOMAIN_RE = re.compile(r"^(?!-)(?:[a-z0-9-]+\.)+[a-z]{2,}$", re.IGNORECASE)


@dataclass
class AuditResult:
    overall_score: float
    dimension_scores: Dict[str, float]
    summary: Dict[str, int]
    issues: pd.DataFrame
    fix_first: pd.DataFrame
    audited_data: pd.DataFrame
    recommendations: List[str]


def _text_present(series: pd.Series) -> pd.Series:
    return series.notna() & series.astype(str).str.strip().ne("")


def _safe_col(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df.columns:
        return df[name]
    return pd.Series([pd.NA] * len(df), index=df.index, dtype="object")


def _score_completeness(df: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    checks = pd.DataFrame(index=df.index)
    for field in REQUIRED_FIELDS:
        checks[field] = _text_present(_safe_col(df, field))
    return float(checks.mean(axis=1).mean() * 100) if len(df) else 0.0, checks


def _score_duplicates(df: pd.DataFrame) -> tuple[float, pd.Series, pd.Series]:
    domains = _safe_col(df, "domain").fillna("").astype(str).str.strip().str.lower()
    names = _safe_col(df, "account_name").fillna("").astype(str).str.strip().str.lower()
    dup_domain = domains.ne("") & domains.duplicated(keep=False)
    dup_name = names.ne("") & names.duplicated(keep=False)
    dup_any = dup_domain | dup_name
    score = (1 - dup_any.mean()) * 100 if len(df) else 0.0
    return float(max(0, score)), dup_domain, dup_name


def _score_standardization(df: pd.DataFrame) -> tuple[float, pd.Series, pd.Series, pd.Series]:
    domain = _safe_col(df, "domain").fillna("").astype(str).str.strip().str.lower()
    stage = _safe_col(df, "lifecycle_stage").fillna("").astype(str).str.strip().str.lower()
    country = _safe_col(df, "country").fillna("").astype(str).str.strip().str.lower()

    valid_domain = domain.apply(lambda x: bool(DOMAIN_RE.match(x)) if x else False)
    valid_stage = stage.isin(VALID_STAGES)
    valid_country = country.isin(STANDARD_COUNTRIES)

    checks = pd.concat([valid_domain, valid_stage, valid_country], axis=1)
    checks.columns = ["domain", "lifecycle_stage", "country"]
    score = checks.mean(axis=1).mean() * 100 if len(df) else 0.0
    return float(score), valid_domain, valid_stage, valid_country


def _score_recency(df: pd.DataFrame, today: date | None = None) -> tuple[float, pd.Series, pd.Series]:
    today = today or date.today()
    parsed = pd.to_datetime(_safe_col(df, "last_activity_date"), errors="coerce")
    age_days = (pd.Timestamp(today) - parsed).dt.days

    row_score = pd.Series(0.0, index=df.index)
    row_score.loc[age_days <= 90] = 100.0
    row_score.loc[(age_days > 90) & (age_days <= 180)] = 50.0
    stale = age_days.gt(180) | parsed.isna()
    return float(row_score.mean()) if len(df) else 0.0, stale, age_days


def _score_segmentation(df: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    checks = pd.DataFrame(index=df.index)
    for field in SEGMENTATION_FIELDS:
        checks[field] = _text_present(_safe_col(df, field))
    return float(checks.mean(axis=1).mean() * 100) if len(df) else 0.0, checks


def audit_crm(df: pd.DataFrame, today: date | None = None) -> AuditResult:
    """Audit a CRM/account table for illustrative GTM data-readiness signals.

    The score is a transparent portfolio/demo heuristic, not an industry standard.
    """
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    completeness, completeness_checks = _score_completeness(df)
    duplicate_score, dup_domain, dup_name = _score_duplicates(df)
    standardization, valid_domain, valid_stage, valid_country = _score_standardization(df)
    recency, stale, age_days = _score_recency(df, today=today)
    segmentation, segmentation_checks = _score_segmentation(df)

    dimension_scores = {
        "Completeness": round(completeness, 1),
        "Duplicate control": round(duplicate_score, 1),
        "Standardization": round(standardization, 1),
        "Recency": round(recency, 1),
        "Segmentation readiness": round(segmentation, 1),
    }

    weights = {
        "Completeness": 0.30,
        "Duplicate control": 0.20,
        "Standardization": 0.20,
        "Recency": 0.15,
        "Segmentation readiness": 0.15,
    }
    overall = sum(dimension_scores[k] * weights[k] for k in weights)

    audited = df.copy()
    audited["issue_duplicate_domain"] = dup_domain
    audited["issue_duplicate_name"] = dup_name
    audited["issue_invalid_domain"] = ~valid_domain
    audited["issue_invalid_stage"] = ~valid_stage
    audited["issue_nonstandard_country"] = ~valid_country
    audited["issue_stale_or_missing_activity"] = stale
    audited["activity_age_days"] = age_days
    audited["required_fields_present_pct"] = completeness_checks.mean(axis=1).mul(100).round(0)
    audited["segmentation_fields_present_pct"] = segmentation_checks.mean(axis=1).mul(100).round(0)

    issue_rows = []

    def add_issue(mask: pd.Series, issue: str, field: str, priority: str) -> None:
        for idx in df.index[mask.fillna(False)]:
            issue_rows.append({
                "row": int(idx) + 2,
                "account_name": _safe_col(df, "account_name").loc[idx],
                "field": field,
                "issue": issue,
                "priority": priority,
            })

    add_issue(dup_domain, "Duplicate domain", "domain", "High")
    add_issue(dup_name, "Duplicate account name", "account_name", "Medium")
    add_issue(~valid_domain, "Missing or invalid domain", "domain", "High")
    add_issue(~valid_stage, "Missing or nonstandard lifecycle stage", "lifecycle_stage", "Medium")
    add_issue(~valid_country, "Missing or nonstandard country value", "country", "Medium")
    add_issue(stale, "Activity is older than 180 days or missing", "last_activity_date", "Medium")

    for field in REQUIRED_FIELDS:
        mask = ~_text_present(_safe_col(df, field))
        if field not in {"domain", "lifecycle_stage", "country", "last_activity_date"}:
            add_issue(mask, f"Missing required field: {field}", field, "High" if field == "owner" else "Medium")

    issues = pd.DataFrame(issue_rows)
    if not issues.empty:
        priority_order = pd.Categorical(issues["priority"], categories=["High", "Medium", "Low"], ordered=True)
        issues = (
            issues.assign(_priority_order=priority_order)
            .sort_values(["_priority_order", "row"])
            .drop(columns="_priority_order")
        )

    summary = {
        "records": len(df),
        "duplicate_records": int((dup_domain | dup_name).sum()),
        "stale_records": int(stale.sum()),
        "records_with_invalid_stage": int((~valid_stage).sum()),
        "records_with_nonstandard_country": int((~valid_country).sum()),
    }

    recommendations: List[str] = []
    if completeness < 90:
        recommendations.append("Raise completion of core account fields before adding enrichment or AI-assisted research workflows.")
    if duplicate_score < 95:
        recommendations.append("Deduplicate accounts using domain as the primary key and review duplicate account names before routing or scoring.")
    if standardization < 90:
        recommendations.append("Normalize lifecycle stages, country values and domain formatting so filters, routing and reporting behave consistently.")
    if recency < 80:
        recommendations.append("Define a stale-account rule and refresh or archive records with no meaningful activity in the last 180 days.")
    if segmentation < 80:
        recommendations.append("Improve firmographic and prioritization fields before relying on automated ICP scoring, personalization or account tiering.")
    if not recommendations:
        recommendations.append("Core data quality is strong; next evaluate governance, enrichment sources and how scoring decisions are monitored over time.")

    # RevOps-oriented fix-first queue. These are operational priorities rather than
    # additional scoring dimensions: the aim is to explain what could break downstream.
    queue = []

    def add_fix(priority, issue, affected, business_risk, why, action):
        if affected:
            queue.append({
                "Priority": priority,
                "Fix first": issue,
                "Affected records": int(affected),
                "Business risk": business_risk,
                "Why it matters": why,
                "Recommended action": action,
            })

    missing_domain = int((~valid_domain).sum())
    missing_owner = int((~_text_present(_safe_col(df, "owner"))).sum())
    missing_source = int((~_text_present(_safe_col(df, "source"))).sum())
    seg_incomplete = int((segmentation_checks.mean(axis=1) < 1.0).sum())

    add_fix(
        "P1",
        "Duplicate accounts/domains",
        int((dup_domain | dup_name).sum()),
        "Routing, attribution and reporting",
        "The same company can be scored, assigned or reported more than once, fragmenting activity and pipeline visibility.",
        "Merge or deduplicate records; use normalized domain as the primary entity key and preserve the surviving account history.",
    )
    add_fix(
        "P1",
        "Missing or invalid domains",
        missing_domain,
        "Enrichment and account matching",
        "Domain is often the most reliable key for enrichment, entity resolution and account-level signal matching.",
        "Recover and normalize domains before enrichment, scoring or account-signal ingestion.",
    )
    add_fix(
        "P1",
        "Missing account owner",
        missing_owner,
        "Lead/account routing and accountability",
        "Unowned records can fall outside SLAs, sequencing and territory accountability.",
        "Assign owners and review routing rules so every in-scope account has a clear owner.",
    )
    add_fix(
        "P2",
        "Nonstandard lifecycle stages",
        int((~valid_stage).sum()),
        "Funnel reporting and automation",
        "Inconsistent stages can break funnel metrics, trigger logic and handoffs between marketing and sales.",
        "Map values to one controlled lifecycle vocabulary and enforce it at entry/import.",
    )
    add_fix(
        "P2",
        "Stale or missing activity",
        int(stale.sum()),
        "Prioritization and pipeline hygiene",
        "Old activity can make dormant accounts look current and distort account-priority or next-best-action logic.",
        "Define a stale-account policy; refresh, recycle or archive records beyond the agreed inactivity threshold.",
    )
    add_fix(
        "P2",
        "Nonstandard country values",
        int((~valid_country).sum()),
        "Territory routing and segmentation",
        "Values such as UK, U.K. and CA can split one territory into several categories and create inconsistent routing/reporting.",
        "Normalize geography to one canonical vocabulary or ISO-based mapping.",
    )
    add_fix(
        "P2",
        "Incomplete segmentation fields",
        seg_incomplete,
        "ICP scoring and personalization",
        "Missing firmographic or prioritization fields weaken account tiering, segmentation and AI-assisted personalization.",
        "Backfill the specific fields used by the ICP model rather than enriching every possible attribute.",
    )
    add_fix(
        "P3",
        "Missing source attribution",
        missing_source,
        "Channel attribution and performance reporting",
        "Unknown acquisition source weakens campaign attribution and channel-performance analysis.",
        "Backfill source where possible and make source capture mandatory for new records.",
    )

    fix_first = pd.DataFrame(queue)
    if not fix_first.empty:
        priority_rank = {"P1": 1, "P2": 2, "P3": 3}
        fix_first["_rank"] = fix_first["Priority"].map(priority_rank)
        fix_first = (
            fix_first.sort_values(["_rank", "Affected records"], ascending=[True, False])
            .drop(columns="_rank")
            .reset_index(drop=True)
        )

    return AuditResult(
        overall_score=round(overall, 1),
        dimension_scores=dimension_scores,
        summary=summary,
        issues=issues,
        fix_first=fix_first,
        audited_data=audited,
        recommendations=recommendations,
    )
