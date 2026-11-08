"""Facilities, wards and bed occupancy thresholds.

IMPORTANT: every facility below is FICTIONAL. The cities, districts and coordinates
are real, but the hospital and puskesmas names are invented and all bed counts are
simulated, so that the demo cannot be mistaken for the real situation at a real
hospital. Connect the system to real hospital information systems (or the national
SIRANAP bed reporting) before using it for anything that matters.

Bed occupancy rate (BOR) bands follow the hospital efficiency indicators of the
Indonesian Ministry of Health (Depkes RI, 2005): a BOR of 60-85% is ideal. The
Barber-Johnson method uses a narrower 75-85%. Verify these values against current
Kemenkes guidance before official use.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("HB_DB", ROOT / "data" / "beds.db"))

# Wards (ruang) whose beds are tracked.
WARDS = {
    "icu": {"en": "ICU", "id": "ICU"},
    "isolation": {"en": "Isolation", "id": "Isolasi"},
    "general": {"en": "General ward", "id": "Rawat inap umum"},
    "maternity": {"en": "Maternity", "id": "Kebidanan"},
    "nicu": {"en": "NICU", "id": "NICU"},
    "emergency": {"en": "Emergency (ER)", "id": "IGD"},
}

# Facility types. Hospital classes A-D follow Permenkes No. 3/2020.
TYPES = {
    "A": {"en": "Hospital, class A", "id": "RS kelas A"},
    "B": {"en": "Hospital, class B", "id": "RS kelas B"},
    "C": {"en": "Hospital, class C", "id": "RS kelas C"},
    "puskesmas": {"en": "Puskesmas (inpatient)", "id": "Puskesmas rawat inap"},
}

# Fictional facilities at real locations. `beds` is the number of beds per ward.
FACILITIES = [
    {"id": "cempaka", "name": "RSU Cempaka Lintang", "type": "A", "city": "Jakarta Pusat",
     "province": "DKI Jakarta", "lat": -6.179, "lon": 106.842,
     "beds": {"icu": 32, "isolation": 24, "general": 260, "maternity": 40, "nicu": 18, "emergency": 30}},
    {"id": "pelita", "name": "RS Pelita Samudra", "type": "B", "city": "Koja, Jakarta Utara",
     "province": "DKI Jakarta", "lat": -6.117, "lon": 106.906,
     "beds": {"icu": 16, "isolation": 12, "general": 140, "maternity": 24, "nicu": 8, "emergency": 20}},
    {"id": "melati", "name": "Puskesmas Melati Asri", "type": "puskesmas", "city": "Pasar Minggu, Jakarta Selatan",
     "province": "DKI Jakarta", "lat": -6.284, "lon": 106.844,
     "beds": {"general": 12, "maternity": 8, "emergency": 4}},
    {"id": "parahyangan", "name": "RSU Parahyangan Lestari", "type": "A", "city": "Bandung",
     "province": "Jawa Barat", "lat": -6.894, "lon": 107.599,
     "beds": {"icu": 28, "isolation": 20, "general": 220, "maternity": 36, "nicu": 14, "emergency": 26}},
    {"id": "patriot", "name": "RS Patriot Sehat Sentosa", "type": "C", "city": "Bekasi",
     "province": "Jawa Barat", "lat": -6.238, "lon": 106.992,
     "beds": {"icu": 8, "isolation": 6, "general": 90, "maternity": 20, "emergency": 14}},
    {"id": "kenanga", "name": "Puskesmas Kenanga Wangi", "type": "puskesmas", "city": "Cibiru, Bandung",
     "province": "Jawa Barat", "lat": -6.917, "lon": 107.717,
     "beds": {"general": 10, "maternity": 6, "emergency": 4}},
    {"id": "candi", "name": "RSU Candi Arum", "type": "B", "city": "Semarang",
     "province": "Jawa Tengah", "lat": -6.993, "lon": 110.421,
     "beds": {"icu": 18, "isolation": 12, "general": 150, "maternity": 26, "nicu": 10, "emergency": 20}},
    {"id": "merapi", "name": "RS Merapi Tirta Husada", "type": "B", "city": "Sleman",
     "province": "DI Yogyakarta", "lat": -7.760, "lon": 110.378,
     "beds": {"icu": 14, "isolation": 10, "general": 120, "maternity": 22, "nicu": 8, "emergency": 18}},
    {"id": "arek", "name": "RSU Arek Suroboyo Medika", "type": "A", "city": "Surabaya",
     "province": "Jawa Timur", "lat": -7.268, "lon": 112.758,
     "beds": {"icu": 30, "isolation": 22, "general": 240, "maternity": 38, "nicu": 16, "emergency": 28}},
    {"id": "bromo", "name": "RS Bromo Kasih Utama", "type": "C", "city": "Malang",
     "province": "Jawa Timur", "lat": -7.966, "lon": 112.633,
     "beds": {"icu": 8, "general": 80, "maternity": 18, "emergency": 12}},
    {"id": "anggrek", "name": "Puskesmas Anggrek Larasati", "type": "puskesmas", "city": "Candi, Sidoarjo",
     "province": "Jawa Timur", "lat": -7.490, "lon": 112.709,
     "beds": {"general": 10, "maternity": 6, "emergency": 4}},
    {"id": "deli", "name": "RSU Deli Cahaya Bangsa", "type": "A", "city": "Medan",
     "province": "Sumatera Utara", "lat": 3.585, "lon": 98.672,
     "beds": {"icu": 26, "isolation": 18, "general": 210, "maternity": 34, "nicu": 12, "emergency": 24}},
    {"id": "seroja", "name": "Puskesmas Seroja Rambung", "type": "puskesmas", "city": "Binjai",
     "province": "Sumatera Utara", "lat": 3.600, "lon": 98.485,
     "beds": {"general": 10, "maternity": 6, "emergency": 3}},
    {"id": "losari", "name": "RSU Losari Bakti Medika", "type": "B", "city": "Makassar",
     "province": "Sulawesi Selatan", "lat": -5.147, "lon": 119.432,
     "beds": {"icu": 16, "isolation": 12, "general": 150, "maternity": 26, "nicu": 10, "emergency": 20}},
    {"id": "dwipa", "name": "RS Dwipa Shanti Sejahtera", "type": "B", "city": "Denpasar",
     "province": "Bali", "lat": -8.656, "lon": 115.219,
     "beds": {"icu": 14, "isolation": 10, "general": 120, "maternity": 22, "nicu": 8, "emergency": 18}},
    {"id": "borneo", "name": "RS Borneo Teluk Harapan", "type": "C", "city": "Balikpapan",
     "province": "Kalimantan Timur", "lat": -1.265, "lon": 116.830,
     "beds": {"icu": 8, "isolation": 6, "general": 90, "maternity": 18, "emergency": 14}},
]
FACILITIES_BY_ID = {f["id"]: f for f in FACILITIES}
FACILITY_IDS = set(FACILITIES_BY_ID)
PROVINCES = sorted({f["province"] for f in FACILITIES})
# Every (facility, ward) pair that has beds: one snapshot per pair per time step.
WARD_SLOTS = [(f["id"], w) for f in FACILITIES for w in f["beds"]]

# Bed occupancy rate (BOR) bands, Depkes RI (2005): 60-85% is ideal.
ALERT_BOR = 85.0
STATUS_BANDS = [
    {"key": "low", "en": "Below ideal (<60%)", "id": "Di bawah ideal (<60%)", "color": "#2f7de1"},
    {"key": "ideal", "en": "Ideal (60-85%)", "id": "Ideal (60-85%)", "color": "#1f9d6b"},
    {"key": "high", "en": "High (>85%)", "id": "Tinggi (>85%)", "color": "#e46b1f"},
    {"key": "full", "en": "Full", "id": "Penuh", "color": "#c8102e"},
]

# Landmarks offered as starting points by the "nearest free bed" finder.
SEARCH_PRESETS = [
    {"id": "monas", "name": "Monas, Jakarta", "lat": -6.1754, "lon": 106.8272},
    {"id": "gedung-sate", "name": "Gedung Sate, Bandung", "lat": -6.9025, "lon": 107.6188},
    {"id": "simpang-lima", "name": "Simpang Lima, Semarang", "lat": -6.9904, "lon": 110.4229},
    {"id": "tugu-jogja", "name": "Tugu, Yogyakarta", "lat": -7.7829, "lon": 110.3671},
    {"id": "tugu-pahlawan", "name": "Tugu Pahlawan, Surabaya", "lat": -7.2458, "lon": 112.7378},
    {"id": "merdeka-medan", "name": "Lapangan Merdeka, Medan", "lat": 3.5907, "lon": 98.6778},
    {"id": "losari", "name": "Pantai Losari, Makassar", "lat": -5.1436, "lon": 119.4072},
    {"id": "puputan", "name": "Lapangan Puputan, Denpasar", "lat": -8.6566, "lon": 115.2177},
]
