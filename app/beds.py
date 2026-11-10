"""Bed occupancy rate, status, regional trends, nearest free bed and alerts.

BOR (bed occupancy rate) = occupied beds / available beds × 100%. The Ministry
of Health hospital efficiency indicators (Depkes RI, 2005) call 60-85% ideal:
below 60% beds stand empty, above 85% a ward has little room for the next
emergency. We add "full" for a ward with no free bed at all. An alert is raised
while a ward (or a whole facility) is above 85% or full. Verify the bands
against current Kemenkes guidance before official use.

Distances are great-circle distances (haversine), not road distances.
"""
import math
from collections import defaultdict
from datetime import datetime, timedelta

from .config import ALERT_BOR, FACILITIES_BY_ID, STATUS_BANDS

BANDS = {b["key"]: b for b in STATUS_BANDS}
LEVELS = {
    "high": {"en": f"Above {ALERT_BOR:.0f}% occupied", "id": f"Terisi di atas {ALERT_BOR:.0f}%"},
    "full": {"en": "No free bed", "id": "Tidak ada tempat tidur kosong"},
}
EARTH_RADIUS_KM = 6371.0088


def bor(occupied: int, capacity: int) -> float:
    """Bed occupancy rate in percent (0 when the ward has no beds)."""
    return round(100.0 * occupied / capacity, 1) if capacity > 0 else 0.0


def status(occupied: int, capacity: int) -> dict:
    rate = bor(occupied, capacity)
    if capacity > 0 and occupied >= capacity:
        key = "full"
    elif rate > ALERT_BOR:
        key = "high"
    elif rate >= 60:
        key = "ideal"
    else:
        key = "low"
    return BANDS[key]


def alert_level(occupied: int, capacity: int) -> str | None:
    key = status(occupied, capacity)["key"]
    return key if key in LEVELS else None


def _rated(occupied: int, capacity: int) -> dict:
    band = status(occupied, capacity)
    return {"capacity": capacity, "occupied": occupied, "free": max(0, capacity - occupied),
            "bor": bor(occupied, capacity), "status": band["key"],
            "status_label": {"en": band["en"], "id": band["id"]}}


def ward_view(row: dict) -> dict:
    """A stored snapshot with free beds, BOR and status attached."""
    return {"facility_id": row["facility_id"], "ward": row["ward"], "timestamp": row["timestamp"],
            **_rated(row["occupied"], row["capacity"]),
            "admissions": row.get("admissions", 0), "discharges": row.get("discharges", 0)}


def facility_view(facility: dict, latest: dict[str, dict] | None) -> dict:
    """A facility with its latest ward snapshots and totals."""
    latest = latest or {}
    wards = [ward_view(latest[w]) for w in facility["beds"] if w in latest]
    total = None
    if wards:
        total = {**_rated(sum(w["occupied"] for w in wards), sum(w["capacity"] for w in wards)),
                 "full_wards": sum(w["status"] == "full" for w in wards),
                 "timestamp": max(w["timestamp"] for w in wards)}
    return {**facility, "wards": wards, "total": total}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def nearest(facilities: list[dict], lat: float, lon: float, ward: str, limit: int = 5) -> list[dict]:
    """Facilities (as from facility_view) with at least one free bed in `ward`, closest first."""
    hits = []
    for f in facilities:
        w = next((w for w in f["wards"] if w["ward"] == ward), None)
        if not w or w["free"] <= 0:
            continue
        hits.append({"facility_id": f["id"], "name": f["name"], "type": f["type"], "city": f["city"],
                     "province": f["province"], "lat": f["lat"], "lon": f["lon"], "ward": ward,
                     "free": w["free"], "capacity": w["capacity"], "bor": w["bor"],
                     "distance_km": round(haversine_km(lat, lon, f["lat"], f["lon"]), 1)})
    return sorted(hits, key=lambda h: h["distance_km"])[:limit]


