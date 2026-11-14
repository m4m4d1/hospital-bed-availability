"""Export a static snapshot of the API for the GitHub Pages demo.

    python -m app.export_demo        # writes web/data/demo.json

The dashboard reads this file when no API is available, so the same web/
folder works both behind the FastAPI server and as a static site. The static
demo cannot answer arbitrary "nearest free bed" questions, so the answers for
every finder preset and ward are exported in advance.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from . import config, simulator

OUT = Path(__file__).resolve().parent.parent / "web" / "data" / "demo.json"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        config.DB_PATH = Path(tmp) / "demo.db"
        os.environ["HB_SIMULATE"] = "0"
        simulator.backfill(hours=72)
        from .main import app

        paths = ["facilities", "summary", "regions?hours=72", "alerts?hours=24&level=high", "meta"]
        paths += [f"facilities/{f['id']}/history?hours=72" for f in config.FACILITIES]
        paths += [f"nearest?lat={p['lat']}&lon={p['lon']}&ward={w}"
                  for p in config.SEARCH_PRESETS for w in config.WARDS]
        with TestClient(app) as client:
            api = {p: client.get(f"/api/{p}").json() for p in paths}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "api": api}, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
