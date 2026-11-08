"""Data model for bed snapshots."""
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from .config import FACILITIES_BY_ID, WARDS


class SnapshotIn(BaseModel):
    """Bed count of one ward at one facility at one moment (from a hospital information system)."""

    facility_id: str
    ward: str = Field(..., description="icu, isolation, general, maternity, nicu or emergency")
    timestamp: datetime | None = Field(None, description="Time of the count; defaults to now (UTC)")
    capacity: int = Field(..., ge=0, le=2000, description="Beds available for patients in this ward")
    occupied: int = Field(..., ge=0, le=2000, description="Beds in use")
    admissions: int = Field(0, ge=0, le=2000, description="Patients admitted since the previous snapshot")
    discharges: int = Field(0, ge=0, le=2000, description="Patients discharged since the previous snapshot")

    @model_validator(mode="after")
    def consistent(self) -> "SnapshotIn":
        facility = FACILITIES_BY_ID.get(self.facility_id)
        if facility is None:
            raise ValueError(f"unknown facility '{self.facility_id}'")
        if self.ward not in WARDS:
            raise ValueError(f"unknown ward '{self.ward}'")
        if self.ward not in facility["beds"]:
            raise ValueError(f"facility '{self.facility_id}' has no {self.ward} ward")
        if self.occupied > self.capacity:
            raise ValueError("occupied beds cannot exceed capacity")
        return self


class Snapshot(SnapshotIn):
    timestamp: datetime
