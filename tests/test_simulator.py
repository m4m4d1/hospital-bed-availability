import random
from datetime import datetime, timedelta, timezone
from statistics import mean

from app import db, simulator
from app.config import FACILITIES_BY_ID, PROVINCES, WARD_SLOTS

END = datetime(2026, 11, 9, tzinfo=timezone.utc)


def test_generate_covers_every_ward_and_hour():
    rows = simulator.generate(END - timedelta(hours=23), END, seed=1)
    assert len(rows) == 24 * len(WARD_SLOTS)
    assert {(r["facility_id"], r["ward"]) for r in rows} == set(WARD_SLOTS)


def test_counts_stay_within_capacity():
    for r in simulator.generate(END - timedelta(days=7), END, seed=2):
        assert 0 <= r["occupied"] <= r["capacity"]
        assert r["admissions"] >= 0 and r["discharges"] >= 0


def test_occupancy_follows_admissions_and_discharges():
    rows = simulator.generate(END - timedelta(days=2), END, seed=3)
    icu = [r for r in rows if r["facility_id"] == "cempaka" and r["ward"] == "icu"]
    for prev, cur in zip(icu, icu[1:]):
        assert cur["occupied"] == prev["occupied"] + cur["admissions"] - cur["discharges"]


def test_referral_hospital_icu_is_busier_than_puskesmas():
    rows = simulator.generate(END - timedelta(days=3), END, seed=4)

    def share(fid, ward):
        return mean(r["occupied"] / r["capacity"] for r in rows if r["facility_id"] == fid and r["ward"] == ward)

    assert share("cempaka", "icu") > share("melati", "general") + 0.15


def test_surges_are_deterministic_and_raise_the_usual_load():
    hours = [END - timedelta(hours=h) for h in range(0, 24 * 120, 6)]
    found = [(p, ts) for p in PROVINCES for ts in hours if simulator.surge_strength(p, ts) > 0.4]
    assert found, "expected at least one surge in 120 days"
    province, ts = found[0]
    assert simulator.surge_strength(province, ts) == simulator.surge_strength(province, ts)
    facility = next(f for f in FACILITIES_BY_ID.values() if f["province"] == province)
    quiet = END + timedelta(days=3650)
    while simulator.surge_strength(province, quiet) > 0:
        quiet += timedelta(days=1)
    assert simulator.usual_load(facility, "general", ts) > simulator.usual_load(facility, "general", quiet)


def test_poisson_mean_is_close_to_lambda():
    rng = random.Random(5)
    assert abs(mean(simulator.poisson(rng, 3.0) for _ in range(4000)) - 3.0) < 0.15
    assert simulator.poisson(rng, 0) == 0


def test_backfill_stores_snapshots():
    n = simulator.backfill(hours=6)
    assert n == 7 * len(WARD_SLOTS)
    assert db.count() == n
    latest = db.latest()
    assert {(fid, w) for fid, wards in latest.items() for w in wards} == set(WARD_SLOTS)
