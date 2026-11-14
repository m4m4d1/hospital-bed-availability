# Changelog

## 1.0.0

First release.

- Live demo on GitHub Pages, built from a static snapshot of the API (`python -m app.export_demo`).
- Dockerfile, tests for the snapshot ingest endpoint and API key, and full documentation.
- Facility map (colour by status), nearest free bed finder and a 24-hour alerts panel linked to the facility detail.
- Bilingual (EN/ID) dashboard: summary, facility table, ward detail with 72-hour chart, occupancy by province.
- REST API: facilities, history, summary, regional trends, nearest free bed, alerts and a snapshot ingest endpoint (`/docs` for details).
- Bed occupancy rate (BOR) with status bands, alert episodes for wards above 85% or full, haversine distances.
- Bed occupancy simulator (admission and discharge cycles, weekend effect, regional dengue surges) and SQLite storage
  (`python -m app.simulator --hours 72`).
- Project scaffold, 16 fictional facilities in 9 provinces, 6 ward types and the bed snapshot data model (BOR bands, Depkes 2005).
