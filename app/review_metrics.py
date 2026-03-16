import json
import math
from collections import Counter

import pandas as pd


def is_st_name(name):
    return isinstance(name, str) and "ST" in name.upper()


def yi_from_amount(amount_series):
    return float(amount_series.sum()) / 100000.0


def normalize_market_day(df: pd.DataFrame):
    result = df.copy()
    result["is_st"] = result["name"].apply(is_st_name)
    result["is_limit_up"] = result["close"].round(2) >= result["up_limit"].round(2)
    result["is_limit_down"] = result["close"].round(2) <= result["down_limit"].round(2)
    result["is_limit_up_non_st"] = result["is_limit_up"] & (~result["is_st"])
    result["is_limit_down_non_st"] = result["is_limit_down"] & (~result["is_st"])
    result["amount_yi"] = result["amount"] / 100000.0
    result["theme_name"] = result["industry"].fillna("未分类")
    return result


def compute_prev_premium(prev_day: pd.DataFrame, current_day: pd.DataFrame):
    prev_up = prev_day[prev_day["is_limit_up_non_st"]][["ts_code", "close"]].rename(columns={"close": "prev_close"})
    premium = prev_up.merge(current_day[["ts_code", "close"]], on="ts_code", how="inner")
    if premium.empty:
        return {"count": 0, "avg": None, "median": None}
    premium["premium_pct"] = (premium["close"] / premium["prev_close"] - 1.0) * 100.0
    return {
        "count": int(len(prev_up)),
        "avg": float(premium["premium_pct"].mean()),
        "median": float(premium["premium_pct"].median()),
    }


def compute_relimit_rate(prev_day: pd.DataFrame, current_day: pd.DataFrame):
    prev_up = prev_day[prev_day["is_limit_up_non_st"]][["ts_code"]]
    cur_up = current_day[current_day["is_limit_up_non_st"]][["ts_code"]]
    if prev_up.empty:
        return {"count": 0, "advance": 0, "rate": None}
    adv = prev_up.merge(cur_up, on="ts_code", how="inner")
    return {
        "count": int(len(prev_up)),
        "advance": int(len(adv)),
        "rate": float(len(adv) / len(prev_up) * 100.0),
    }


def compute_board_ladder(day_frames: dict[str, pd.DataFrame]):
    frames = []
    ordered_dates = sorted(day_frames.keys())
    for trade_date in ordered_dates:
        day = day_frames[trade_date]
        frames.append(day[["ts_code", "is_limit_up"]].assign(trade_date=trade_date))
    panel = pd.concat(frames, ignore_index=True)
    pivot = panel.pivot(index="ts_code", columns="trade_date", values="is_limit_up").fillna(False)

    counts = {}
    ordered_dates_desc = list(reversed(ordered_dates))
    for code, row in pivot.iterrows():
        streak = 0
        for trade_date in ordered_dates_desc:
            if bool(row.get(trade_date, False)):
                streak += 1
            else:
                break
        if streak > 0:
            counts[code] = streak
    return counts


def classify_market(stats):
    if stats["relimit_rate"] is not None and stats["relimit_rate"] < 25 and stats["highest_board"] <= 3:
        return "分化偏弱"
    if stats["relimit_rate"] is not None and stats["relimit_rate"] >= 35 and stats["highest_board"] >= 4:
        return "主升偏强"
    if stats["premium_avg"] is not None and stats["premium_avg"] < -1 and stats["limit_down_non_st"] >= 10:
        return "退潮"
    return "轮动市"


def calc_emotion_score(stats):
    score = 50.0
    score += min(stats["limit_up_non_st"], 60) * 0.25
    score -= min(stats["limit_down_non_st"], 30) * 0.8
    score += min(max(stats["highest_board"] - 2, 0), 4) * 4.0
    if stats["premium_avg"] is not None:
        score += max(min(stats["premium_avg"], 5), -5) * 2.0
    if stats["relimit_rate"] is not None:
        score += (stats["relimit_rate"] - 20.0) * 0.4
    return max(0, min(100, round(score, 1)))


