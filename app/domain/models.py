from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


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
    FREQUENCY_MISMATCH = "frequency_mismatch"
    DUPLICATE_ENTRY = "duplicate_entry"
    CLASS_COMBINATION = "class_combination"
    STOPPED_MISMATCH = "stopped_mismatch"


class ConflictSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncomingMedication(BaseModel):
    name: str = Field(min_length=1)
    dose_value: float | None = Field(default=None, gt=0)
    dose_unit: str | None = None
    dose_text: str | None = None
    frequency: str | None = None
    route: str | None = None
    status: MedicationStatus = MedicationStatus.ACTIVE
    drug_class: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name cannot be blank")
        return cleaned

    @field_validator("dose_unit", "dose_text", "frequency", "route", "drug_class", mode="before")
    @classmethod
    def normalize_optional_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class IngestMedicationRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    source: SourceType
    captured_at: datetime
    medications: list[IncomingMedication] = Field(default_factory=list, min_length=1)
    source_reference: str | None = None

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("patient_id cannot be blank")
        return cleaned

    @field_validator("captured_at")
    @classmethod
    def validate_captured_at_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must include timezone information")
        return value

    @field_validator("source_reference", mode="before")
    @classmethod
    def normalize_source_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


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
    severity: ConflictSeverity
    involved_drugs: list[str]
    involved_sources: list[SourceType]
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class ResolveConflictRequest(BaseModel):
    resolution_reason: str = Field(min_length=3)
    chosen_source: SourceType | None = None
    resolver: str | None = None

    @field_validator("resolver", mode="before")
    @classmethod
    def normalize_resolver(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


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

    @field_validator("clinic_id", "first_name", "last_name")
    @classmethod
    def validate_required_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("field cannot be blank")
        return cleaned


class PatientResponse(BaseModel):
    id: str
    clinic_id: str
    first_name: str
    last_name: str
    date_of_birth: datetime
    created_at: datetime
