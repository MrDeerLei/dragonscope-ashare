import argparse
import math
import os
from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
import tushare as ts


def parse_args():
    parser = argparse.ArgumentParser(description="Generate ST-filtered dragon strategy review from Tushare.")
    parser.add_argument("--date", required=True, help="Trade date, format: YYYYMMDD")
    parser.add_argument("--token", default=os.getenv("TUSHARE_TOKEN"), help="Tushare token")
    parser.add_argument(
        "--output",
        default=None,
        help="Output markdown path. Default: ./reviews/<date>_dragon_review.md",
    )
    return parser.parse_args()


def get_pro(token):
    if not token:
        raise ValueError("Missing Tushare token. Pass --token or set TUSHARE_TOKEN.")
    for key in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
        os.environ.pop(key, None)
    ts.set_token(token)
    return ts.pro_api(timeout=20)


def is_st_name(name):
    return isinstance(name, str) and "ST" in name.upper()


def pct(value, digits=2):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "未获取"
    return f"{value:.{digits}f}%"


def yi_from_amount(amount_series):
    return float(amount_series.sum()) / 100000.0


def get_trade_dates(pro, trade_date, count=6):
    end_dt = datetime.strptime(trade_date, "%Y%m%d")
    start_dt = end_dt - timedelta(days=40)
    cal = pro.trade_cal(
        exchange="SSE",
        start_date=start_dt.strftime("%Y%m%d"),
        end_date=trade_date,
        is_open="1",
    )
    dates = sorted(cal["cal_date"].tolist())
    if trade_date not in dates:
        raise ValueError(f"{trade_date} is not an open trading day.")
    idx = dates.index(trade_date)
    start = max(0, idx - count + 1)
    return dates[start : idx + 1]


def fetch_indices(pro, trade_date):
    index_codes = {
        "上证指数": "000001.SH",
        "深成指": "399001.SZ",
        "创业板": "399006.SZ",
        "沪深300": "000300.SH",
    }
    rows = []
    for name, code in index_codes.items():
        df = pro.index_daily(ts_code=code, start_date=trade_date, end_date=trade_date)
        if len(df):
            row = df.iloc[0].to_dict()
            row["name"] = name
            rows.append(row)
    return pd.DataFrame(rows)


def fetch_market_day(pro, trade_date, basic=None):
    daily = pro.daily(trade_date=trade_date)
    limits = pro.stk_limit(trade_date=trade_date)
    if basic is None:
        basic = pro.stock_basic(exchange="", list_status="L", fields="ts_code,name,industry,market")
    merged = (
        daily.merge(limits[["ts_code", "up_limit", "down_limit"]], on="ts_code", how="left")
        .merge(basic, on="ts_code", how="left")
    )
    merged["is_st"] = merged["name"].apply(is_st_name)
    merged["is_up_limit"] = merged["close"].round(2) >= merged["up_limit"].round(2)
    merged["is_down_limit"] = merged["close"].round(2) <= merged["down_limit"].round(2)
    return merged


def compute_prev_premium(prev_day, current_day):
    prev_up = prev_day[(prev_day["is_up_limit"]) & (~prev_day["is_st"])][["ts_code", "close"]].rename(
        columns={"close": "prev_close"}
    )
    premium = prev_up.merge(current_day[["ts_code", "close"]], on="ts_code", how="inner")
    if premium.empty:
        return {"count": 0, "avg": None, "median": None}
    premium["premium_pct"] = (premium["close"] / premium["prev_close"] - 1.0) * 100.0
    return {
        "count": int(len(prev_up)),
        "avg": float(premium["premium_pct"].mean()),
        "median": float(premium["premium_pct"].median()),
    }


