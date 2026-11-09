"""Realistic simulated bed snapshots for every ward.

Each ward has a usual share of beds in use, higher at big referral hospitals
(class A) than at puskesmas. Patients arrive and leave as random (Poisson)
flows: admissions peak in the late morning (evening for the ER), discharges
around midday after the doctors' rounds, and fewer planned admissions happen
at the weekend. Occupancy drifts back towards its usual level, so the numbers
wander like a real ward without running away.

On top of that a province sometimes gets a surge, such as a dengue outbreak,
that fills general, isolation, ICU and ER beds for several days. Surges are
derived from a hash of (province, day), so the same moment always gives the
same answer whichever order snapshots are generated in.

    python -m app.simulator --hours 72      # fill the database with 3 days of snapshots
"""
import argparse
import math
import random
from datetime import datetime, timedelta, timezone

from . import db
from .config import FACILITIES

# Usual share of beds in use, by ward, at a class B hospital.
BASE_LOAD = {"icu": 0.80, "isolation": 0.62, "general": 0.72, "maternity": 0.66, "nicu": 0.74, "emergency": 0.60}
TYPE_FACTOR = {"A": 1.08, "B": 1.0, "C": 0.94, "puskesmas": 0.78}
# Share of a ward's beds that turn over per hour (roughly 1 / average length of stay).
TURNOVER = {"icu": 0.007, "isolation": 0.006, "general": 0.009, "maternity": 0.02, "nicu": 0.005, "emergency": 0.13}
# How much a surge at full strength raises the usual load.
SURGE_GAIN = {"icu": 0.16, "isolation": 0.42, "general": 0.24, "maternity": 0.0, "nicu": 0.0, "emergency": 0.35}
SURGE_CHANCE = 0.05  # per province per day
SURGE_DAYS = (3, 7)
PULL = 0.12  # share of the gap to the usual level closed per hour


def poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam > 30:
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def surge_strength(province: str, ts: datetime) -> float:
    """0 when no surge is active in the province, up to ~1 at the peak of one."""
    strength = 0.0
    day = ts.date()
    for back in range(SURGE_DAYS[1]):
        rng = random.Random(f"{province}:{day - timedelta(days=back)}")
        if rng.random() < SURGE_CHANCE:
            length = rng.randint(*SURGE_DAYS)
            elapsed = back + (ts.hour + ts.minute / 60) / 24
            if elapsed < length:
                strength = max(strength, math.sin(math.pi * elapsed / length) * rng.uniform(0.6, 1.0))
    return strength


def usual_load(facility: dict, ward: str, ts: datetime) -> float:
    """Share of beds normally in use in this ward at this moment (can pass 1 in a surge)."""
    offset = random.Random(f"{facility['id']}:{ward}").uniform(-0.06, 0.06)
    load = BASE_LOAD[ward] * TYPE_FACTOR[facility["type"]] + offset
    return max(0.05, load + SURGE_GAIN[ward] * surge_strength(facility["province"], ts))


def _cycles(ward: str, ts: datetime) -> tuple[float, float]:
    """(admission, discharge) rate multipliers for the local time of day and weekday; mean ~1."""
    local = ts + timedelta(hours=7)  # WIB
    h = local.hour + local.minute / 60
    if ward == "emergency":
        admit = 1 + 0.5 * math.cos(2 * math.pi * (h - 19) / 24)
        discharge = 1 + 0.4 * math.cos(2 * math.pi * (h - 21) / 24)
    else:
        admit = 1 + 0.6 * math.cos(2 * math.pi * (h - 10.5) / 24)
        discharge = max(0.15, 1 + 0.85 * math.cos(2 * math.pi * (h - 12.5) / 24))
        if local.weekday() >= 5 and ward in ("general", "maternity"):
            admit *= 0.85  # fewer planned admissions at the weekend
        if local.weekday() == 6:
            discharge *= 0.7
    return admit, discharge


def step(facility: dict, ward: str, ts: datetime, occupied: int, rng: random.Random,
         minutes: float = 60) -> dict:
    """The next snapshot of a ward, `minutes` after the one with `occupied` beds in use."""
    capacity = facility["beds"][ward]
    occupied = min(max(0, occupied), capacity)
    hours = minutes / 60
    target = usual_load(facility, ward, ts) * capacity
    admit, discharge = _cycles(ward, ts)
    flow = capacity * TURNOVER[ward] * hours
    lam_in = flow * admit + PULL * hours * max(0.0, target - occupied)
    lam_out = flow * discharge * occupied / max(target, 1.0) + PULL * hours * max(0.0, occupied - target)
    admissions = poisson(rng, lam_in)
    discharges = min(occupied, poisson(rng, lam_out))
    new = occupied + admissions - discharges
    if new > capacity:  # no bed left: the extra patients are referred elsewhere
        admissions -= new - capacity
        new = capacity
    return {"facility_id": facility["id"], "ward": ward, "timestamp": ts, "capacity": capacity,
            "occupied": new, "admissions": admissions, "discharges": discharges}


def next_snapshots(latest: dict[str, dict[str, dict]], ts: datetime, rng: random.Random,
                   minutes: float = 60) -> list[dict]:
    """One new snapshot per ward, continuing from the latest stored ones."""
    rows = []
    for f in FACILITIES:
        for ward in f["beds"]:
            prev = latest.get(f["id"], {}).get(ward)
            occupied = prev["occupied"] if prev else round(usual_load(f, ward, ts) * f["beds"][ward])
            rows.append(step(f, ward, ts, occupied, rng, minutes))
    return rows


def generate(start: datetime, end: datetime, step_minutes: int = 60, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []
    latest: dict[str, dict[str, dict]] = {}
    ts = start.replace(second=0, microsecond=0)
    while ts <= end:
        batch = next_snapshots(latest, ts, rng, step_minutes)
        for r in batch:
            latest.setdefault(r["facility_id"], {})[r["ward"]] = r
        rows.extend(batch)
        ts += timedelta(minutes=step_minutes)
    return rows


def backfill(hours: int = 72, step_minutes: int = 60, seed: int | None = 42) -> int:
    """Store `hours` of history ending now."""
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    db.init_db()
    return db.insert_snapshots(generate(end - timedelta(hours=hours), end, step_minutes, seed))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill the database with simulated bed snapshots.")
    parser.add_argument("--hours", type=int, default=72)
    parser.add_argument("--step", type=int, default=60, help="minutes between snapshots")
    args = parser.parse_args()
    n = backfill(args.hours, args.step)
    print(f"stored {n} snapshots in {db.db_path()}")


if __name__ == "__main__":
    main()
