import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.settings_store import get_tushare_token


def parse_args():
    parser = argparse.ArgumentParser(description="Run daily sync + daily review generation.")
    parser.add_argument("--date", default="", help="Trade date YYYYMMDD, default=today")
    return parser.parse_args()


def normalize_trade_date(date_text: str) -> str:
    text = (date_text or "").strip()
    if not text:
        return datetime.now().strftime("%Y%m%d")
    if len(text) == 8 and text.isdigit():
        return text
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text.replace("-", "")
    raise ValueError("date format must be YYYYMMDD or YYYY-MM-DD")


def run_step(cmd: list[str]):
    completed = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        message = stderr or stdout or "unknown error"
        raise RuntimeError(message)
    if completed.stdout:
        print(completed.stdout.strip().splitlines()[-1])


def main():
    token = get_tushare_token() or os.getenv("TUSHARE_TOKEN", "").strip()
    if not token:
        raise ValueError("Missing Tushare token. Please configure it in data/app_settings.json or export TUSHARE_TOKEN.")
    os.environ["TUSHARE_TOKEN"] = token

    args = parse_args()
    trade_date = normalize_trade_date(args.date)

    run_step([sys.executable, "scripts/sync_day.py", "--date", trade_date])
    run_step([sys.executable, "scripts/generate_daily_review_from_db.py", "--date", trade_date])
    print(f"daily pipeline done: {trade_date}")


if __name__ == "__main__":
    main()