def build_daily_stock_snapshot(current_day: pd.DataFrame, board_counts: dict[str, int]):
    snapshot = current_day.copy()
    snapshot["board_count"] = snapshot["ts_code"].map(board_counts).fillna(0).astype(int)
    snapshot["leader_score"] = snapshot["board_count"] * 12 + snapshot["amount_yi"] * 0.05 + snapshot["pct_chg"].fillna(0)
    snapshot["role_type"] = "普通"
    return snapshot[
        [
            "trade_date",
            "ts_code",
            "name",
            "industry",
            "market",
            "close",
            "pct_chg",
            "amount",
            "amount_yi",
            "is_st",
            "is_limit_up",
            "is_limit_down",
            "is_limit_up_non_st",
            "is_limit_down_non_st",
            "board_count",
            "theme_name",
            "leader_score",
            "role_type",
        ]
    ].copy()


def build_daily_market_stats(trade_date: str, indices: pd.DataFrame, current_day: pd.DataFrame, prev_day: pd.DataFrame, board_counts: dict[str, int]):
    idx_map = {row["name"]: row for _, row in indices.iterrows()}
    premium = compute_prev_premium(prev_day, current_day)
    relimit = compute_relimit_rate(prev_day, current_day)

    board_df = current_day[["ts_code", "name", "is_st"]].copy()
    board_df["board_count"] = board_df["ts_code"].map(board_counts).fillna(0).astype(int)
    board_df = board_df[(board_df["board_count"] > 0) & (~board_df["is_st"])]
    board_dist = Counter(board_df["board_count"])
    highest_board = int(board_df["board_count"].max()) if len(board_df) else 0

    stats = {
        "limit_up_non_st": int(current_day["is_limit_up_non_st"].sum()),
        "limit_down_non_st": int(current_day["is_limit_down_non_st"].sum()),
        "highest_board": highest_board,
        "premium_avg": premium["avg"],
        "relimit_rate": relimit["rate"],
    }
    emotion_score = calc_emotion_score(stats)
    market_stage = classify_market(stats)

    row = {
        "trade_date": trade_date,
        "sh_pct": _get_idx_pct(idx_map, "上证指数"),
        "sz_pct": _get_idx_pct(idx_map, "深成指"),
        "cyb_pct": _get_idx_pct(idx_map, "创业板"),
        "hs300_pct": _get_idx_pct(idx_map, "沪深300"),
        "amount_total": yi_from_amount(current_day["amount"]),
        "amount_delta": yi_from_amount(current_day["amount"]) - yi_from_amount(prev_day["amount"]),
        "up_count": int((current_day["pct_chg"] > 0).sum()),
        "down_count": int((current_day["pct_chg"] < 0).sum()),
        "flat_count": int((current_day["pct_chg"] == 0).sum()),
        "limit_up_non_st": stats["limit_up_non_st"],
        "limit_down_non_st": stats["limit_down_non_st"],
        "up_5_count": int((current_day["pct_chg"] >= 5).sum()),
        "down_5_count": int((current_day["pct_chg"] <= -5).sum()),
        "premium_avg": premium["avg"],
        "premium_median": premium["median"],
        "advance_rate": relimit["rate"],
        "highest_board_non_st": highest_board,
        "board_dist_json": json.dumps(dict(sorted(board_dist.items())), ensure_ascii=False),
        "emotion_score": emotion_score,
        "market_stage": market_stage,
    }
    return pd.DataFrame([row])


