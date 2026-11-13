from fastapi.testclient import TestClient

from app.main import app

ICU = {"facility_id": "cempaka", "ward": "icu", "capacity": 32, "occupied": 20, "admissions": 2, "discharges": 1}


def test_ingest_scores_and_stores_a_snapshot():
    with TestClient(app) as c:
        res = c.post("/api/snapshots", json=ICU)
        assert res.status_code == 201
        body = res.json()
        assert body["free"] == 12 and body["bor"] == 62.5 and body["status"] == "ideal"
        icu = next(w for w in c.get("/api/facilities/cempaka").json()["wards"] if w["ward"] == "icu")
        assert icu["occupied"] == 20


def test_a_full_ward_raises_an_alert_and_drops_out_of_nearest():
    with TestClient(app) as c:
        assert c.post("/api/snapshots", json={**ICU, "occupied": 32}).json()["status"] == "full"
        c.post("/api/snapshots", json={**ICU, "facility_id": "pelita", "capacity": 16, "occupied": 10})
        alerts = c.get("/api/alerts?hours=1&level=full").json()
        # The ward is full, and so is the facility, since ICU is the only ward it has reported.
        assert {(a["facility_id"], a["ward"]) for a in alerts} == {("cempaka", "icu"), ("cempaka", None)}
        assert all(a["ongoing"] for a in alerts)
        near = c.get("/api/nearest?lat=-6.1754&lon=106.8272&ward=icu").json()["results"]
        assert [r["facility_id"] for r in near] == ["pelita"]


def test_ingest_validates_input():
    with TestClient(app) as c:
        assert c.post("/api/snapshots", json={**ICU, "facility_id": "nowhere"}).status_code == 422
        assert c.post("/api/snapshots", json={**ICU, "ward": "dentist"}).status_code == 422
        assert c.post("/api/snapshots", json={**ICU, "facility_id": "melati"}).status_code == 422  # no ICU
        assert c.post("/api/snapshots", json={**ICU, "occupied": 33}).status_code == 422
        assert c.post("/api/snapshots", json={**ICU, "occupied": -1}).status_code == 422
        assert c.post("/api/snapshots", json={"facility_id": "cempaka"}).status_code == 422


def test_api_key_is_enforced_when_set(monkeypatch):
    monkeypatch.setenv("HB_API_KEY", "secret")
    with TestClient(app) as c:
        assert c.post("/api/snapshots", json=ICU).status_code == 401
        assert c.post("/api/snapshots", json=ICU, headers={"X-API-Key": "secret"}).status_code == 201
