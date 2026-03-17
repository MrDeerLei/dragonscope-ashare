from pathlib import Path
import sys

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    uvicorn.run("app.web_app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