def rollup(rows: list[dict], group) -> dict[str, list[dict]]:
    """Total beds over time per group (facility, province...).

    `group(row)` names the group of a snapshot. Each ward's last snapshot is
    carried forward, so a group's total is right even when its wards report at
    different moments. One point per distinct timestamp in the group.
    """
    state: dict = defaultdict(dict)
    out: dict[str, list[dict]] = defaultdict(list)
    for r in sorted(rows, key=lambda r: r["timestamp"]):
        g = group(r)
        wards = state[g]
        wards[(r["facility_id"], r["ward"])] = r
        by_ward: dict = defaultdict(lambda: [0, 0])
        for (_, w), s in wards.items():
            by_ward[w][0] += s["occupied"]
            by_ward[w][1] += s["capacity"]
        occupied = sum(v[0] for v in by_ward.values())
        capacity = sum(v[1] for v in by_ward.values())
        point = {"timestamp": r["timestamp"], **_rated(occupied, capacity),
                 "wards": {w: bor(*v) for w, v in by_ward.items()},
                 "admissions": r.get("admissions", 0), "discharges": r.get("discharges", 0)}
        del point["status_label"]
        points = out[g]
        if points and points[-1]["timestamp"] == r["timestamp"]:
            point["admissions"] += points[-1]["admissions"]
            point["discharges"] += points[-1]["discharges"]
            points[-1] = point
        else:
            points.append(point)
    return dict(out)


def facility_history(rows: list[dict]) -> list[dict]:
    """Rows of one facility as a time series of totals and per-ward BOR."""
    return rollup(rows, lambda r: r["facility_id"]).get(rows[0]["facility_id"], []) if rows else []


def _hourly(points: list[dict]) -> list[dict]:
    """Keep the last point of every hour."""
    last: dict[str, dict] = {}
    for p in points:
        last[p["timestamp"][:13]] = p
    return list(last.values())


def regions(rows: list[dict]) -> list[dict]:
    """Occupancy per province: now, change over 24 hours and an hourly trend."""
    series = rollup(rows, lambda r: FACILITIES_BY_ID[r["facility_id"]]["province"]
                    if r["facility_id"] in FACILITIES_BY_ID else "?")
    out = []
    for province, points in sorted(series.items()):
        now = points[-1]
        cutoff = datetime.fromisoformat(now["timestamp"]) - timedelta(hours=24)
        before = next((p for p in points if datetime.fromisoformat(p["timestamp"]) >= cutoff), points[0])
        band = BANDS[now["status"]]
        out.append({
            "province": province,
            "facilities": sum(f["province"] == province for f in FACILITIES_BY_ID.values()),
            "capacity": now["capacity"], "occupied": now["occupied"], "free": now["free"], "bor": now["bor"],
            "status": now["status"], "status_label": {"en": band["en"], "id": band["id"]},
            "wards": now["wards"],
            "change_24h": round(now["bor"] - before["bor"], 1),
            "trend": [{"timestamp": p["timestamp"], "bor": p["bor"]} for p in _hourly(points)],
        })
    return out


def _episodes(points: list[dict], facility_id: str, ward: str | None) -> list[dict]:
    """Stretches of consecutive points above the alert threshold or full."""
    out, cur = [], None
    for p in points:
        level = alert_level(p["occupied"], p["capacity"])
        rate, free = bor(p["occupied"], p["capacity"]), max(0, p["capacity"] - p["occupied"])
        if level and cur:
            cur["end"] = p["timestamp"]
            cur["peak_bor"] = max(cur["peak_bor"], rate)
            cur["min_free"] = min(cur["min_free"], free)
            if level == "full":
                cur["level"] = "full"
        elif level:
            cur = {"facility_id": facility_id, "ward": ward, "level": level, "start": p["timestamp"],
                   "end": p["timestamp"], "peak_bor": rate, "min_free": free, "capacity": p["capacity"]}
        elif cur:
            out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    last = points[-1]["timestamp"] if points else None
    for a in out:
        a["ongoing"] = a["end"] == last
        a["hours"] = round((datetime.fromisoformat(a["end"]) - datetime.fromisoformat(a["start"]))
                           .total_seconds() / 3600, 1)
        a["level_label"] = LEVELS[a["level"]]
    return out


def alerts(rows: list[dict], level: str = "high") -> list[dict]:
    """Alert episodes for wards and whole facilities, newest first.

    level="high" returns everything above the threshold (including full);
    level="full" only episodes in which a ward or facility ran out of beds.
    """
    by_ward: dict = defaultdict(list)
    for r in sorted(rows, key=lambda r: r["timestamp"]):
        by_ward[(r["facility_id"], r["ward"])].append(r)
    out = []
    for (fid, ward), series in by_ward.items():
        out += _episodes(series, fid, ward)
    for fid, points in rollup(rows, lambda r: r["facility_id"]).items():
        out += _episodes(points, fid, None)
    if level == "full":
        out = [a for a in out if a["level"] == "full"]
    return sorted(out, key=lambda a: (a["end"], a["start"], a["facility_id"], a["ward"] or ""), reverse=True)
