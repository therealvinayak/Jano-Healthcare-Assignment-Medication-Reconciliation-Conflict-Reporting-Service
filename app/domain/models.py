from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    CLINIC_EMR = "clinic_emr"
    HOSPITAL_DISCHARGE = "hospital_discharge"
    PATIENT_REPORTED = "patient_reported"


class MedicationStatus(str, Enum):
    ACTIVE = "active"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


class ConflictType(str, Enum):
    DOSE_MISMATCH = "dose_mismatch"
    CLASS_COMBINATION = "class_combination"
    STOPPED_MISMATCH = "stopped_mismatch"


class IncomingMedication(BaseModel):
    name: str = Field(min_length=1)
    dose_value: float | None = None
    dose_unit: str | None = None
    dose_text: str | None = None
    frequency: str | None = None
    route: str | None = None
    status: MedicationStatus = MedicationStatus.ACTIVE
    drug_class: str | None = None


class IngestMedicationRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    source: SourceType
    captured_at: datetime
    medications: list[IncomingMedication] = Field(default_factory=list)
    source_reference: str | None = None


class CanonicalMedication(BaseModel):
    drug_name: str
    dose_value: float | None = None
    dose_unit: str | None = None
    dose_signature: str | None = None
    frequency: str | None = None
    route: str | None = None
    status: MedicationStatus = MedicationStatus.UNKNOWN
    drug_class: str | None = None


class ConflictCandidate(BaseModel):
    conflict_type: ConflictType
    involved_drugs: list[str]
    involved_sources: list[SourceType]
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class ResolveConflictRequest(BaseModel):
    resolution_reason: str = Field(min_length=3)
    chosen_source: SourceType | None = None
    resolver: str | None = None


class ConflictRecordResponse(BaseModel):
    id: str
    patient_id: str
    clinic_id: str
    conflict_type: ConflictType
    involved_drugs: list[str]
    involved_sources: list[SourceType]
    summary: str
    details: dict[str, Any]
    resolved: bool
    resolution_reason: str | None
    chosen_source: SourceType | None
    resolved_at: datetime | None
    created_at: datetime
    last_seen_at: datetime


class PatientCreateRequest(BaseModel):
    clinic_id: str = Field(min_length=1)
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    date_of_birth: datetime


class PatientResponse(BaseModel):
    id: str
    clinic_id: str
    first_name: str
    last_name: str
    date_of_birth: datetime
    created_at: datetime
