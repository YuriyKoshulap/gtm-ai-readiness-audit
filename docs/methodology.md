# Methodology

## What the score is

The **GTM AI Readiness Score** is a transparent portfolio/demo heuristic for evaluating whether account-level CRM data is in reasonable shape for workflows such as account prioritization, enrichment, routing, segmentation, reporting and AI-assisted research.

It is **not** an industry standard, maturity certification or prediction of business performance.

## Dimensions and weights

| Dimension | Weight | What it measures |
|---|---:|---|
| Completeness | 30% | Presence of core account fields needed for ownership, routing and research |
| Duplicate control | 20% | Duplicate domains and account names that can fragment activity and reporting |
| Standardization | 20% | Basic consistency of domains, lifecycle stages and country values |
| Recency | 15% | Whether account activity is recent enough to support prioritization |
| Segmentation readiness | 15% | Availability of firmographic and prioritization attributes |

## Why these dimensions

Modern sales and RevOps workflows often depend on account records being usable across several downstream steps: filtering, segmentation, enrichment, scoring, routing, personalization and reporting. Poor source data can make more advanced automation look sophisticated while producing unreliable outputs.

The project therefore starts with a deliberately simple question: **Is the underlying account data usable and explainable before we automate more of the GTM workflow?**

## Current rules

### Completeness
Checks these core fields:

- account name
- domain
- industry
- country
- lifecycle stage
- owner
- last activity date
- source

### Duplicate control
Flags duplicate:

- domains
- account names

In a production system, duplicate handling would normally involve stronger entity resolution and CRM-specific merge rules.

### Standardization
The demo checks:

- domain syntax
- lifecycle stage against a documented controlled vocabulary
- country value against a small standardized vocabulary used by the sample

### Recency
- 0–90 days since last activity: full credit
- 91–180 days: partial credit
- more than 180 days or missing: no credit

These thresholds are illustrative and should be configurable by sales cycle.

### Segmentation readiness
Checks whether the record contains:

- employee count
- annual revenue
- account tier
- fit score
- intent signal

These fields are examples rather than a prescribed ICP model.

## Design principle

The score is intentionally explainable. Every point deduction maps to a visible rule, and the audited output contains row-level flags so a user can trace a dashboard result back to individual records.

A future extension could add configurable YAML/JSON rules, CRM-specific schemas, enrichment, account-signal ingestion or an LLM-generated remediation summary. Those features are deliberately outside the MVP.
