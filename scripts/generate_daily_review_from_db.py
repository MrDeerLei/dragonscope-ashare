import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import DAILY_REVIEWS_DIR, DB_PATH, ensure_directories
from app.database import connect_db, init_db


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a daily review markdown from local DragonScope database.")
    parser.add_argument("--date", required=True, help="Trade date, format: YYYYMMDD")
    return parser.parse_args()


def main():
    args = parse_args()
    ensure_directories()
    init_db(DB_PATH)
    with connect_db(DB_PATH) as conn:
        market = pd.read_sql_query(
            "SELECT * FROM daily_market_stats WHERE trade_date = ?",
            conn,
            params=(args.date,),
        )
        review = pd.read_sql_query(
            "SELECT * FROM daily_review WHERE trade_date = ?",
            conn,
            params=(args.date,),
        )
        themes = pd.read_sql_query(
            """
            SELECT *
            FROM daily_theme_stats
            WHERE trade_date = ?
            ORDER BY theme_rank
            LIMIT 10
            """,
            conn,
            params=(args.date,),
        )
        leaders = pd.read_sql_query(
            """
            SELECT *
            FROM daily_leader_stats
            WHERE trade_date = ?
            ORDER BY is_market_leader DESC, is_theme_leader DESC, is_capacity_core DESC, leader_score DESC
            LIMIT 20
            """,
            conn,
            params=(args.date,),
        )

    if market.empty or review.empty:
        raise ValueError(f"No synced daily review found for {args.date}. Run sync_day.py first.")

    market_row = market.iloc[0]
    review_row = review.iloc[0]
    lines = [
        f"# {args.date} 单日复盘",
        "",
        "## 市场总览",
        "",
        f"- 市场阶段：`{market_row['market_stage']}`",
        f"- 情绪分：`{market_row['emotion_score']}`",
        f"- 两市成交额：`{market_row['amount_total']:.2f}亿`",
        f"- 成交额变化：`{market_row['amount_delta']:+.2f}亿`",
        f"- 非ST涨停 / 跌停：`{market_row['limit_up_non_st']} / {market_row['limit_down_non_st']}`",
        f"- 非ST最高连板：`{market_row['highest_board_non_st']}板`",
        "",
        "## 主线题材",
        "",
    ]
    for _, row in themes.head(5).iterrows():
        lines.append(
            f"- `{int(row['theme_rank'])}. {row['theme_name']}`：阶段=`{row['theme_stage']}`，涨停=`{row['limit_up_count']}`，连板=`{row['board_count']}`，核心=`{row['core_stock']}`，容量=`{row['capacity_stock']}`"
        )
    lines.extend(["", "## 龙头梯队", ""])
    for _, row in leaders.head(10).iterrows():
        lines.append(
            f"- `{row['name']}`：角色=`{row['role_type']}`，题材=`{row['theme_name']}`，板数=`{row['board_count']}`，强度=`{row['leader_score']:.2f}`"
        )
    lines.extend(
        [
            "",
            "## 自动结论",
            "",
            f"- 主线：`{review_row['main_theme']}`",
            f"- 次主线：`{review_row['secondary_theme']}`",
            f"- 市场龙头：`{review_row['market_leader']}`",
            f"- 容量核心：`{review_row['capacity_core']}`",
            f"- 风险锚：`{review_row['risk_anchor']}`",
            f"- 最佳形态：`{review_row['best_setup']}`",
            f"- 避免形态：`{review_row['bad_setup']}`",
            f"- 明日计划：`{review_row['tomorrow_plan']}`",
            f"- 仓位建议：`{review_row['position_plan']}`",
            "",
        ]
    )
    output = DAILY_REVIEWS_DIR / f"{args.date}_from_db.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
