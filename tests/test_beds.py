import pytest

from app import beds
from app.config import FACILITIES_BY_ID


def snap(fid, ward, ts, occupied, capacity, admissions=0, discharges=0):
    return {"facility_id": fid, "ward": ward, "timestamp": f"2026-11-09T{ts:02d}:00:00+00:00",
            "occupied": occupied, "capacity": capacity, "admissions": admissions, "discharges": discharges}


@pytest.mark.parametrize("occupied,capacity,expected", [
    (10, 20, "low"), (12, 20, "ideal"), (17, 20, "ideal"), (18, 20, "high"), (20, 20, "full"), (0, 0, "low"),
])
def test_status_bands(occupied, capacity, expected):
    assert beds.status(occupied, capacity)["key"] == expected


def test_bor_is_a_percentage():
    assert beds.bor(17, 20) == 85.0
    assert beds.bor(1, 3) == 33.3
    assert beds.bor(0, 0) == 0.0


def test_haversine_known_distance():
    # Monas (Jakarta) to Gedung Sate (Bandung) is about 118 km in a straight line.
    assert beds.haversine_km(-6.1754, 106.8272, -6.9025, 107.6188) == pytest.approx(118, abs=3)
    assert beds.haversine_km(1.0, 100.0, 1.0, 100.0) == 0


def test_facility_view_totals():
    f = FACILITIES_BY_ID["melati"]
    latest = {"general": snap("melati", "general", 1, 12, 12), "maternity": snap("melati", "maternity", 1, 4, 8)}
    view = beds.facility_view(f, latest)
    assert view["total"]["capacity"] == 20 and view["total"]["free"] == 4
    assert view["total"]["full_wards"] == 1
    assert {w["ward"]: w["status"] for w in view["wards"]} == {"general": "full", "maternity": "low"}
    assert beds.facility_view(f, None)["total"] is None


def test_nearest_skips_full_wards_and_sorts_by_distance():
    def view(fid, free):
        f = FACILITIES_BY_ID[fid]
        return beds.facility_view(f, {"icu": snap(fid, "icu", 1, f["beds"]["icu"] - free, f["beds"]["icu"])})

    facilities = [view("arek", 3), view("cempaka", 0), view("pelita", 2), view("parahyangan", 1)]
    hits = beds.nearest(facilities, -6.1754, 106.8272, "icu")  # Monas
    assert [h["facility_id"] for h in hits] == ["pelita", "parahyangan", "arek"]
    assert hits[0]["distance_km"] < hits[1]["distance_km"] < hits[2]["distance_km"]
    assert beds.nearest(facilities, -6.1754, 106.8272, "nicu") == []


def test_rollup_carries_wards_forward():
    rows = [snap("melati", "general", 1, 6, 12, admissions=2), snap("melati", "maternity", 1, 4, 8, admissions=1),
            snap("melati", "general", 2, 12, 12)]
    points = beds.facility_history(rows)
    assert [p["occupied"] for p in points] == [10, 16]
    assert points[0]["admissions"] == 3
    assert points[1]["wards"] == {"general": 100.0, "maternity": 50.0}


def test_regions_report_change_over_24_hours():
    rows = [snap("deli", "general", h, 100 + 2 * h, 210) for h in range(0, 24)]
    rows.append({**snap("deli", "general", 0, 160, 210), "timestamp": "2026-11-10T00:00:00+00:00"})
    (region,) = beds.regions(rows)
    assert region["province"] == "Sumatera Utara"
    assert region["bor"] == beds.bor(160, 210)
    assert region["change_24h"] == pytest.approx(beds.bor(160, 210) - beds.bor(100, 210), abs=0.1)
    assert len(region["trend"]) == 25


def test_alert_episodes_group_consecutive_hours():
    rows = [snap("cempaka", "icu", h, occ, 32) for h, occ in enumerate([20, 28, 30, 32, 29, 20, 29])]
    ward_alerts = [a for a in beds.alerts(rows) if a["ward"] == "icu"]
    assert len(ward_alerts) == 2
    newest, first = ward_alerts
    assert newest["ongoing"] and newest["level"] == "high"
    assert first["level"] == "full" and first["min_free"] == 0 and first["hours"] == 3
    assert not first["ongoing"]
    assert [a["level"] for a in beds.alerts(rows, "full") if a["ward"] == "icu"] == ["full"]


def test_facility_level_alerts():
    rows = [snap("melati", "general", 1, 12, 12), snap("melati", "maternity", 1, 8, 8),
            snap("melati", "emergency", 1, 3, 4)]
    whole = [a for a in beds.alerts(rows) if a["ward"] is None]
    assert len(whole) == 1 and whole[0]["level"] == "high" and whole[0]["peak_bor"] == 95.8
