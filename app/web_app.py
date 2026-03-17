import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

import pandas as pd
from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import DB_PATH, PROJECT_ROOT
from app.database import connect_db, init_db
from app.settings_store import get_tushare_token, llm_config_status, load_settings, save_settings


TEMPLATES_DIR = PROJECT_ROOT / "app" / "ui" / "templates"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

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


def _normalize_trade_date(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        return text
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text.replace("-", "")
    return None


def _to_date_input(trade_date: str | None) -> str:
    normalized = _normalize_trade_date(trade_date)
    if not normalized:
        return ""
    return f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:8]}"


def _run_script(*args: str) -> tuple[bool, str]:
    cmd = [sys.executable, *args]
    env = os.environ.copy()
    token = get_tushare_token()
    if not token:
        return False, "未配置 Tushare Token，请先到“设置中心”填写。"
    env["TUSHARE_TOKEN"] = token
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        output = (completed.stdout or "").strip()
        if output:
            return True, output.splitlines()[-1]
        return True, "执行成功"
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        msg = stderr or stdout or str(exc)
        return False, msg.splitlines()[-1][:240]


def _upsert_custom_summary(trade_date: str, custom_summary: str):
    with connect_db(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO daily_review (trade_date, market_stage, review_markdown, review_status)
            VALUES (?, COALESCE((SELECT market_stage FROM daily_market_stats WHERE trade_date = ?), ''), ?, 'active')
            ON CONFLICT(trade_date) DO UPDATE SET
                review_markdown = excluded.review_markdown
            """,
            (trade_date, trade_date, _safe_text(custom_summary)),
        )
        conn.commit()


def _load_recent_trade_dates(anchor_trade_date: str | None, limit: int = 22) -> list[str]:
    if anchor_trade_date:
        start = (datetime.strptime(anchor_trade_date, "%Y%m%d") - timedelta(days=60)).strftime("%Y%m%d")
        try:
            from app.tushare_data import get_pro

            token = get_tushare_token()
            if token:
                pro = get_pro(token)
                cal = pro.trade_cal(exchange="SSE", start_date=start, end_date=anchor_trade_date, is_open="1")
                dates = sorted(cal["cal_date"].astype(str).tolist())
                if dates:
                    return dates[-limit:]
        except Exception:
            pass
    df = _query_df("SELECT trade_date FROM daily_market_stats ORDER BY trade_date DESC LIMIT ?", (limit,))
    dates = [str(v) for v in df["trade_date"].tolist()]
    dates.reverse()
    return dates


def _build_trade_calendar(anchor_trade_date: str | None) -> list[dict[str, Any]]:
    dates = _load_recent_trade_dates(anchor_trade_date, limit=22)
    if not dates:
        return []
    placeholders = ",".join(["?"] * len(dates))
    sql = f"""
    SELECT
        d.trade_date,
        CASE WHEN m.trade_date IS NULL THEN 0 ELSE 1 END AS has_market_stats,
        CASE WHEN r.trade_date IS NULL THEN 0 ELSE 1 END AS has_review_row,
        COALESCE(r.review_status, 'active') AS review_status
    FROM (
        SELECT ? AS trade_date
        {"".join([" UNION ALL SELECT ?" for _ in range(len(dates) - 1)])}
    ) d
    LEFT JOIN daily_market_stats m ON d.trade_date = m.trade_date
    LEFT JOIN daily_review r ON d.trade_date = r.trade_date
    ORDER BY d.trade_date DESC
    """
    rows = _query_df(sql, tuple(dates)).to_dict("records")
    for row in rows:
        row["trade_date_input"] = _to_date_input(str(row["trade_date"]))
    return rows


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
            "today_date": datetime.now().strftime("%Y%m%d"),
            "page_msg": request.query_params.get("msg", ""),
        },
    )


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    settings = load_settings()
    llm = settings.get("llm", {})
    model_options = [
        "gpt-5-mini",
        "gpt-5",
        "gpt-4.1",
        "deepseek-chat",
        "qwen-plus",
        "glm-4.5",
    ]
    selected_model = str(llm.get("model", "gpt-5-mini")).strip()
    custom_model = ""
    if selected_model and selected_model not in model_options:
        custom_model = selected_model
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "settings": settings,
            "model_options": model_options,
            "selected_model": selected_model if selected_model in model_options else "",
            "custom_model": custom_model,
            "page_msg": request.query_params.get("msg", ""),
        },
    )


@app.post("/settings/save")
def save_settings_page(
    tushare_token: str = Form(""),
    llm_provider: str = Form("openai-compatible"),
    llm_base_url: str = Form(""),
    llm_model: str = Form(""),
    llm_model_custom: str = Form(""),
    llm_api_key: str = Form(""),
    llm_temperature: str = Form("0.2"),
    llm_max_tokens: str = Form("1200"),
):
    settings = load_settings()
    model = _safe_text(llm_model_custom) or _safe_text(llm_model) or "gpt-5-mini"
    try:
        temperature = float(llm_temperature)
    except Exception:
        temperature = 0.2
    try:
        max_tokens = int(float(llm_max_tokens))
    except Exception:
        max_tokens = 1200
    settings["tushare"] = {"token": _safe_text(tushare_token)}
    settings["llm"] = {
        "provider": _safe_text(llm_provider) or "openai-compatible",
        "base_url": _safe_text(llm_base_url),
        "model": model,
        "api_key": _safe_text(llm_api_key),
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    save_settings(settings)
    return RedirectResponse(url="/settings?msg=" + quote("设置已保存"), status_code=303)


@app.post("/ops/run-daily")
def run_daily_pipeline(trade_date: str = Form(...)):
    normalized = _normalize_trade_date(trade_date)
    if not normalized:
        return RedirectResponse(url="/?msg=" + quote("交易日格式错误，请使用 YYYYMMDD 或 YYYY-MM-DD"), status_code=303)
    ok_sync, sync_msg = _run_script(str(SCRIPTS_DIR / "sync_day.py"), "--date", normalized)
    if not ok_sync:
        return RedirectResponse(url=f"/daily/{normalized}?msg=" + quote(f"采集失败：{sync_msg}"), status_code=303)
    ok_review, review_msg = _run_script(str(SCRIPTS_DIR / "generate_daily_review_from_db.py"), "--date", normalized)
    if not ok_review:
        return RedirectResponse(url=f"/daily/{normalized}?msg=" + quote(f"复盘生成失败：{review_msg}"), status_code=303)
    return RedirectResponse(url=f"/daily/{normalized}?msg=" + quote(f"已完成采集+复盘：{sync_msg}"), status_code=303)


@app.post("/ops/create-review")
def create_daily_review(trade_date: str = Form(...)):
    normalized = _normalize_trade_date(trade_date)
    if not normalized:
        return RedirectResponse(url="/?msg=" + quote("交易日格式错误，请使用 YYYYMMDD 或 YYYY-MM-DD"), status_code=303)
    ok_review, review_msg = _run_script(str(SCRIPTS_DIR / "generate_daily_review_from_db.py"), "--date", normalized)
    if not ok_review:
        return RedirectResponse(url=f"/daily/{normalized}?msg=" + quote(f"复盘生成失败：{review_msg}"), status_code=303)
    return RedirectResponse(url=f"/daily/{normalized}?msg=" + quote(f"复盘文档已生成：{review_msg}"), status_code=303)


@app.get("/daily", response_class=HTMLResponse)
def daily_page_query(request: Request, date: str | None = Query(None)):
    normalized = _normalize_trade_date(date) or _latest_trade_date()
    if not normalized:
        return templates.TemplateResponse(request, "empty.html", {"message": "暂无可查看交易日，请先同步数据。"})
    return RedirectResponse(url=f"/daily/{normalized}", status_code=303)


@app.get("/daily/{trade_date}", response_class=HTMLResponse)
def daily_page(request: Request, trade_date: str):
    trade_date = _normalize_trade_date(trade_date) or trade_date
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
    market_row = market_df.iloc[0].to_dict() if len(market_df) else None
    review_row = review_df.iloc[0].to_dict() if len(review_df) else {}
    board_dist = {}
    if market_row and market_row.get("board_dist_json"):
        board_dist = json.loads(market_row["board_dist_json"])
    llm_ready, llm_msg = llm_config_status()
    calendar_rows = _build_trade_calendar(trade_date)
    page_msg = request.query_params.get("msg", "")
    return templates.TemplateResponse(
        request,
        "daily.html",
        {
            "trade_date": trade_date,
            "trade_date_input": _to_date_input(trade_date),
            "market": market_row,
            "review": review_row,
            "themes": theme_df.to_dict("records"),
            "leaders": leader_df.to_dict("records"),
            "board_dist": board_dist,
            "calendar_rows": calendar_rows,
            "llm_ready": llm_ready,
            "llm_msg": llm_msg,
            "page_msg": page_msg,
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


@app.post("/daily/{trade_date}/custom-summary")
def daily_custom_summary(trade_date: str, custom_summary: str = Form("")):
    _upsert_custom_summary(trade_date, custom_summary)
    return RedirectResponse(url=f"/daily/{trade_date}?msg=" + quote("自定义总结已保存"), status_code=303)


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
