# GTM AI Readiness Auditor

A small, explainable portfolio project that audits CRM/account data before it is used for AI-assisted sales, RevOps, account intelligence, routing or personalization.

The central idea is simple: **advanced GTM automation is only as reliable as the account data feeding it.**

## What it does

Upload a CRM-style CSV—or use the bundled synthetic sample—and the app evaluates five dimensions:

1. **Completeness** — are core account fields populated?
2. **Duplicate control** — are account names or domains duplicated?
3. **Standardization** — are domains, lifecycle stages and country values consistent?
4. **Recency** — is account activity current enough to support prioritization?
5. **Segmentation readiness** — are firmographic and prioritization fields available?

The result is a transparent **0–100 readiness score**, dimension-level scores, an issue register, prioritized recommendations and an audited CSV that can be downloaded.

## Why I built it

My background includes B2B business research, CRM/data management, reporting and sales-support work. I wanted to revisit that domain through a current RevOps/GTM lens without hiding the logic behind a black-box AI score.

This project focuses on the data-quality layer that precedes workflows such as enrichment, account scoring, routing, personalization and AI-assisted account research.

## Live demo

**[Open the GTM AI Readiness Auditor](https://gtm-ai-readiness-audit.streamlit.app/)**

The live Streamlit app opens with a bundled synthetic CRM sample and also accepts user-uploaded CSV files. It returns a readiness score, dimension-level diagnostics, a RevOps fix-first queue, executive recommendations, a detailed issue register and a downloadable audited CSV.

## Project status

**v1 complete.** The core audit, business-priority layer, interactive dashboard, synthetic sample data and live deployment are operational. Future additions are optional extensions rather than requirements for the portfolio version.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens with `data/sample_crm.csv`, a fully synthetic dataset containing intentional quality issues. You can also upload your own CSV using the same core schema.

## Sample schema

Core fields used by the audit:

- `account_name`
- `domain`
- `industry`
- `country`
- `lifecycle_stage`
- `owner`
- `source`
- `last_activity_date`

Optional segmentation/readiness fields:

- `employee_count`
- `annual_revenue_usd`
- `account_tier`
- `fit_score`
- `intent_signal`

## Scoring

| Dimension | Weight |
|---|---:|
| Completeness | 30% |
| Duplicate control | 20% |
| Standardization | 20% |
| Recency | 15% |
| Segmentation readiness | 15% |

The score is a **documented demo heuristic, not an industry benchmark**. See [docs/methodology.md](docs/methodology.md) for the exact logic and limitations.

## Example issues intentionally included in the sample

- duplicate account/domain
- missing owner
- missing domain
- nonstandard country values such as `UK` and `CA`
- nonstandard lifecycle stages such as `MQL` and `SQL`
- stale or missing activity dates
- incomplete firmographic/prioritization fields

## Project structure

```text
.
├── app.py
├── data/
│   └── sample_crm.csv
├── docs/
│   └── methodology.md
├── src/
│   ├── __init__.py
│   └── audit.py
├── requirements.txt
└── README.md
```

## Skills demonstrated

- CRM / RevOps data-quality thinking
- account and pipeline data auditing
- Python and pandas
- transparent scoring logic
- data validation and RevOps issue prioritization
- business-impact translation: what to fix first, why it matters and what action to take
- Streamlit dashboard development and deployment
- translating business-process requirements into reproducible rules

## Possible next extensions

The MVP intentionally stays small. Useful extensions could include:

- configurable scoring weights and lifecycle vocabularies;
- fuzzy account/entity matching;
- enrichment-source comparison;
- account-signal ingestion and a “why now?” score;
- CRM-specific mapping for Salesforce or HubSpot exports;
- a lightweight AI-generated executive summary grounded only in the audit results.

## Data

All data committed to this repository is synthetic and created for demonstration purposes.
