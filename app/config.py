from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = DATA_DIR / "db"
EXPORT_DIR = DATA_DIR / "exports"
THEME_RULES_PATH = DATA_DIR / "theme_rules.json"
THEME_RULES_EXAMPLE_PATH = DATA_DIR / "theme_rules.example.json"
APP_SETTINGS_PATH = DATA_DIR / "app_settings.json"
APP_SETTINGS_EXAMPLE_PATH = DATA_DIR / "app_settings.example.json"
REVIEWS_DIR = PROJECT_ROOT / "reviews"
DAILY_REVIEWS_DIR = REVIEWS_DIR / "daily"
PERIOD_REVIEWS_DIR = REVIEWS_DIR / "period"
COMPARE_REVIEWS_DIR = REVIEWS_DIR / "compare"
DB_PATH = DB_DIR / "dragonscope.db"


def ensure_directories():
    for path in [
        DATA_DIR,
        DB_DIR,
        EXPORT_DIR,
        REVIEWS_DIR,
        DAILY_REVIEWS_DIR,
        PERIOD_REVIEWS_DIR,
        COMPARE_REVIEWS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
