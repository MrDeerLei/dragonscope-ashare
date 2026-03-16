import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import COMPARE_REVIEWS_DIR, DB_PATH, ensure_directories
from app.database import connect_db, init_db, replace_by_keys
from app.review_metrics import build_day_change_matrix


def parse_args():
    parser = argparse.ArgumentParser(description="Generate multi-day comparison matrix from local DragonScope database.")
    parser.add_argument("--start", required=True, help="Start date, format: YYYYMMDD")
    parser.add_argument("--end", required=True, help="End date, format: YYYYMMDD")
    return parser.parse_args()


def main():
    args = parse_args()
    ensure_directories()
    init_db(DB_PATH)
    with connect_db(DB_PATH) as conn:
        daily_stats = pd.read_sql_query(
            """
            SELECT m.*, r.main_theme, r.market_leader
            FROM daily_market_stats m
            LEFT JOIN daily_review r ON m.trade_date = r.trade_date
            WHERE m.trade_date BETWEEN ? AND ?
            ORDER BY m.trade_date
            """,
            conn,
            params=(args.start, args.end),
        )
        matrix_df = build_day_change_matrix(daily_stats)
        replace_by_keys(conn, "day_compare_cache", matrix_df, ["trade_date"])
        conn.commit()

    lines = [
        f"# 多日对比矩阵",
        "",
        f"- 区间：`{args.start} ~ {args.end}`",
        "",
        "| 日期 | 前一日 | 情绪变化 | 成交额变化(亿) | 涨停变化 | 跌停变化 | 主线切换 | 龙头切换 | 拐点评分 | 原因 |",
        "|---|---|---:|---:|---:|---:|---|---|---:|---|",
    ]
    for _, row in matrix_df.sort_values("trade_date").iterrows():
        lines.append(
            f"| {row['trade_date']} | {row['prev_trade_date']} | {row['emotion_delta']:+.2f} | {row['amount_delta']:+.2f} | {row['limit_up_delta']:+.0f} | {row['limit_down_delta']:+.0f} | {'是' if row['main_theme_changed'] else '否'} | {'是' if row['market_leader_changed'] else '否'} | {row['inflection_score']:.2f} | {row['inflection_reason']} |"
        )

    top_rows = matrix_df.sort_values("inflection_score", ascending=False).head(3)
    lines.extend(["", "## 重点拐点", ""])
    if top_rows.empty:
        lines.append("- 区间内无可识别拐点")
    else:
        for _, row in top_rows.iterrows():
            lines.append(
                f"- `{row['prev_trade_date']} -> {row['trade_date']}`：评分=`{row['inflection_score']:.2f}`，原因=`{row['inflection_reason']}`"
            )

    output = COMPARE_REVIEWS_DIR / f"{args.start}_{args.end}_matrix.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
