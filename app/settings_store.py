import json
import os
from copy import deepcopy
from typing import Any

from app.config import APP_SETTINGS_PATH, PROJECT_ROOT


LEGACY_LLM_CONFIG_PATH = PROJECT_ROOT / "data" / "llm_config.json"

DEFAULT_SETTINGS = {
    "tushare": {
        "token": "",
    },
    "llm": {
        "provider": "openai-compatible",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-5-mini",
        "api_key": "",
        "temperature": 0.2,
        "max_tokens": 1200,
    },
}


def _deep_merge_dict(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_settings() -> dict[str, Any]:
    settings = deepcopy(DEFAULT_SETTINGS)
    if APP_SETTINGS_PATH.exists():
        try:
            user_settings = json.loads(APP_SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(user_settings, dict):
                settings = _deep_merge_dict(settings, user_settings)
        except Exception:
            pass
    if LEGACY_LLM_CONFIG_PATH.exists():
        try:
            legacy = json.loads(LEGACY_LLM_CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(legacy, dict):
                settings["llm"] = _deep_merge_dict(settings["llm"], legacy)
        except Exception:
            pass
    env_token = os.getenv("TUSHARE_TOKEN", "").strip()
    if env_token and not str(settings.get("tushare", {}).get("token", "")).strip():
        settings["tushare"]["token"] = env_token
    return settings


def save_settings(settings: dict[str, Any]):
    APP_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APP_SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def get_tushare_token() -> str:
    settings = load_settings()
    token = str(settings.get("tushare", {}).get("token", "")).strip()
    if token:
        return token
    return os.getenv("TUSHARE_TOKEN", "").strip()


def get_llm_config() -> dict[str, Any]:
    settings = load_settings()
    return settings.get("llm", {})


def llm_config_status() -> tuple[bool, str]:
    llm = get_llm_config()
    endpoint = str(llm.get("base_url", "")).strip()
    token = str(llm.get("api_key", "")).strip()
    model = str(llm.get("model", "")).strip()
    if endpoint and token and model:
        return True, f"已配置模型：{model}"
    return False, "模型配置未完整，请到“设置中心”填写 base_url / model / api_key。"
