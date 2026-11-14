# Hospital Bed & Puskesmas Availability System

**Sistem Ketersediaan Tempat Tidur RS & Puskesmas** for Indonesia.

Shows available beds by ward at hospitals and puskesmas, the bed occupancy rate (BOR) and its trend
by province, and the nearest facility that still has a free bed of the type a patient needs.

> Week 3 of Nusantara Intel: one new open-source
> information system for Indonesia every week, built in public one step per day.

**Live demo:** https://m4m4d1.github.io/hospital-bed-availability/ (simulated data)

## Features

- **16 facilities in 9 provinces**: class A, B and C hospitals and inpatient puskesmas in DKI
  Jakarta, Jawa Barat, Jawa Tengah, DI Yogyakarta, Jawa Timur, Sumatera Utara, Sulawesi Selatan,
  Bali and Kalimantan Timur. **Facility names are fictional** (see Notes).
- **Six ward types**: ICU, isolation, general ward, maternity, NICU and emergency (IGD).
- **Bed occupancy rate** per ward, facility and province, with the Depkes efficiency bands.
- **Trend by province** over the last 72 hours and the change over 24 hours.
- **Nearest free bed**: the closest facilities with a free bed in the ward a patient needs.
- **Alerts** while a ward or a whole facility is above 85% occupied or has no free bed.
- **Bilingual dashboard** (English / Bahasa Indonesia): summary, facility table, ward detail,
  72-hour charts, map, nearest free bed finder and alerts.
- **REST API** with interactive docs at `/docs`, including an endpoint for hospital systems.
- **Simulator** that produces realistic bed counts (admission and discharge cycles, weekends,
  regional dengue surges) so the system runs out of the box.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000 for the dashboard and http://localhost:8000/docs for the API.
On first start the database is filled with 72 hours of simulated snapshots, and a new snapshot per
ward is added every minute.

With Docker:

```bash
docker build -t hospital-bed-availability .
docker run -p 8000:8000 -v hb-data:/data hospital-bed-availability
```

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `HB_DB` | `data/beds.db` | SQLite database file |
| `HB_SIMULATE` | `1` | `0` turns the simulator off (use with real hospital systems) |
| `HB_SIM_INTERVAL` | `60` | Seconds between simulated snapshots |
| `HB_API_KEY` | not set | If set, `POST /api/snapshots` needs the header `X-API-Key` |

## API

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/facilities` | All facilities with their wards, free beds, BOR and status |
| GET | `/api/facilities/{id}` | One facility |
| GET | `/api/facilities/{id}/history?hours=72` | Total and per-ward BOR over time |
| GET | `/api/summary` | Totals, free beds per ward type, full wards, busiest facility |
| GET | `/api/regions?hours=72` | BOR per province, change over 24 hours and hourly trend |
| GET | `/api/nearest?lat=-6.1754&lon=106.8272&ward=icu` | Closest facilities with a free bed in that ward |
| GET | `/api/alerts?hours=24&level=high` | Alert episodes (`level=full` for full wards only) |
| GET | `/api/meta` | Wards, facility types, status bands and finder presets |
| POST | `/api/snapshots` | Store a ward's bed count; returns its BOR and status |

Send a bed count from a hospital information system:

```bash
curl -X POST http://localhost:8000/api/snapshots \
  -H "Content-Type: application/json" \
  -d '{"facility_id": "cempaka", "ward": "icu", "capacity": 32, "occupied": 30, "admissions": 2, "discharges": 1}'
```

## How occupancy is scored

BOR = occupied beds / available beds × 100%, per ward, per facility (all wards together) and per
province. The bands follow the Ministry of Health hospital efficiency indicators
(Depkes RI, 2005), where 60-85% is ideal (the Barber-Johnson method uses a narrower 75-85%):

| BOR | Status |
|-----|--------|
| below 60% | Below ideal (*di bawah ideal*): beds stand empty |
| 60 to 85% | Ideal |
| above 85% | High (*tinggi*): little room for the next emergency, alert |
| no free bed | Full (*penuh*), alert |

An alert is one episode: consecutive snapshots in which a ward (or the facility as a whole) stays
above 85% or full, with its start, end, peak BOR and the fewest free beds. "Ongoing" means the
latest snapshot is still above the threshold.

The nearest free bed finder ranks facilities with at least one free bed of the chosen ward by
straight-line (haversine) distance. Road distance and travel time can be much longer, especially
across water or mountains.

## Tests

```bash
pytest -q
```

## Notes

**The facilities are fictional.** Cities and coordinates are real, but the hospital and puskesmas
names are invented and every bed count is simulated, so that nothing here can be mistaken for the
real situation at a real hospital. For real bed availability in Indonesia, use the Ministry of
Health's official services (such as SIRANAP) or call the facility. Verify the BOR bands against
current Kemenkes guidance before official use.

## Built this week

- [x] Mon: scaffold, facilities and data model
- [x] Tue: bed occupancy simulator and storage
- [x] Wed: REST API, occupancy rate, nearest free bed and alerts
- [x] Thu: dashboard
- [x] Fri: map, nearest free bed finder and alerts panel
- [x] Sat: Docker, tests and documentation
- [x] Sun: live demo and v1.0 release

## License

MIT
