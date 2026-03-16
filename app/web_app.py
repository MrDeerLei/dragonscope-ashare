import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import DB_PATH, PROJECT_ROOT
from app.database import connect_db, init_db


TEMPLATES_DIR = PROJECT_ROOT / "app" / "ui" / "templates"

app = FastAPI(title="DragonScope-AShare Dashboard", version="0.5.0-dev")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _query_df(sql: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    with connect_db(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def _latest_trade_date() -> str | None:
    df = _query_df("SELECT trade_date FROM daily_market_stats ORDER BY trade_date DESC LIMIT 1")
    if df.empty:
        return None
    return str(df.iloc[0]["trade_date"])


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _upsert_daily_review(
    trade_date: str,
    main_theme: str,
    secondary_theme: str,
    market_leader: str,
    capacity_core: str,
    risk_anchor: str,
    best_setup: str,
    bad_setup: str,
    tomorrow_plan: str,
    position_plan: str,
    review_status: str,
):
    main_theme = _safe_text(main_theme)
    secondary_theme = _safe_text(secondary_theme)
    market_leader = _safe_text(market_leader)
    capacity_core = _safe_text(capacity_core)
    risk_anchor = _safe_text(risk_anchor)
    best_setup = _safe_text(best_setup)
    bad_setup = _safe_text(bad_setup)
    tomorrow_plan = _safe_text(tomorrow_plan)
    position_plan = _safe_text(position_plan)
    review_status = _safe_text(review_status) or "active"
    with connect_db(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO daily_review (
                trade_date, market_stage, main_theme, secondary_theme, market_leader,
                capacity_core, risk_anchor, best_setup, bad_setup, tomorrow_plan, position_plan, review_status
            )
            VALUES (
                ?, COALESCE((SELECT market_stage FROM daily_market_stats WHERE trade_date = ?), ''),
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(trade_date) DO UPDATE SET
                main_theme = excluded.main_theme,
                secondary_theme = excluded.secondary_theme,
                market_leader = excluded.market_leader,
                capacity_core = excluded.capacity_core,
                risk_anchor = excluded.risk_anchor,
                best_setup = excluded.best_setup,
                bad_setup = excluded.bad_setup,
                tomorrow_plan = excluded.tomorrow_plan,
                position_plan = excluded.position_plan,
                review_status = excluded.review_status
            """,
            (
                trade_date,
                trade_date,
                main_theme,
                secondary_theme,
                market_leader,
                capacity_core,
                risk_anchor,
                best_setup,
                bad_setup,
                tomorrow_plan,
                position_plan,
                review_status,
            ),
        )
        conn.commit()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    init_db(DB_PATH)
    latest = _latest_trade_date()
    latest_stats = None
    latest_review = None
    theme_top = []
    leader_top = []
    inflections = []
    recent_days = []
    if latest:
        stats_df = _query_df("SELECT * FROM daily_market_stats WHERE trade_date = ?", (latest,))
        review_df = _query_df("SELECT * FROM daily_review WHERE trade_date = ?", (latest,))
        theme_df = _query_df(
            "SELECT theme_name, theme_rank, theme_stage, limit_up_count FROM daily_theme_stats WHERE trade_date = ? ORDER BY theme_rank LIMIT 5",
            (latest,),
        )
        leader_df = _query_df(
            "SELECT name, role_type, theme_name, board_count, leader_score FROM daily_leader_stats WHERE trade_date = ? ORDER BY is_market_leader DESC, is_theme_leader DESC, leader_score DESC LIMIT 8",
            (latest,),
        )
        day_df = _query_df(
            "SELECT * FROM day_compare_cache ORDER BY trade_date DESC LIMIT 5",
        )
        recent_df = _query_df(
            "SELECT trade_date, emotion_score, market_stage, limit_up_non_st, limit_down_non_st FROM daily_market_stats ORDER BY trade_date DESC LIMIT 10"
        )
        latest_stats = stats_df.iloc[0].to_dict() if len(stats_df) else None
        latest_review = review_df.iloc[0].to_dict() if len(review_df) else None
        theme_top = theme_df.to_dict("records")
        leader_top = leader_df.to_dict("records")
        inflections = day_df.to_dict("records")
        recent_days = recent_df.to_dict("records")
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "latest_date": latest,
            "latest_stats": latest_stats,
            "latest_review": latest_review,
            "theme_top": theme_top,
            "leader_top": leader_top,
            "inflections": inflections,
            "recent_days": recent_days,
        },
    )


@app.get("/daily/{trade_date}", response_class=HTMLResponse)
def daily_page(request: Request, trade_date: str):
    market_df = _query_df("SELECT * FROM daily_market_stats WHERE trade_date = ?", (trade_date,))
    review_df = _query_df("SELECT * FROM daily_review WHERE trade_date = ?", (trade_date,))
    theme_df = _query_df(
        "SELECT * FROM daily_theme_stats WHERE trade_date = ? ORDER BY theme_rank",
        (trade_date,),
    )
    leader_df = _query_df(
        "SELECT * FROM daily_leader_stats WHERE trade_date = ? ORDER BY is_market_leader DESC, is_theme_leader DESC, leader_score DESC",
        (trade_date,),
    )
    if market_df.empty:
        return templates.TemplateResponse(request, "empty.html", {"message": f"{trade_date} 没有同步数据"})
    market_row = market_df.iloc[0].to_dict()
    review_row = review_df.iloc[0].to_dict() if len(review_df) else {}
    board_dist = {}
    if market_row.get("board_dist_json"):
        board_dist = json.loads(market_row["board_dist_json"])
    return templates.TemplateResponse(
        request,
        "daily.html",
        {
            "trade_date": trade_date,
            "market": market_row,
            "review": review_row,
            "themes": theme_df.to_dict("records"),
            "leaders": leader_df.to_dict("records"),
            "board_dist": board_dist,
        },
    )


@app.post("/daily/{trade_date}/edit")
def daily_edit(
    trade_date: str,
    main_theme: str = Form(""),
    secondary_theme: str = Form(""),
    market_leader: str = Form(""),
    capacity_core: str = Form(""),
    risk_anchor: str = Form(""),
    best_setup: str = Form(""),
    bad_setup: str = Form(""),
    tomorrow_plan: str = Form(""),
    position_plan: str = Form(""),
):
    _upsert_daily_review(
        trade_date=trade_date,
        main_theme=main_theme,
        secondary_theme=secondary_theme,
        market_leader=market_leader,
        capacity_core=capacity_core,
        risk_anchor=risk_anchor,
        best_setup=best_setup,
        bad_setup=bad_setup,
        tomorrow_plan=tomorrow_plan,
        position_plan=position_plan,
        review_status="active",
    )
    return RedirectResponse(url=f"/daily/{trade_date}", status_code=303)


@app.post("/daily/{trade_date}/archive")
def daily_archive(trade_date: str):
    with connect_db(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO daily_review (trade_date, market_stage, review_status)
            VALUES (?, COALESCE((SELECT market_stage FROM daily_market_stats WHERE trade_date = ?), ''), 'archived')
            ON CONFLICT(trade_date) DO UPDATE SET review_status = 'archived'
            """,
            (trade_date, trade_date),
        )
        conn.commit()
    return RedirectResponse(url=f"/daily/{trade_date}", status_code=303)


@app.post("/daily/{trade_date}/unarchive")
def daily_unarchive(trade_date: str):
    with connect_db(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO daily_review (trade_date, market_stage, review_status)
            VALUES (?, COALESCE((SELECT market_stage FROM daily_market_stats WHERE trade_date = ?), ''), 'active')
            ON CONFLICT(trade_date) DO UPDATE SET review_status = 'active'
            """,
            (trade_date, trade_date),
        )
        conn.commit()
    return RedirectResponse(url=f"/daily/{trade_date}", status_code=303)


@app.get("/period", response_class=HTMLResponse)
def period_page(
    request: Request,
    start: str = Query(..., description="YYYYMMDD"),
    end: str = Query(..., description="YYYYMMDD"),
    period_type: str = Query("custom"),
):
    period_id = f"{period_type}:{start}:{end}"
    period_df = _query_df("SELECT * FROM period_review WHERE period_id = ?", (period_id,))
    theme_df = _query_df(
        "SELECT * FROM period_theme_compare WHERE period_id = ? ORDER BY appear_days DESC, avg_theme_score DESC LIMIT 20",
        (period_id,),
    )
    leader_df = _query_df(
        "SELECT * FROM period_leader_compare WHERE period_id = ? ORDER BY leader_days DESC, highest_board DESC LIMIT 20",
        (period_id,),
    )
    matrix_df = _query_df(
        "SELECT * FROM day_compare_cache WHERE trade_date BETWEEN ? AND ? ORDER BY trade_date",
        (start, end),
    )
    if period_df.empty:
        return templates.TemplateResponse(request, "empty.html", {"message": f"{period_id} 没有周期复盘，请先运行 generate_period_review.py"})
    period_row = period_df.iloc[0].to_dict()
    return templates.TemplateResponse(
        request,
        "period.html",
        {
            "period_id": period_id,
            "period": period_row,
            "themes": theme_df.to_dict("records"),
            "leaders": leader_df.to_dict("records"),
            "matrix": matrix_df.to_dict("records"),
        },
    )


@app.get("/compare/matrix", response_class=HTMLResponse)
def compare_matrix_page(
    request: Request,
    start: str = Query(..., description="YYYYMMDD"),
    end: str = Query(..., description="YYYYMMDD"),
):
    matrix_df = _query_df(
        "SELECT * FROM day_compare_cache WHERE trade_date BETWEEN ? AND ? ORDER BY trade_date",
        (start, end),
    )
    if matrix_df.empty:
        return templates.TemplateResponse(request, "empty.html", {"message": f"{start}~{end} 没有对比矩阵，请先运行 generate_compare_matrix.py"})
    return templates.TemplateResponse(
        request,
        "compare_matrix.html",
        {
            "start": start,
            "end": end,
            "matrix": matrix_df.to_dict("records"),
        },
    )


@app.get("/history", response_class=HTMLResponse)
def history_page(
    request: Request,
    start: str | None = Query(None, description="YYYYMMDD"),
    end: str | None = Query(None, description="YYYYMMDD"),
    theme: str | None = Query(None, description="主线关键字"),
    leader: str | None = Query(None, description="龙头关键字"),
    status: str = Query("all", description="all/active/archived"),
):
    latest = _latest_trade_date()
    sql = """
    SELECT
        m.trade_date,
        m.market_stage,
        m.emotion_score,
        m.limit_up_non_st,
        m.limit_down_non_st,
        COALESCE(r.main_theme, '') AS main_theme,
        COALESCE(r.market_leader, '') AS market_leader,
        COALESCE(r.review_status, 'active') AS review_status
    FROM daily_market_stats m
    LEFT JOIN daily_review r ON m.trade_date = r.trade_date
    WHERE 1 = 1
    """
    params: list[Any] = []
    if start:
        sql += " AND m.trade_date >= ?"
        params.append(start)
    if end:
        sql += " AND m.trade_date <= ?"
        params.append(end)
    if theme:
        sql += " AND COALESCE(r.main_theme, '') LIKE ?"
        params.append(f"%{theme.strip()}%")
    if leader:
        sql += " AND COALESCE(r.market_leader, '') LIKE ?"
        params.append(f"%{leader.strip()}%")
    if status in {"active", "archived"}:
        sql += " AND COALESCE(r.review_status, 'active') = ?"
        params.append(status)
    sql += " ORDER BY m.trade_date DESC LIMIT 300"
    rows = _query_df(sql, tuple(params))
    return templates.TemplateResponse(
        request,
        "history.html",
        {
            "latest_date": latest,
            "rows": rows.to_dict("records"),
            "q_start": start or "",
            "q_end": end or "",
            "q_theme": theme or "",
            "q_leader": leader or "",
            "q_status": status,
        },
    )
