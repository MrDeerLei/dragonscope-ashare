# Project Control

This is the master operating file for launching the GitHub open-source project.

Project name:

1. `DragonScope-AShare`

Local path:

1. `/Users/ray/Myworkspace/龙头复盘系统`

Recommended GitHub repository name:

1. `dragonscope-ashare`

## Step-by-Step Launch Checklist

### Step 1. Confirm the project name

Primary:

1. `DragonScope-AShare`

Alternatives:

1. `LongTouScope`
2. `DragonReviewLab`

Current recommendation:

1. Use `DragonScope-AShare`

Reason:

1. Professional
2. Easy to understand
3. Specific to A-share dragon-head review
4. Not generic like `stock-review-system`

### Step 2. Keep the local repo root clean

Files already prepared:

1. `README.md`
2. `LICENSE`
3. `CONTRIBUTING.md`
4. `ROADMAP.md`
5. `PROJECT_CONTROL.md`
6. `docs/system-design.md`
7. `docs/system-spec-v1.md`
8. `scripts/generate_daily_review.py`

### Step 3. Create the GitHub repository

On GitHub:

1. Click `New repository`
2. Repository name: `dragonscope-ashare`
3. Description:
   `An open-source A-share dragon-head review and research system for daily review, period review, and multi-day comparison.`
4. Set visibility to `Public`
5. Do not initialize with README if you want to push this local directory directly

### Step 4. Initialize local git

Run:

```bash
cd "/Users/ray/Myworkspace/龙头复盘系统"
git init
git checkout -b main
git add .
git commit -m "chore: initialize DragonScope-AShare open-source project"
```

### Step 5. Connect the GitHub remote

Run:

```bash
git remote add origin git@github.com:<your-github-username>/dragonscope-ashare.git
git push -u origin main
```

### Step 6. Improve the GitHub repository page

After pushing:

1. Add repository topics:
   `a-share`, `quant`, `trading`, `review-system`, `stock-analysis`, `china-market`
2. Add a short project website or documentation link later
3. Pin the repository on your GitHub profile

### Step 7. First public release content

Your first public message should say:

1. What the project is
2. Why it exists
3. What is already usable
4. What the roadmap is

### Step 8. First release target

Target tag:

1. `v0.1.0`

Release title:

1. `v0.1.0 - documentation and daily review demo`

### Step 9. Immediate next coding milestone

Build next:

1. Local database schema
2. Daily data sync pipeline
3. Stored daily market stats
4. Period review generator
5. Multi-day comparison generator

## Suggested Public Description

Short GitHub description:

`Open-source A-share dragon-head review and research system for daily review, period review, and multi-day comparison.`

Longer intro:

`DragonScope-AShare is an open-source review workbench for A-share dragon-head trading. It standardizes daily review, tracks theme and leader evolution, and supports period review plus multi-day comparison.`

## Suggested First GitHub Topics

1. `a-share`
2. `quant`
3. `trading-system`
4. `market-review`
5. `stock-research`
6. `python`
7. `tushare`

## Success Criteria For The First Month

1. Repository is public
2. README is clear
3. Demo script can run
4. At least one example review is generated
5. v0.2 tasks are broken into GitHub issues
