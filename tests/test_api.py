from fastapi.testclient import TestClient

from app import simulator
from app.config import FACILITIES, PROVINCES, WARD_SLOTS
from app.main import app


def client() -> TestClient:
    simulator.backfill(hours=24)
    return TestClient(app)


def test_health():
    with client() as c:
        body = c.get("/api/health").json()
        assert body["status"] == "ok"
        assert body["snapshots"] == 25 * len(WARD_SLOTS)


def test_facilities_have_wards_and_totals():
    with client() as c:
        facilities = c.get("/api/facilities").json()
        assert len(facilities) == len(FACILITIES)
        for f in facilities:
            assert {w["ward"] for w in f["wards"]} == set(f["beds"])
            assert f["total"]["status"] in {"low", "ideal", "high", "full"}
            assert f["total"]["free"] == f["total"]["capacity"] - f["total"]["occupied"]


def test_facility_history_and_unknown_facility():
    with client() as c:
        rows = c.get("/api/facilities/cempaka/history?hours=12").json()
        assert 12 <= len(rows) <= 13
        assert set(rows[-1]["wards"]) == set(FACILITIES[0]["beds"])
        assert c.get("/api/facilities/nowhere").status_code == 404
        assert c.get("/api/facilities/nowhere/history").status_code == 404


def test_summary_adds_up():
    with client() as c:
        body = c.get("/api/summary").json()
        assert body["reporting"] == len(FACILITIES)
        assert sum(body["status_counts"].values()) == len(FACILITIES)
        assert body["free"] == sum(body["free_by_ward"].values())
        assert body["busiest"]["bor"] >= body["bor"]


def test_regions_cover_every_province():
    with client() as c:
        regions = c.get("/api/regions?hours=24").json()
        assert [r["province"] for r in regions] == PROVINCES
        assert all(24 <= len(r["trend"]) <= 25 for r in regions)


def test_nearest_free_bed():
    with client() as c:
        body = c.get("/api/nearest?lat=-6.1754&lon=106.8272&ward=general").json()
        assert body["query"]["ward"] == "general"
        distances = [r["distance_km"] for r in body["results"]]
        assert distances == sorted(distances) and len(distances) <= 5
        assert all(r["free"] > 0 for r in body["results"])
        assert c.get("/api/nearest?lat=-6.2&lon=106.8&ward=dentist").status_code == 422
        assert c.get("/api/nearest?lat=-96&lon=106.8&ward=icu").status_code == 422


def test_alerts_endpoint():
    with client() as c:
        alerts = c.get("/api/alerts?hours=24").json()
        assert all(a["level"] in {"high", "full"} for a in alerts)
        assert all(a["peak_bor"] > 85 for a in alerts)
        full = c.get("/api/alerts?hours=24&level=full").json()
        assert all(a["level"] == "full" and a["min_free"] == 0 for a in full)
        assert c.get("/api/alerts?level=bogus").status_code == 422
