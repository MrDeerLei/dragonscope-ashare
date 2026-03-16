SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trade_dates (
    trade_date TEXT PRIMARY KEY,
    prev_trade_date TEXT,
    is_open INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_basic_info (
    ts_code TEXT PRIMARY KEY,
    name TEXT,
    industry TEXT,
    market TEXT,
    list_status TEXT
);

CREATE TABLE IF NOT EXISTS raw_index_daily (
    trade_date TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    close REAL,
    open REAL,
    high REAL,
    low REAL,
    pct_chg REAL,
    amount REAL,
    PRIMARY KEY (trade_date, ts_code)
);

CREATE TABLE IF NOT EXISTS raw_stock_daily (
    trade_date TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    close REAL,
    open REAL,
    high REAL,
    low REAL,
    pct_chg REAL,
    amount REAL,
    vol REAL,
    up_limit REAL,
    down_limit REAL,
    PRIMARY KEY (trade_date, ts_code)
);

CREATE TABLE IF NOT EXISTS daily_stock_snapshot (
    trade_date TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    name TEXT,
    industry TEXT,
    market TEXT,
    close REAL,
    pct_chg REAL,
    amount REAL,
    amount_yi REAL,
    is_st INTEGER,
    is_limit_up INTEGER,
    is_limit_down INTEGER,
    is_limit_up_non_st INTEGER,
    is_limit_down_non_st INTEGER,
    board_count INTEGER,
    theme_name TEXT,
    theme_source TEXT,
    leader_score REAL,
    role_type TEXT,
    PRIMARY KEY (trade_date, ts_code)
);

CREATE TABLE IF NOT EXISTS daily_market_stats (
    trade_date TEXT PRIMARY KEY,
    sh_pct REAL,
    sz_pct REAL,
    cyb_pct REAL,
    hs300_pct REAL,
    amount_total REAL,
    amount_delta REAL,
    up_count INTEGER,
    down_count INTEGER,
    flat_count INTEGER,
    limit_up_non_st INTEGER,
    limit_down_non_st INTEGER,
    up_5_count INTEGER,
    down_5_count INTEGER,
    premium_avg REAL,
    premium_median REAL,
    advance_rate REAL,
    highest_board_non_st INTEGER,
    board_dist_json TEXT,
    emotion_score REAL,
    market_stage TEXT
);

CREATE TABLE IF NOT EXISTS daily_theme_stats (
    trade_date TEXT NOT NULL,
    theme_name TEXT NOT NULL,
    limit_up_count INTEGER,
    limit_down_count INTEGER,
    board_count INTEGER,
    theme_amount REAL,
    core_stock TEXT,
    capacity_stock TEXT,
    theme_score REAL,
    theme_rank INTEGER,
    PRIMARY KEY (trade_date, theme_name)
);

CREATE TABLE IF NOT EXISTS daily_leader_stats (
    trade_date TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    name TEXT,
    theme_name TEXT,
    board_count INTEGER,
    amount REAL,
    is_market_leader INTEGER,
    is_theme_leader INTEGER,
    is_capacity_core INTEGER,
    is_risk_anchor INTEGER,
    leader_score REAL,
    PRIMARY KEY (trade_date, ts_code)
);

CREATE TABLE IF NOT EXISTS daily_review (
    trade_date TEXT PRIMARY KEY,
    market_stage TEXT,
    main_theme TEXT,
    secondary_theme TEXT,
    market_leader TEXT,
    capacity_core TEXT,
    risk_anchor TEXT,
    best_setup TEXT,
    bad_setup TEXT,
    tomorrow_plan TEXT,
    position_plan TEXT,
    review_markdown TEXT,
    review_status TEXT
);

CREATE TABLE IF NOT EXISTS period_review (
    period_id TEXT PRIMARY KEY,
    start_date TEXT,
    end_date TEXT,
    period_type TEXT,
    emotion_avg REAL,
    emotion_max REAL,
    emotion_min REAL,
    amount_avg REAL,
    limit_up_avg REAL,
    limit_down_avg REAL,
    advance_rate_avg REAL,
    premium_avg REAL,
    highest_board_max INTEGER,
    main_theme_summary TEXT,
    leader_summary TEXT,
    risk_summary TEXT,
    period_markdown TEXT
);

CREATE TABLE IF NOT EXISTS period_theme_compare (
    period_id TEXT NOT NULL,
    theme_name TEXT NOT NULL,
    appear_days INTEGER,
    limit_up_total INTEGER,
    board_total INTEGER,
    avg_theme_score REAL,
    best_leader TEXT,
    theme_stage TEXT,
    PRIMARY KEY (period_id, theme_name)
);

CREATE TABLE IF NOT EXISTS period_leader_compare (
    period_id TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    name TEXT,
    theme_name TEXT,
    leader_days INTEGER,
    highest_board INTEGER,
    avg_amount REAL,
    avg_leader_score REAL,
    role_type TEXT,
    PRIMARY KEY (period_id, ts_code)
);

CREATE TABLE IF NOT EXISTS compare_result (
    compare_id TEXT PRIMARY KEY,
    compare_type TEXT,
    left_range TEXT,
    right_range TEXT,
    emotion_delta REAL,
    amount_delta REAL,
    limit_up_delta REAL,
    limit_down_delta REAL,
    premium_delta REAL,
    advance_rate_delta REAL,
    main_theme_changed INTEGER,
    leader_changed INTEGER,
    compare_markdown TEXT
);

CREATE TABLE IF NOT EXISTS day_compare_cache (
    trade_date TEXT PRIMARY KEY,
    prev_trade_date TEXT,
    emotion_delta REAL,
    amount_delta REAL,
    limit_up_delta REAL,
    limit_down_delta REAL,
    premium_delta REAL,
    advance_rate_delta REAL,
    highest_board_delta REAL,
    main_theme_changed INTEGER,
    market_stage_changed INTEGER,
    market_leader_changed INTEGER,
    inflection_score REAL,
    inflection_reason TEXT
);
"""
