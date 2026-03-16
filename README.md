# DragonScope-AShare

Chinese name: `龙头复盘系统`

`DragonScope-AShare` is an open-source review and research system for A-share dragon-head trading.
It focuses on three core workflows:

1. Daily review
2. Period review
3. Multi-day comparison

Unlike generic market dashboards, this project is built for traders who care about:

1. Market emotion
2. Main themes
3. Leader ladders
4. Capacity cores
5. Risk anchors
6. Next-day plans

## Why This Project

Most review workflows are fragmented:

1. One notebook for daily notes
2. One spreadsheet for stats
3. One trading app for charts
4. No structured history

`DragonScope-AShare` aims to turn review into a repeatable system:

1. Standardize daily review
2. Aggregate period review
3. Compare multiple days and detect regime shifts
4. Build a searchable historical review archive

## Core Features

### Daily Review

1. Index and market breadth snapshot
2. Non-ST limit-up / limit-down statistics
3. Non-ST board ladder
4. Main-theme ranking
5. Core leaders and risk anchors
6. Auto-generated review draft

### Period Review

1. 5-day / 10-day / 20-day review
2. Emotion score trend
3. Main-theme persistence
4. Leader switching
5. Best patterns and worst mistakes in the period

### Multi-Day Comparison

1. Compare recent trading days
2. Compare two custom ranges
3. Detect inflection days
4. Track theme rotation and environment changes

## Project Status

Current stage: `v0.1 documentation + demo`

Already included:

1. System design documents
2. Open-source launch files
3. A Tushare-based daily review generator demo

Next stage:

1. Database layer
2. Daily market stats storage
3. Period review engine
4. Comparison engine

## Repository Structure

```text
dragon-review-system/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── ROADMAP.md
├── PROJECT_CONTROL.md
├── requirements.txt
├── pyproject.toml
├── docs/
├── app/
├── scripts/
├── tests/
├── data/
└── reviews/
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your Tushare token

```bash
export TUSHARE_TOKEN=your_token
```

### 3. Generate a daily review

```bash
python scripts/generate_daily_review.py --date 20260316
```

## Documentation

1. [System Design](./docs/system-design.md)
2. [System Spec v1](./docs/system-spec-v1.md)
3. [Roadmap](./ROADMAP.md)
4. [Project Control](./PROJECT_CONTROL.md)

## Name Choice

Primary project name:

1. `DragonScope-AShare`

Why this name:

1. `Dragon` maps clearly to 龙头战法
2. `Scope` sounds like a professional research and observation system
3. `AShare` immediately explains the market scope
4. The combination is specific enough to avoid looking generic

Backup names:

1. `LongTouScope`
2. `DragonReviewLab`

## Disclaimer

This project is for research and review only.
It does not constitute investment advice.

## License

MIT
