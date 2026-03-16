# Roadmap

## v0.1 Documentation + Demo

Goal:

1. Define the product clearly
2. Ship repository skeleton
3. Include one working daily review demo

Deliverables:

1. README
2. System design docs
3. Open-source launch docs
4. `scripts/generate_daily_review.py`

## v0.2 Data Foundation

Goal:

1. Add a persistent local database
2. Store daily normalized market snapshots
3. Build daily market stats pipeline

Deliverables:

1. SQLite schema
2. `sync_day` pipeline
3. Stored daily snapshots
4. Stored daily market stats

## v0.3 Period Review

Goal:

1. Add 5-day / 10-day / 20-day review generation
2. Aggregate daily results into stage summaries

Deliverables:

1. Period review engine
2. Period markdown export
3. Period leader/theme ranking

## v0.4 Multi-Day Comparison

Goal:

1. Compare multiple days or ranges
2. Detect inflection points and regime changes

Deliverables:

1. Comparison engine
2. Day-to-day comparison tables
3. Range-vs-range comparison reports

## v0.5 Local Web Workbench

Goal:

1. Add a local review dashboard
2. Support editing and saving conclusions

Deliverables:

1. Dashboard page
2. Daily review page
3. Period review page
4. Comparison page

## v1.0 Research Platform

Goal:

1. Make the project useful as a real review system
2. Support historical tracking and workflow reuse

Deliverables:

1. Complete review archive
2. Search and filtering
3. Plan generation
4. Stable release docs