def compute_relimit_rate(prev_day, current_day):
    prev_up = prev_day[(prev_day["is_up_limit"]) & (~prev_day["is_st"])][["ts_code"]]
    cur_up = current_day[(current_day["is_up_limit"]) & (~current_day["is_st"])][["ts_code"]]
    if prev_up.empty:
        return {"count": 0, "advance": 0, "rate": None}
    adv = prev_up.merge(cur_up, on="ts_code", how="inner")
    return {
        "count": int(len(prev_up)),
        "advance": int(len(adv)),
        "rate": float(len(adv) / len(prev_up) * 100.0),
    }


def compute_board_ladder(pro, trade_dates, basic):
    frames = []
    for trade_date in reversed(trade_dates):
        day = fetch_market_day(pro, trade_date, basic)
        frames.append(day[["ts_code", "is_up_limit"]].assign(trade_date=trade_date))
    panel = pd.concat(frames, ignore_index=True)
    pivot = panel.pivot(index="ts_code", columns="trade_date", values="is_up_limit").fillna(False)

    counts = {}
    ordered_dates = list(reversed(trade_dates))
    for code, row in pivot.iterrows():
        streak = 0
        for day in ordered_dates:
            if bool(row.get(day, False)):
                streak += 1
            else:
                break
        if streak > 0:
            counts[code] = streak

    board = pd.Series(counts, name="boards").reset_index().rename(columns={"index": "ts_code"})
    board = board.merge(basic, on="ts_code", how="left")
    board = board[~board["name"].apply(is_st_name)].sort_values(["boards", "ts_code"], ascending=[False, True])
    dist = Counter(board["boards"])
    return board, dist


def classify_market(stats):
    if stats["relimit_rate"] is not None and stats["relimit_rate"] < 25 and stats["highest_board"] <= 3:
        return "分化偏弱"
    if stats["relimit_rate"] is not None and stats["relimit_rate"] >= 35 and stats["highest_board"] >= 4:
        return "主升偏强"
    return "轮动市"


def calc_emotion_score(stats):
    score = 50.0
    score += min(stats["up_limit_non_st"], 60) * 0.25
    score -= min(stats["down_limit_non_st"], 30) * 0.8
    score += min(max(stats["highest_board"] - 2, 0), 4) * 4.0
    if stats["premium_avg"] is not None:
        score += max(min(stats["premium_avg"], 5), -5) * 2.0
    if stats["relimit_rate"] is not None:
        score += (stats["relimit_rate"] - 20.0) * 0.4
    return max(0, min(100, round(score, 1)))


def top_industries(df, flag_col, topn=5):
    subset = df[(df[flag_col]) & (~df["is_st"])].copy()
    if subset.empty:
        return pd.Series(dtype=int)
    return subset["industry"].fillna("未分类").value_counts().head(topn)


def top_stocks(df, flag_col, topn=10):
    subset = df[(df[flag_col]) & (~df["is_st"])].copy()
    if subset.empty:
        return subset
    return subset.sort_values("amount", ascending=False).head(topn)


def fmt_board_dist(dist):
    parts = []
    for board in sorted(dist.keys(), reverse=True):
        parts.append(f"{board}板{dist[board]}家")
    return "，".join(parts) if parts else "无"


def infer_main_themes(up_industries):
    if up_industries.empty:
        return "无明确主线"
    return "、".join(up_industries.index[:3].tolist())


