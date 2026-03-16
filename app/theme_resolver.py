import json
from pathlib import Path

import pandas as pd

from app.config import THEME_RULES_EXAMPLE_PATH, THEME_RULES_PATH


def load_theme_rules():
    path = THEME_RULES_PATH if THEME_RULES_PATH.exists() else THEME_RULES_EXAMPLE_PATH
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def apply_theme_mapping(df: pd.DataFrame, rules: dict | None = None):
    if df.empty:
        return df
    rules = rules or {}
    result = df.copy()
    resolved = result.apply(lambda row: _resolve_row_theme(row, rules), axis=1, result_type="expand")
    resolved.columns = ["theme_name", "theme_source"]
    result["theme_name"] = resolved["theme_name"]
    result["theme_source"] = resolved["theme_source"]
    return result


def _resolve_row_theme(row, rules: dict):
    ts_code = str(row.get("ts_code", "") or "")
    name = str(row.get("name", "") or "")
    industry = str(row.get("industry", "") or "")
    market = str(row.get("market", "") or "")

    stock_themes = rules.get("stock_themes", {})
    if ts_code in stock_themes:
        return stock_themes[ts_code], "stock_code"
    if name in stock_themes:
        return stock_themes[name], "stock_name"

    text = f"{name} {industry} {market}"
    for item in rules.get("keyword_themes", []):
        theme = item.get("theme")
        keywords = item.get("keywords", [])
        if theme and any(keyword and keyword in text for keyword in keywords):
            return theme, "keyword"

    industry_aliases = rules.get("industry_aliases", {})
    if industry in industry_aliases:
        return industry_aliases[industry], "industry_alias"

    if industry:
        return industry, "industry"
    return "未分类", "fallback"
