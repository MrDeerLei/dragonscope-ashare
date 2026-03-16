from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import DB_PATH
from app.database import init_db


def main():
    db_path = init_db(DB_PATH)
    print(db_path)


if __name__ == "__main__":
    main()
