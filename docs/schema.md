# MongoDB Schema and Indexing Rationale

## Collections

## patients
- _id: string (UUID)
- clinic_id: string
- first_name: string
- last_name: string
- date_of_birth: datetime
- created_at: datetime

Why: Demographics and clinic ownership are stable and queried by clinic for reporting.

## medication_snapshots
- _id: string (UUID)
- patient_id: string
- clinic_id: string
- source: enum (clinic_emr, hospital_discharge, patient_reported)
- version: int
- captured_at: datetime
- source_reference: string | null
- payload_hash: string
- medications: array of canonical medication objects
- created_at: datetime

Why: Immutable snapshot history allows longitudinal traceability and source-specific versioning.

## medication_conflicts
- _id: string (UUID)
- patient_id: string
- clinic_id: string
- conflict_type: enum (dose_mismatch, class_combination, stopped_mismatch)
- involved_drugs: string[]
- involved_sources: string[]
- summary: string
- details: object
- conflict_key: string (deterministic hash)
- resolved: boolean
- resolution_reason: string | null
- chosen_source: string | null
- resolved_at: datetime | null
- resolved_by: string | null
- created_at: datetime
- last_seen_at: datetime

Why: Separate conflict records improve auditability and make cross-patient reporting/indexing straightforward.

## Indexes
- patients: (clinic_id)
  - supports clinic-level reporting joins
- medication_snapshots: (patient_id, source, version desc)
  - supports latest version lookup per source
- medication_snapshots: (patient_id, captured_at desc)
  - supports patient history retrieval
- medication_conflicts: (clinic_id, resolved, last_seen_at desc)
  - supports unresolved-by-clinic dashboard query
- medication_conflicts unique: (patient_id, conflict_key)
  - idempotent conflict upsert

## Versioning Decision
A new snapshot version is created only when the incoming normalized medication payload hash differs from the latest snapshot for the same patient and source.

Benefits:
- Preserves clinically relevant change history
- Avoids noisy duplicate versions

Trade-off:
- Hash-based semantic equality may miss nuanced differences not represented in normalized fields.
