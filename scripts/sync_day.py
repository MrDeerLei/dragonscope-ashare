import os
import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import DB_PATH
from app.database import connect_db, init_db, replace_by_keys
from app.review_metrics import (
    build_daily_market_stats,
    build_daily_review_row,
    build_daily_stock_snapshot,
    build_leader_stats,
    build_theme_stats,
    compute_board_ladder,
    normalize_market_day,
)
from app.tushare_data import fetch_indices, fetch_market_day, fetch_stock_basic, get_pro, get_trade_dates


def parse_args():
    parser = argparse.ArgumentParser(description="Sync one trade day into local DragonScope database.")
    parser.add_argument("--date", required=True, help="Trade date, format: YYYYMMDD")
    parser.add_argument("--token", default=os.getenv("TUSHARE_TOKEN"), help="Tushare token, defaults to TUSHARE_TOKEN")
    return parser.parse_args()


def main():
    args = parse_args()
    init_db(DB_PATH)
    pro = get_pro(args.token)
    trade_dates, prev_trade_date = get_trade_dates(pro, args.date, count=6)
    if not prev_trade_date:
        raise ValueError("Cannot compute previous trade date for the selected day.")

    basic = fetch_stock_basic(pro)
    day_frames = {}
    for trade_date in trade_dates:
        day_frames[trade_date] = normalize_market_day(fetch_market_day(pro, trade_date, basic))

    current_day = day_frames[args.date]
    prev_day = day_frames[prev_trade_date]
    indices = fetch_indices(pro, args.date)
    board_counts = compute_board_ladder(day_frames)

    snapshot = build_daily_stock_snapshot(current_day, board_counts)
    market_stats = build_daily_market_stats(args.date, indices, current_day, prev_day, board_counts)
    theme_stats = build_theme_stats(args.date, snapshot)
    leader_stats = build_leader_stats(args.date, snapshot, theme_stats)
    daily_review = build_daily_review_row(args.date, market_stats, theme_stats, leader_stats)

    raw_stock_daily = current_day[
        ["trade_date", "ts_code", "close", "open", "high", "low", "pct_chg", "amount", "vol", "up_limit", "down_limit"]
    ].copy()
    raw_index_daily = indices[
        ["trade_date", "ts_code", "close", "open", "high", "low", "pct_chg", "amount"]
    ].copy()
    trade_dates_df = pd.DataFrame(
        [{"trade_date": args.date, "prev_trade_date": prev_trade_date, "is_open": 1}]
    )

    with connect_db(DB_PATH) as conn:
        replace_by_keys(conn, "trade_dates", trade_dates_df, ["trade_date"])
        replace_by_keys(conn, "stock_basic_info", basic, ["ts_code"])
        replace_by_keys(conn, "raw_index_daily", raw_index_daily, ["trade_date", "ts_code"])
        replace_by_keys(conn, "raw_stock_daily", raw_stock_daily, ["trade_date", "ts_code"])
        replace_by_keys(conn, "daily_stock_snapshot", snapshot, ["trade_date", "ts_code"])
        replace_by_keys(conn, "daily_market_stats", market_stats, ["trade_date"])
        replace_by_keys(conn, "daily_theme_stats", theme_stats, ["trade_date", "theme_name"])
        replace_by_keys(conn, "daily_leader_stats", leader_stats, ["trade_date", "ts_code"])
        replace_by_keys(conn, "daily_review", daily_review, ["trade_date"])
        conn.commit()

    print(f"synced trade_date={args.date} db={DB_PATH}")


if __name__ == "__main__":
    main()
