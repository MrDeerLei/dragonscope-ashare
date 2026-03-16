import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import COMPARE_REVIEWS_DIR, DB_PATH, PERIOD_REVIEWS_DIR, ensure_directories
from app.database import connect_db, init_db, replace_by_keys
from app.review_metrics import build_period_review


def parse_args():
    parser = argparse.ArgumentParser(description="Generate period review from local DragonScope database.")
    parser.add_argument("--start", required=True, help="Start date, format: YYYYMMDD")
    parser.add_argument("--end", required=True, help="End date, format: YYYYMMDD")
    parser.add_argument(
        "--period-type",
        default="custom",
        help="Period label, e.g. 5d / 10d / 20d / custom",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    ensure_directories()
    init_db(DB_PATH)
    with connect_db(DB_PATH) as conn:
        daily_stats = pd.read_sql_query(
            """
            SELECT *
            FROM daily_market_stats
            WHERE trade_date BETWEEN ? AND ?
            ORDER BY trade_date
            """,
            conn,
            params=(args.start, args.end),
        )
        daily_reviews = pd.read_sql_query(
            """
            SELECT trade_date, main_theme, market_leader
            FROM daily_review
            WHERE trade_date BETWEEN ? AND ?
            ORDER BY trade_date
            """,
            conn,
            params=(args.start, args.end),
        )
        daily_stats = daily_stats.merge(daily_reviews, on="trade_date", how="left")
        theme_stats = pd.read_sql_query(
            """
            SELECT *
            FROM daily_theme_stats
            WHERE trade_date BETWEEN ? AND ?
            ORDER BY trade_date, theme_rank
            """,
            conn,
            params=(args.start, args.end),
        )
        leader_stats = pd.read_sql_query(
            """
            SELECT *
            FROM daily_leader_stats
            WHERE trade_date BETWEEN ? AND ?
            ORDER BY trade_date
            """,
            conn,
            params=(args.start, args.end),
        )
        period_df, theme_compare_df, leader_compare_df, day_change_df, markdown = build_period_review(
            args.period_type, daily_stats, theme_stats, leader_stats
        )
        replace_by_keys(conn, "period_review", period_df, ["period_id"])
        replace_by_keys(conn, "period_theme_compare", theme_compare_df, ["period_id", "theme_name"])
        replace_by_keys(conn, "period_leader_compare", leader_compare_df, ["period_id", "ts_code"])
        replace_by_keys(conn, "day_compare_cache", day_change_df, ["trade_date"])
        conn.commit()

    output = PERIOD_REVIEWS_DIR / f"{args.start}_{args.end}_{args.period_type}_review.md"
    output.write_text(markdown, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
