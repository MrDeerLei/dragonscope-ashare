import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import COMPARE_REVIEWS_DIR, DB_PATH, ensure_directories
from app.database import connect_db, init_db, replace_by_keys
from app.review_metrics import build_compare_result


def parse_args():
    parser = argparse.ArgumentParser(description="Compare two date ranges from local DragonScope database.")
    parser.add_argument("--left-start", required=True)
    parser.add_argument("--left-end", required=True)
    parser.add_argument("--right-start", required=True)
    parser.add_argument("--right-end", required=True)
    parser.add_argument("--compare-type", default="range_vs_range")
    return parser.parse_args()


def _load_stats(conn, start, end):
    stats = pd.read_sql_query(
        """
        SELECT m.*, r.main_theme
        FROM daily_market_stats m
        LEFT JOIN daily_review r ON m.trade_date = r.trade_date
        WHERE m.trade_date BETWEEN ? AND ?
        ORDER BY m.trade_date
        """,
        conn,
        params=(start, end),
    )
    return stats


def main():
    args = parse_args()
    ensure_directories()
    init_db(DB_PATH)
    with connect_db(DB_PATH) as conn:
        left_stats = _load_stats(conn, args.left_start, args.left_end)
        right_stats = _load_stats(conn, args.right_start, args.right_end)
        compare_df, markdown = build_compare_result(
            args.compare_type,
            f"{args.left_start}-{args.left_end}",
            f"{args.right_start}-{args.right_end}",
            left_stats,
            right_stats,
        )
        replace_by_keys(conn, "compare_result", compare_df, ["compare_id"])
        conn.commit()

    output = COMPARE_REVIEWS_DIR / f"{args.left_start}_{args.left_end}__vs__{args.right_start}_{args.right_end}.md"
    output.write_text(markdown, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