def build_theme_stats(trade_date: str, snapshot: pd.DataFrame):
    grouped = snapshot.groupby("theme_name", dropna=False)
    rows = []
    for theme_name, group in grouped:
        non_st = group[~group["is_st"]]
        if non_st.empty:
            continue
        limit_up_count = int(non_st["is_limit_up_non_st"].sum())
        limit_down_count = int(non_st["is_limit_down_non_st"].sum())
        board_count = int((non_st["board_count"] >= 2).sum())
        theme_amount = float(non_st["amount_yi"].sum())
        capacity_stock = (
            non_st.sort_values(["amount_yi", "pct_chg"], ascending=[False, False]).iloc[0]["name"]
            if len(non_st)
            else None
        )
        core_candidates = non_st[non_st["is_limit_up_non_st"]].sort_values(
            ["board_count", "amount_yi"], ascending=[False, False]
        )
        core_stock = core_candidates.iloc[0]["name"] if len(core_candidates) else capacity_stock
        theme_score = limit_up_count * 5 + board_count * 8 + theme_amount * 0.02 - limit_down_count * 2
        rows.append(
            {
                "trade_date": trade_date,
                "theme_name": theme_name,
                "limit_up_count": limit_up_count,
                "limit_down_count": limit_down_count,
                "board_count": board_count,
                "theme_amount": theme_amount,
                "core_stock": core_stock,
                "capacity_stock": capacity_stock,
                "theme_score": round(theme_score, 2),
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values(["theme_score", "limit_up_count", "theme_amount"], ascending=[False, False, False]).reset_index(drop=True)
    df["theme_rank"] = df.index + 1
    return df


def build_leader_stats(trade_date: str, snapshot: pd.DataFrame, theme_stats: pd.DataFrame):
    non_st = snapshot[~snapshot["is_st"]].copy()
    if non_st.empty:
        return pd.DataFrame()
    highest_board = int(non_st["board_count"].max())
    market_leader_codes = set(non_st[non_st["board_count"] == highest_board]["ts_code"]) if highest_board > 0 else set()
    capacity_code = (
        non_st.sort_values(["amount_yi", "pct_chg"], ascending=[False, False]).iloc[0]["ts_code"]
        if len(non_st)
        else None
    )
    risk_anchor_codes = set(
        non_st[non_st["is_limit_down_non_st"]].sort_values(["amount_yi"], ascending=[False]).head(5)["ts_code"]
    )
    theme_core_map = {}
    if theme_stats is not None and not theme_stats.empty:
        theme_core_map = dict(zip(theme_stats["theme_name"], theme_stats["core_stock"]))
    rows = []
    for _, row in non_st.iterrows():
        is_market_leader = int(row["ts_code"] in market_leader_codes and highest_board > 0)
        is_theme_leader = int(theme_core_map.get(row["theme_name"]) == row["name"])
        is_capacity_core = int(capacity_code == row["ts_code"])
        is_risk_anchor = int(row["ts_code"] in risk_anchor_codes)
        rows.append(
            {
                "trade_date": trade_date,
                "ts_code": row["ts_code"],
                "name": row["name"],
                "theme_name": row["theme_name"],
                "board_count": int(row["board_count"]),
                "amount": float(row["amount_yi"]),
                "is_market_leader": is_market_leader,
                "is_theme_leader": is_theme_leader,
                "is_capacity_core": is_capacity_core,
                "is_risk_anchor": is_risk_anchor,
                "leader_score": float(row["leader_score"]),
            }
        )
    return pd.DataFrame(rows)


def build_daily_review_row(trade_date: str, market_stats: pd.DataFrame, theme_stats: pd.DataFrame, leader_stats: pd.DataFrame):
    market_stage = market_stats.iloc[0]["market_stage"]
    main_theme = theme_stats.iloc[0]["theme_name"] if len(theme_stats) else None
    secondary_theme = theme_stats.iloc[1]["theme_name"] if len(theme_stats) > 1 else None
    market_leaders = leader_stats[leader_stats["is_market_leader"] == 1]["name"].tolist()
    market_leader = "、".join(market_leaders[:3]) if market_leaders else None
    capacity = leader_stats[leader_stats["is_capacity_core"] == 1]["name"].tolist()
    capacity_core = capacity[0] if capacity else None
    risk = leader_stats[leader_stats["is_risk_anchor"] == 1]["name"].tolist()
    risk_anchor = "、".join(risk[:3]) if risk else None
    markdown = _render_auto_daily_summary(trade_date, market_stats.iloc[0], theme_stats, leader_stats)
    row = {
        "trade_date": trade_date,
        "market_stage": market_stage,
        "main_theme": main_theme,
        "secondary_theme": secondary_theme,
        "market_leader": market_leader,
        "capacity_core": capacity_core,
        "risk_anchor": risk_anchor,
        "best_setup": "前排强板与容量首板",
        "bad_setup": "高标硬接与弱势抄底",
        "tomorrow_plan": "先看接力修复，再决定是否加仓",
        "position_plan": "轻仓试错，优先前排",
        "review_markdown": markdown,
        "review_status": "auto_generated",
    }
    return pd.DataFrame([row])


def build_period_review(period_type: str, daily_stats: pd.DataFrame, theme_stats: pd.DataFrame, leader_stats: pd.DataFrame):
    if daily_stats.empty:
        raise ValueError("No daily stats found for the selected period.")
    start_date = daily_stats["trade_date"].min()
    end_date = daily_stats["trade_date"].max()
    period_id = f"{period_type}:{start_date}:{end_date}"
    theme_summary = (
        theme_stats.groupby("theme_name").agg(appear_days=("trade_date", "nunique"), total_score=("theme_score", "sum"))
        .sort_values(["appear_days", "total_score"], ascending=[False, False])
        .head(5)
        .reset_index()
    )
    leader_summary = (
        leader_stats[leader_stats["is_market_leader"] == 1]
        .groupby("name")
        .agg(leader_days=("trade_date", "nunique"), max_board=("board_count", "max"))
        .sort_values(["leader_days", "max_board"], ascending=[False, False])
        .head(5)
        .reset_index()
    )
    risk_summary = (
        leader_stats[leader_stats["is_risk_anchor"] == 1]
        .groupby("name")
        .agg(risk_days=("trade_date", "nunique"))
        .sort_values(["risk_days"], ascending=[False])
        .head(5)
        .reset_index()
    )

    markdown = _render_period_markdown(period_type, daily_stats, theme_summary, leader_summary, risk_summary)
    row = {
        "period_id": period_id,
        "start_date": start_date,
        "end_date": end_date,
        "period_type": period_type,
        "emotion_avg": float(daily_stats["emotion_score"].mean()),
        "emotion_max": float(daily_stats["emotion_score"].max()),
        "emotion_min": float(daily_stats["emotion_score"].min()),
        "amount_avg": float(daily_stats["amount_total"].mean()),
        "limit_up_avg": float(daily_stats["limit_up_non_st"].mean()),
        "limit_down_avg": float(daily_stats["limit_down_non_st"].mean()),
        "advance_rate_avg": _safe_mean(daily_stats["advance_rate"]),
        "premium_avg": _safe_mean(daily_stats["premium_avg"]),
        "highest_board_max": int(daily_stats["highest_board_non_st"].max()),
        "main_theme_summary": json.dumps(theme_summary.to_dict("records"), ensure_ascii=False),
        "leader_summary": json.dumps(leader_summary.to_dict("records"), ensure_ascii=False),
        "risk_summary": json.dumps(risk_summary.to_dict("records"), ensure_ascii=False),
        "period_markdown": markdown,
    }
    return pd.DataFrame([row]), markdown


def build_compare_result(compare_type: str, left_label: str, right_label: str, left_stats: pd.DataFrame, right_stats: pd.DataFrame):
    if left_stats.empty or right_stats.empty:
        raise ValueError("Comparison requires data on both sides.")
    left = _aggregate_compare_stats(left_stats)
    right = _aggregate_compare_stats(right_stats)
    compare_id = f"{compare_type}:{left_label}:{right_label}"
    markdown = _render_compare_markdown(compare_type, left_label, right_label, left, right)
    row = {
        "compare_id": compare_id,
        "compare_type": compare_type,
        "left_range": left_label,
        "right_range": right_label,
        "emotion_delta": right["emotion_score"] - left["emotion_score"],
        "amount_delta": right["amount_total"] - left["amount_total"],
        "limit_up_delta": right["limit_up_non_st"] - left["limit_up_non_st"],
        "limit_down_delta": right["limit_down_non_st"] - left["limit_down_non_st"],
        "premium_delta": _safe_sub(right["premium_avg"], left["premium_avg"]),
        "advance_rate_delta": _safe_sub(right["advance_rate"], left["advance_rate"]),
        "main_theme_changed": int(left["main_theme"] != right["main_theme"]),
        "leader_changed": int(left["market_stage"] != right["market_stage"]),
        "compare_markdown": markdown,
    }
    return pd.DataFrame([row]), markdown


def _render_auto_daily_summary(trade_date, market_stats_row, theme_stats, leader_stats):
    top_themes = "、".join(theme_stats["theme_name"].head(3).tolist()) if len(theme_stats) else "无明确主线"
    market_leaders = "、".join(leader_stats[leader_stats["is_market_leader"] == 1]["name"].head(3).tolist()) or "空缺"
    return "\n".join(
        [
            f"# {trade_date} 自动复盘摘要",
            "",
            f"- 市场阶段：`{market_stats_row['market_stage']}`",
            f"- 情绪分：`{market_stats_row['emotion_score']}`",
            f"- 非ST涨停 / 跌停：`{market_stats_row['limit_up_non_st']} / {market_stats_row['limit_down_non_st']}`",
            f"- 非ST最高连板：`{market_stats_row['highest_board_non_st']}板`",
            f"- 主线候选：`{top_themes}`",
            f"- 市场高标：`{market_leaders}`",
        ]
    )


def _render_period_markdown(period_type, daily_stats, theme_summary, leader_summary, risk_summary):
    start_date = daily_stats["trade_date"].min()
    end_date = daily_stats["trade_date"].max()
    top_theme = theme_summary.iloc[0]["theme_name"] if len(theme_summary) else "无"
    top_leader = leader_summary.iloc[0]["name"] if len(leader_summary) else "无"
    top_risk = risk_summary.iloc[0]["name"] if len(risk_summary) else "无"
    return "\n".join(
        [
            f"# {period_type} 周期复盘",
            "",
            f"- 周期范围：`{start_date} ~ {end_date}`",
            f"- 情绪均值：`{daily_stats['emotion_score'].mean():.2f}`",
            f"- 情绪最高 / 最低：`{daily_stats['emotion_score'].max():.2f} / {daily_stats['emotion_score'].min():.2f}`",
            f"- 平均非ST涨停 / 跌停：`{daily_stats['limit_up_non_st'].mean():.2f} / {daily_stats['limit_down_non_st'].mean():.2f}`",
            f"- 最高非ST连板峰值：`{int(daily_stats['highest_board_non_st'].max())}板`",
            f"- 周期最强主线：`{top_theme}`",
            f"- 周期核心龙头：`{top_leader}`",
            f"- 周期风险锚：`{top_risk}`",
        ]
    )


def _render_compare_markdown(compare_type, left_label, right_label, left, right):
    return "\n".join(
        [
            f"# {compare_type} 对比",
            "",
            f"- 左侧区间：`{left_label}`",
            f"- 右侧区间：`{right_label}`",
            f"- 情绪分变化：`{right['emotion_score'] - left['emotion_score']:+.2f}`",
            f"- 平均成交额变化：`{right['amount_total'] - left['amount_total']:+.2f}亿`",
            f"- 平均非ST涨停变化：`{right['limit_up_non_st'] - left['limit_up_non_st']:+.2f}`",
            f"- 平均非ST跌停变化：`{right['limit_down_non_st'] - left['limit_down_non_st']:+.2f}`",
            f"- 主线变化：`{left['main_theme']} -> {right['main_theme']}`",
            f"- 市场阶段变化：`{left['market_stage']} -> {right['market_stage']}`",
        ]
    )


def _aggregate_compare_stats(stats_df: pd.DataFrame):
    return {
        "emotion_score": float(stats_df["emotion_score"].mean()),
        "amount_total": float(stats_df["amount_total"].mean()),
        "limit_up_non_st": float(stats_df["limit_up_non_st"].mean()),
        "limit_down_non_st": float(stats_df["limit_down_non_st"].mean()),
        "premium_avg": _safe_mean(stats_df["premium_avg"]),
        "advance_rate": _safe_mean(stats_df["advance_rate"]),
        "market_stage": stats_df["market_stage"].iloc[-1],
        "main_theme": stats_df["main_theme"].mode().iloc[0] if "main_theme" in stats_df.columns and stats_df["main_theme"].notna().any() else "无",
    }


def _safe_mean(series):
    s = pd.Series(series).dropna()
    return float(s.mean()) if len(s) else None


def _safe_sub(a, b):
    if a is None or b is None or (isinstance(a, float) and math.isnan(a)) or (isinstance(b, float) and math.isnan(b)):
        return None
    return a - b


def _get_idx_pct(idx_map, name):
    if name not in idx_map:
        return None
    return idx_map[name].get("pct_chg")
