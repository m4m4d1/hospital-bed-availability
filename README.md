# Hospital Bed & Puskesmas Availability System

**Sistem Ketersediaan Tempat Tidur RS & Puskesmas** for Indonesia.

Shows available beds by ward at hospitals and puskesmas, the bed occupancy rate (BOR) and its trend
by province, and the nearest facility that still has a free bed of the type a patient needs.

> Week 3 of Nusantara Intel: one new open-source
> information system for Indonesia every week, built in public one step per day.

## Facilities

16 facilities in 9 provinces (DKI Jakarta, Jawa Barat, Jawa Tengah, DI Yogyakarta, Jawa Timur,
Sumatera Utara, Sulawesi Selatan, Bali and Kalimantan Timur): class A, B and C hospitals and
inpatient puskesmas.

**The facility names are fictional.** Cities and coordinates are real, but no facility here is a
real hospital or puskesmas, and every bed count is simulated.

## Wards

| Ward | Bahasa Indonesia | Where |
|------|------------------|-------|
| ICU | ICU | hospitals |
| Isolation | Isolasi | most hospitals |
| General ward | Rawat inap umum | all facilities |
| Maternity | Kebidanan | all facilities |
| NICU | NICU | class A and B hospitals |
| Emergency (ER) | IGD | all facilities |

## Bed occupancy rate

BOR = occupied beds / available beds × 100%. Bands follow the Ministry of Health efficiency
indicators (Depkes RI, 2005), where 60-85% is ideal:

| BOR | Status |
|-----|--------|
| below 60% | Below ideal (*di bawah ideal*) |
| 60 to 85% | Ideal |
| above 85% | High (*tinggi*), alert |
| no free bed | Full (*penuh*), alert |

## Roadmap this week

- [x] Mon: scaffold, facilities and data model
- [x] Tue: bed occupancy simulator and storage
- [x] Wed: REST API, occupancy rate, nearest free bed and alerts
- [x] Thu: dashboard
- [x] Fri: map, nearest free bed finder and alerts panel
- [ ] Sat: Docker, tests and documentation
- [ ] Sun: live demo and v1.0 release

## License

MIT
