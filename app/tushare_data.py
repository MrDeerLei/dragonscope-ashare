import os
import time
from datetime import datetime, timedelta

import pandas as pd
import tushare as ts


INDEX_CODES = {
    "上证指数": "000001.SH",
    "深成指": "399001.SZ",
    "创业板": "399006.SZ",
    "沪深300": "000300.SH",
}


def get_pro(token: str):
    if not token:
        raise ValueError("Missing Tushare token. Pass --token or set TUSHARE_TOKEN.")
    for key in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
        os.environ.pop(key, None)
    ts.set_token(token)
    return ts.pro_api(timeout=30)


def _call_with_retry(func, retries=3, delay=1.0, **kwargs):
    last_error = None
    for attempt in range(retries):
        try:
            return func(**kwargs)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == retries - 1:
                raise
            time.sleep(delay * (attempt + 1))
    raise last_error


def get_trade_dates(pro, trade_date: str, count: int = 6):
    end_dt = datetime.strptime(trade_date, "%Y%m%d")
    start_dt = end_dt - timedelta(days=60)
    cal = _call_with_retry(
        pro.trade_cal,
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
    selected = dates[start : idx + 1]
    prev_trade_date = selected[-2] if len(selected) >= 2 else None
    return selected, prev_trade_date


def fetch_stock_basic(pro):
    return _call_with_retry(
        pro.stock_basic,
        exchange="",
        list_status="L",
        fields="ts_code,name,industry,market,list_status",
    )


def fetch_indices(pro, trade_date: str):
    rows = []
    for name, code in INDEX_CODES.items():
        df = _call_with_retry(pro.index_daily, ts_code=code, start_date=trade_date, end_date=trade_date)
        if len(df):
            row = df.iloc[0].to_dict()
            row["name"] = name
            rows.append(row)
    return pd.DataFrame(rows)


def fetch_market_day(pro, trade_date: str, basic: pd.DataFrame | None = None):
    daily = _call_with_retry(pro.daily, trade_date=trade_date)
    limits = _call_with_retry(pro.stk_limit, trade_date=trade_date)
    if basic is None:
        basic = fetch_stock_basic(pro)
    merged = (
        daily.merge(limits[["ts_code", "up_limit", "down_limit"]], on="ts_code", how="left")
        .merge(basic[["ts_code", "name", "industry", "market", "list_status"]], on="ts_code", how="left")
    )
    return merged