def render_review(trade_date, indices, current_day, prev_day, board_df, board_dist):
    idx_map = {row["name"]: row for _, row in indices.iterrows()}

    total_amount = yi_from_amount(current_day["amount"])
    prev_amount = yi_from_amount(prev_day["amount"])
    up_count = int((current_day["pct_chg"] > 0).sum())
    down_count = int((current_day["pct_chg"] < 0).sum())
    flat_count = int((current_day["pct_chg"] == 0).sum())
    ge5_count = int((current_day["pct_chg"] >= 5).sum())
    le5_count = int((current_day["pct_chg"] <= -5).sum())

    up_limit_non_st = int((current_day["is_up_limit"] & ~current_day["is_st"]).sum())
    down_limit_non_st = int((current_day["is_down_limit"] & ~current_day["is_st"]).sum())
    highest_board = int(board_df["boards"].max()) if len(board_df) else 0

    premium = compute_prev_premium(prev_day, current_day)
    relimit = compute_relimit_rate(prev_day, current_day)
    up_industries = top_industries(current_day, "is_up_limit")
    down_industries = top_industries(current_day, "is_down_limit")
    top_up = top_stocks(current_day, "is_up_limit", topn=8)
    top_down = top_stocks(current_day, "is_down_limit", topn=5)

    stats = {
        "up_limit_non_st": up_limit_non_st,
        "down_limit_non_st": down_limit_non_st,
        "highest_board": highest_board,
        "premium_avg": premium["avg"],
        "relimit_rate": relimit["rate"],
    }
    emotion_score = calc_emotion_score(stats)
    market_stage = classify_market(stats)
    main_themes = infer_main_themes(up_industries)

    lines = []
    lines.append(f"# {trade_date} 龙头战法复盘（剔除ST版）")
    lines.append("")
    lines.append("## 1. 市场总览")
    lines.append("")
    lines.append("| 维度 | 数值 | 结论 |")
    lines.append("|---|---:|---|")
    lines.append(f"| 上证指数涨跌幅 | `{pct(idx_map['上证指数']['pct_chg'], 2)}` | {'主板偏弱' if idx_map['上证指数']['pct_chg'] < 0 else '主板偏强'} |")
    lines.append(f"| 深成指涨跌幅 | `{pct(idx_map['深成指']['pct_chg'], 2)}` | {'深市偏强' if idx_map['深成指']['pct_chg'] > 0 else '深市偏弱'} |")
    lines.append(f"| 创业板涨跌幅 | `{pct(idx_map['创业板']['pct_chg'], 2)}` | {'弹性方向更强' if idx_map['创业板']['pct_chg'] > idx_map['上证指数']['pct_chg'] else '弹性方向一般'} |")
    lines.append(f"| 沪深300涨跌幅 | `{pct(idx_map['沪深300']['pct_chg'], 2)}` | {'权重维稳' if idx_map['沪深300']['pct_chg'] >= 0 else '权重走弱'} |")
    lines.append(f"| 两市成交额 | `{total_amount:.2f}亿` | {'高成交' if total_amount > 20000 else '成交一般'} |")
    lines.append(f"| 较前一日变化 | `{total_amount - prev_amount:+.2f}亿` | {'放量' if total_amount > prev_amount else '缩量'} |")
    lines.append(f"| 上涨家数 | `{up_count}` | {'宽度尚可' if up_count > down_count else '宽度一般'} |")
    lines.append(f"| 下跌家数 | `{down_count}` | {'分化' if down_count > 1500 else '较强'} |")
    lines.append(f"| 平盘家数 | `{flat_count}` | 正常 |")
    lines.append(f"| 涨停家数（剔除ST） | `{up_limit_non_st}` | {'活跃度中等' if up_limit_non_st >= 40 else '活跃度偏低'} |")
    lines.append(f"| 跌停家数（剔除ST） | `{down_limit_non_st}` | {'亏钱效应存在' if down_limit_non_st >= 8 else '亏钱效应可控'} |")
    lines.append(f"| 5%以上上涨家数 | `{ge5_count}` | 局部赚钱效应仍有 |")
    lines.append(f"| 5%以上下跌家数 | `{le5_count}` | 风险没有消失 |")
    lines.append(f"| 昨日涨停平均溢价 | `{pct(premium['avg'], 2)}` | {'接力亏钱' if premium['avg'] is not None and premium['avg'] < 0 else '接力赚钱'} |")
    lines.append(f"| 昨日涨停溢价中位数 | `{pct(premium['median'], 2)}` | {'大多数接力低于预期' if premium['median'] is not None and premium['median'] < 0 else '大多数接力高于预期'} |")
    lines.append(f"| 昨日涨停晋级率 | `{pct(relimit['rate'], 2)}` | {'高标晋级难' if relimit['rate'] is not None and relimit['rate'] < 25 else '晋级环境尚可'} |")
    lines.append(f"| 最高连板（剔除ST） | `{highest_board}板` | {'高度不高' if highest_board <= 3 else '高度打开'} |")
    lines.append("")
    lines.append("**市场结论**")
    lines.append(f"- 市场状态：`{market_stage}`")
    lines.append("- 风格状态：`科技弹性与权重并存，但高标接力一般`")
    lines.append("- 交易环境：`能做前排低位，不适合高标猛干`")
    lines.append("")
    lines.append("## 2. 情绪周期判断")
    lines.append("")
    lines.append("| 维度 | 数值 | 结论 |")
    lines.append("|---|---:|---|")
    lines.append(f"| 情绪得分 | `{emotion_score}/100` | {'中性偏弱' if emotion_score < 50 else '中性偏强'} |")
    lines.append(f"| 涨停 / 跌停（剔除ST） | `{up_limit_non_st} / {down_limit_non_st}` | {'有活跃度，但不强' if up_limit_non_st >= 40 and down_limit_non_st >= 5 else '一般'} |")
    lines.append(f"| 昨日涨停平均溢价 | `{pct(premium['avg'], 2)}` | {'接力资金不赚钱' if premium['avg'] is not None and premium['avg'] < 0 else '接力资金赚钱'} |")
    lines.append(f"| 昨日涨停晋级率 | `{pct(relimit['rate'], 2)}` | {'接力成功率低' if relimit['rate'] is not None and relimit['rate'] < 25 else '接力成功率尚可'} |")
    lines.append(f"| 最高连板 | `{highest_board}板` | {'没有强空间板' if highest_board <= 3 else '高度有支撑'} |")
    lines.append(f"| 非ST连板梯队 | `{fmt_board_dist(board_dist)}` | {'低位轮动为主' if highest_board <= 3 else '接力梯队存在'} |")
    lines.append(f"| 市场宽度 | `{up_count}涨 / {down_count}跌` | {'不是冰点' if up_count > 2000 else '偏冷'} |")
    lines.append(f"| 成交额变化 | `{'缩量' if total_amount < prev_amount else '放量'} {abs(total_amount - prev_amount):.2f}亿` | {'情绪没有继续扩张' if total_amount < prev_amount else '情绪扩张'} |")
    lines.append("")
    lines.append("**情绪结论**")
    lines.append(f"- 情绪定位：`{market_stage}`")
    lines.append("- 赚钱模式：`低位前排/容量首板 > 高标接力`")
    lines.append("- 明日预期：`先看接力修复，再决定是否加仓`")
    lines.append("")
    lines.append("## 3. 主线题材复盘")
    lines.append("")
    lines.append("| 题材 | 涨停家数（剔除ST） | 结论 |")
    lines.append("|---|---:|---|")
    for industry, count in up_industries.items():
        lines.append(f"| {industry} | `{count}` | {'今日最活跃方向' if count == up_industries.iloc[0] else '活跃分支'} |")
    for industry, count in down_industries.head(3).items():
        lines.append(f"| {industry} | `跌停 {count}` | 风险释放方向 |")
    lines.append("")
    lines.append("**主线结论**")
    lines.append(f"- 今日最强方向：`{main_themes}`")
    if not down_industries.empty:
        lines.append(f"- 今日最弱方向：`{'、'.join(down_industries.index[:3].tolist())}`")
    lines.append("- 市场结构：`没有绝对大主线，前排科技和低位轮动更占优`")
    lines.append("")
    lines.append("## 4. 龙头梯队梳理（剔除ST）")
    lines.append("")
    lines.append("| 梯队 | 个股 | 板数 | 地位 | 评价 |")
    lines.append("|---|---|---:|---|---|")
    shown_boards = board_df.head(8)
    for idx, row in shown_boards.iterrows():
        position = "最高板" if row["boards"] == highest_board else f"{int(row['boards'])}板前排"
        comment = "可观察" if row["boards"] >= 2 else "首板观察"
        lines.append(f"| {position} | {row['name']} | `{int(row['boards'])}板` | 前排 | {comment} |")
    lines.append("")
    lines.append("**梯队结论**")
    lines.append("- 市场总龙头：`空缺或不清晰`")
    if len(board_df):
        leaders = "、".join(board_df[board_df["boards"] == highest_board]["name"].head(3).tolist())
        lines.append(f"- 可交易高标：`{leaders}`")
    cap_leader = top_up.iloc[0]["name"] if len(top_up) else "无"
    lines.append(f"- 今日最有辨识度的容量前排：`{cap_leader}`")
    lines.append("- 结论：`今天不是高度板统治市场，而是低位前排更有价值`")
    lines.append("")
    lines.append("## 5. 核心个股逐一复盘")
    lines.append("")
    lines.append("| 个股 | 涨跌幅 | 成交额 | 身份 | 结论 |")
    lines.append("|---|---:|---:|---|---|")
    for _, row in top_up.head(5).iterrows():
        role = "科技容量核心" if row["amount"] == top_up["amount"].max() else "前排强板"
        lines.append(f"| {row['name']} | `{pct(row['pct_chg'], 2)}` | `{row['amount'] / 100000:.2f}亿` | {role} | 强，观察次日承接 |")
    for _, row in top_down.head(3).iterrows():
        lines.append(f"| {row['name']} | `{pct(row['pct_chg'], 2)}` | `{row['amount'] / 100000:.2f}亿` | 亏钱效应锚 | 回避 |")
    lines.append("")
    lines.append("**个股结论**")
    lines.append(f"- 今日最值得看的票：`{cap_leader}`")
    if len(top_down):
        lines.append(f"- 今日最值得回避的票：`{top_down.iloc[0]['name']}`")
    lines.append("- 交易核心：`做前排强板，避开弱势大面方向`")
    lines.append("")
    lines.append("## 6. 今日标准买点复盘")
    lines.append("")
    lines.append("| 买点类型 | 代表股 | 结果 | 结论 |")
    lines.append("|---|---|---|---|")
    head_names = "、".join(top_up["name"].head(3).tolist()) if len(top_up) else "无"
    high_names = "、".join(board_df[board_df["boards"] == highest_board]["name"].tolist()) if len(board_df) else "无"
    lines.append(f"| 容量首板 | {cap_leader} | 成立 | 今日最优买点类型 |")
    lines.append(f"| 前排首板 | {head_names} | 成立 | 可做 |")
    lines.append(f"| 高标接力 | {high_names} | 一般 | 不属于舒服环境 |")
    if len(top_down):
        lines.append(f"| 弱势线抄底 | {top_down.iloc[0]['name']} 等 | 不成立 | 不做 |")
    lines.append("")
    lines.append("**买点结论**")
    lines.append("- 今日最佳买点：`科技容量首板 / 前排首板`")
    lines.append("- 今日次优买点：`低位板块前排`")
    lines.append("- 今日最差买点：`高标接力、弱势线抄底`")
    lines.append("")
    lines.append("## 7. 今日标准卖点复盘")
    lines.append("")
    lines.append("| 方向 | 代表股 | 数值 | 卖点结论 |")
    lines.append("|---|---|---:|---|")
    for _, row in top_down.head(3).iterrows():
        lines.append(f"| {row['industry']} | {row['name']} | `{pct(row['pct_chg'], 2)}` | 弱势方向反抽也是卖点 |")
    lines.append(f"| 昨日涨停整体 | 非ST昨日涨停股 | `{pct(premium['avg'], 2)}` | 不及预期应先卖 |")
    lines.append(f"| 高标晋级 | 非ST昨日涨停股 | `{pct(relimit['rate'], 2)}` | 高标不值得恋战 |")
    lines.append("")
    lines.append("**卖点结论**")
    lines.append("- 今日卖出原则：`不及预期先走`")
    lines.append("- 最不该做的事：`高标硬扛`")
    lines.append("- 明日卖点纪律：`高开不强卖，冲高无承接卖，板块掉队卖`")
    lines.append("")
    lines.append("## 8. 自己的交易复盘示范")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("|---|---|")
    lines.append("| 今日适合仓位 | `1-3成` |")
    lines.append("| 今日适合笔数 | `0-2笔` |")
    lines.append("| 最大正确 | `识别出接力差，放弃高标` |")
    lines.append("| 最大错误 | `如果去接高标或抄跌停` |")
    lines.append("| 是否适合满仓 | `否` |")
    lines.append("| 是否适合激进接力 | `否` |")
    lines.append("")
    lines.append("**个人结论**")
    lines.append("- 今天正确做法：`只做前排低位，小仓`")
    lines.append("- 今天错误做法：`看见涨停不少就误判为主升`")
    lines.append("- 明天必须坚持：`先看接力修复，再决定是否加仓`")
    lines.append("")
    lines.append("## 9. 明日预案")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("|---|---|")
    lines.append(f"| 明日市场预判 | `继续分化，重点看 {main_themes} 是否有持续性` |")
    lines.append(f"| 明日主线观察 | `{main_themes}` |")
    lines.append(f"| 明日高标观察 | `{high_names}` |")
    lines.append(f"| 明日容量观察 | `{head_names}` |")
    if len(top_down):
        lines.append(f"| 明日风险锚 | `{top_down.iloc[0]['name']}` |")
    lines.append("| 明日可做买点 | `前排强承接后的继续走强` |")
    lines.append("| 明日不做情形 | `高标继续掉队，昨日涨停继续负溢价` |")
    lines.append("| 计划仓位 | `2成左右` |")
    lines.append("| 单票仓位 | `不超过1成` |")
    lines.append("| 核心原则 | `只做前排，不做后排；只做低位，不接高标` |")
    lines.append("")
    lines.append("**明日执行句**")
    lines.append("- 如果 `昨日涨停溢价转正，前排科技继续加强`，就 `小仓试错前排`")
    lines.append("- 如果 `高标继续断板，亏钱效应扩大`，就 `继续控仓`")
    lines.append("- 如果 `风险锚继续扩散`，就 `按防守思路处理`")
    lines.append("")
    lines.append("## 10. 最终一句话总结")
    lines.append("")
    lines.append(f"- 今日市场：`{market_stage}`")
    lines.append(f"- 今日主线：`{main_themes}`")
    lines.append(f"- 今日高度：`非ST最高仅{highest_board}板`")
    lines.append("- 今日机会：`前排容量首板和低位前排`")
    lines.append("- 今日风险：`高标接力、弱势方向抄底`")
    lines.append("- 明日策略：`只看前排低位，小仓试错`")
    lines.append("")
    lines.append("数据源：`Tushare Pro`")
    return "\n".join(lines)


def main():
    args = parse_args()
    pro = get_pro(args.token)
    trade_dates = get_trade_dates(pro, args.date, count=6)
    prev_date = trade_dates[-2]
    basic = pro.stock_basic(exchange="", list_status="L", fields="ts_code,name,industry,market")
    indices = fetch_indices(pro, args.date)
    current_day = fetch_market_day(pro, args.date, basic)
    prev_day = fetch_market_day(pro, prev_date, basic)
    board_df, board_dist = compute_board_ladder(pro, trade_dates, basic)

    content = render_review(args.date, indices, current_day, prev_day, board_df, board_dist)

    output = args.output or os.path.join(
        os.getcwd(),
        "reviews",
        f"{args.date}_dragon_review.md",
    )
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(content)
    print(output)


if __name__ == "__main__":
    main()
