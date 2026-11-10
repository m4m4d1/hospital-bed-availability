"""REST API (and, once the web/ folder exists, the dashboard).

    uvicorn app.main:app --reload      # then open http://localhost:8000 and /docs

Environment variables:
    HB_DB             SQLite file (default data/beds.db)
    HB_SIMULATE       1 (default) to add simulated snapshots every HB_SIM_INTERVAL seconds
    HB_SIM_INTERVAL   seconds between simulated snapshots (default 60)
    HB_API_KEY        if set, POST /api/snapshots requires the header X-API-Key
"""
import asyncio
import os
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from . import __version__, beds, db, simulator
from .config import ALERT_BOR, FACILITIES, FACILITIES_BY_ID, SEARCH_PRESETS, STATUS_BANDS, TYPES, WARDS
from .models import SnapshotIn

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
WARD_PATTERN = "^(" + "|".join(WARDS) + ")$"


async def simulate_forever(interval: int) -> None:
    rng = random.Random()
    while True:
        await asyncio.sleep(interval)
        now = datetime.now(timezone.utc)
        db.insert_snapshots(simulator.next_snapshots(db.latest(), now, rng, interval / 60))


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    task = None
    if os.environ.get("HB_SIMULATE", "1") == "1":
        if db.count() == 0:
            simulator.backfill(hours=72)
        task = asyncio.create_task(simulate_forever(int(os.environ.get("HB_SIM_INTERVAL", "60"))))
    yield
    if task:
        task.cancel()


app = FastAPI(
    title="Hospital Bed & Puskesmas Availability System",
    description="Free beds by ward, bed occupancy rate (BOR), regional trends, nearest free bed and "
                "alerts for Indonesian hospitals and puskesmas. Demo facilities are fictional.",
    version=__version__,
    lifespan=lifespan,
)


def facility_views() -> list[dict]:
    latest = db.latest()
    return [beds.facility_view(f, latest.get(f["id"])) for f in FACILITIES]


def known(facility_id: str) -> dict:
    if facility_id not in FACILITIES_BY_ID:
        raise HTTPException(404, f"unknown facility '{facility_id}'")
    return FACILITIES_BY_ID[facility_id]


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "snapshots": db.count()}


@app.get("/api/meta")
def meta() -> dict:
    """Wards, facility types, status bands and finder presets, for building a UI."""
    return {"wards": WARDS, "types": TYPES, "status_bands": STATUS_BANDS, "alert_bor": ALERT_BOR,
            "presets": SEARCH_PRESETS,
            "note": "Facility names are fictional and bed counts are simulated."}


@app.get("/api/facilities")
def facilities() -> list[dict]:
    return facility_views()


@app.get("/api/facilities/{facility_id}")
def facility(facility_id: str) -> dict:
    f = known(facility_id)
    return beds.facility_view(f, db.latest().get(facility_id))


@app.get("/api/facilities/{facility_id}/history")
def facility_history(facility_id: str, hours: int = Query(72, ge=1, le=24 * 30)) -> list[dict]:
    known(facility_id)
    return beds.facility_history(db.history(facility_id, hours))


@app.get("/api/summary")
def summary() -> dict:
    views = [f for f in facility_views() if f["total"]]
    counts = {b["key"]: 0 for b in STATUS_BANDS}
    for f in views:
        counts[f["total"]["status"]] += 1
    free_by_ward = {w: 0 for w in WARDS}
    capacity_by_ward = {w: 0 for w in WARDS}
    for f in views:
        for w in f["wards"]:
            free_by_ward[w["ward"]] += w["free"]
            capacity_by_ward[w["ward"]] += w["capacity"]
    capacity = sum(f["total"]["capacity"] for f in views)
    occupied = sum(f["total"]["occupied"] for f in views)
    busiest = max(views, key=lambda f: f["total"]["bor"], default=None)
    day = db.history(hours=24)
    return {
        "facilities": len(FACILITIES),
        "reporting": len(views),
        "capacity": capacity,
        "occupied": occupied,
        "free": capacity - occupied,
        "bor": beds.bor(occupied, capacity),
        "status_counts": counts,
        "free_by_ward": free_by_ward,
        "capacity_by_ward": capacity_by_ward,
        "full_wards": sum(f["total"]["full_wards"] for f in views),
        "busiest": {"facility_id": busiest["id"], "bor": busiest["total"]["bor"]} if busiest else None,
        "admissions_24h": sum(r["admissions"] for r in day),
        "discharges_24h": sum(r["discharges"] for r in day),
        "alerts_24h": len(beds.alerts(day)),
    }


@app.get("/api/regions")
def regions(hours: int = Query(72, ge=1, le=24 * 30)) -> list[dict]:
    """Occupancy per province with change over 24 hours and an hourly trend."""
    return beds.regions(db.history(hours=hours))


@app.get("/api/nearest")
def nearest(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180),
            ward: str = Query(..., pattern=WARD_PATTERN), limit: int = Query(5, ge=1, le=20)) -> dict:
    """Closest facilities with at least one free bed in `ward` (straight-line distance)."""
    return {"query": {"lat": lat, "lon": lon, "ward": ward},
            "results": beds.nearest(facility_views(), lat, lon, ward, limit)}


@app.get("/api/alerts")
def alerts(hours: int = Query(24, ge=1, le=24 * 30),
           level: str = Query("high", pattern="^(high|full)$")) -> list[dict]:
    return beds.alerts(db.history(hours=hours), level)[:200]


@app.post("/api/snapshots", status_code=201)
def ingest(snapshot: SnapshotIn, x_api_key: str | None = Header(None)) -> dict:
    """Store a ward's bed count from a hospital information system and return its status."""
    key = os.environ.get("HB_API_KEY")
    if key and x_api_key != key:
        raise HTTPException(401, "invalid or missing X-API-Key")
    row = snapshot.model_dump()
    row["timestamp"] = row["timestamp"] or datetime.now(timezone.utc)
    db.insert_snapshots([row])
    return beds.ward_view({**row, "timestamp": db.to_iso(row["timestamp"])})


if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
