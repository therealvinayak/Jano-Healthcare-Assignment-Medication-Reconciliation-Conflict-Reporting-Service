from __future__ import annotations

import hashlib
import json
from datetime import timezone
from pathlib import Path
from typing import Any

from app.domain.conflict_detection import detect_conflicts
from app.domain.models import (
    CanonicalMedication,
    IngestMedicationRequest,
    ResolveConflictRequest,
    SourceType,
)
from app.domain.normalization import normalize_medication, stable_medication_payload


def _stable_hash(payload: Any) -> str:
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _conflict_key(
    conflict_type: str,
    severity: str,
    involved_drugs: list[str],
    involved_sources: list[str],
    details: dict[str, Any],
) -> str:
    content = {
        "type": conflict_type,
        "severity": severity,
        "drugs": sorted(involved_drugs),
        "sources": sorted(involved_sources),
        "details": details,
    }
    return _stable_hash(content)


class MedicationService:
    def __init__(self, repository, rules: dict[str, Any]):
        self.repository = repository
        self.rules = rules

    @classmethod
    def from_rules_file(cls, repository, rules_path: str) -> "MedicationService":
        path = Path(rules_path)
        rules = json.loads(path.read_text(encoding="utf-8"))
        return cls(repository=repository, rules=rules)

    def create_patient(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.repository.create_patient(payload)

    def ingest(self, request: IngestMedicationRequest) -> dict[str, Any]:
        patient = self.repository.get_patient(request.patient_id)
        if not patient:
            raise ValueError("patient_not_found")

        unit_aliases = self.rules.get("unit_aliases", {})
        drug_aliases = self.rules.get("drug_name_aliases", {})
        normalized_medications = [
            normalize_medication(item, unit_aliases, drug_aliases) for item in request.medications
        ]
        stable_payload = stable_medication_payload(normalized_medications)
        payload_hash = _stable_hash(stable_payload)
        rules_hash = _stable_hash(self.rules)

        source = request.source.value
        try:
            snapshot, created_new_version = self.repository.create_snapshot_if_new_payload(
                patient_id=request.patient_id,
                source=source,
                clinic_id=patient["clinic_id"],
                captured_at=request.captured_at.astimezone(timezone.utc),
                source_reference=request.source_reference,
                payload_hash=payload_hash,
                medications=stable_payload,
            )
        except RuntimeError as exc:
            if str(exc) == "snapshot_version_contention":
                raise ValueError("snapshot_version_contention") from exc
            raise

        latest_snapshots = self.repository.get_latest_snapshots_for_patient(request.patient_id)
        source_medications = {}
        compared_snapshots: dict[str, dict[str, Any]] = {}
        for snapshot_source, latest_snapshot in latest_snapshots.items():
            source_medications[SourceType(snapshot_source)] = [
                CanonicalMedication.model_validate(med)
                for med in latest_snapshot.get("medications", [])
            ]
            compared_snapshots[snapshot_source] = {
                "snapshot_id": latest_snapshot.get("_id"),
                "version": latest_snapshot.get("version"),
                "captured_at": latest_snapshot.get("captured_at"),
            }

        source_medications[request.source] = normalized_medications
        compared_snapshots[source] = {
            "snapshot_id": snapshot.get("_id"),
            "version": snapshot.get("version"),
            "captured_at": snapshot.get("captured_at"),
        }

        blacklisted_combinations = self.rules.get("blacklisted_class_combinations", [])
        detected = detect_conflicts(source_medications, blacklisted_combinations)

        active_keys: set[str] = set()
        upserted_conflicts: list[dict[str, Any]] = []

        for conflict in detected:
            involved_sources = [src.value for src in conflict.involved_sources]
            conflict_key = _conflict_key(
                conflict.conflict_type.value,
                conflict.severity.value,
                conflict.involved_drugs,
                involved_sources,
                conflict.details,
            )
            active_keys.add(conflict_key)
            saved = self.repository.upsert_conflict(
                {
                    "patient_id": request.patient_id,
                    "clinic_id": patient["clinic_id"],
                    "conflict_type": conflict.conflict_type.value,
                    "severity": conflict.severity.value,
                    "involved_drugs": sorted(conflict.involved_drugs),
                    "involved_sources": sorted(involved_sources),
                    "summary": conflict.summary,
                    "details": conflict.details,
                    "conflict_key": conflict_key,
                    "detection_context": {
                        "rules_hash": rules_hash,
                        "compared_snapshots": compared_snapshots,
                    },
                }
            )
            upserted_conflicts.append(saved)

        self.repository.auto_resolve_conflicts_not_in_keys(request.patient_id, active_keys)

        return {
            "snapshot_id": snapshot["_id"],
            "snapshot_version": snapshot["version"],
            "created_new_version": created_new_version,
            "patient_id": request.patient_id,
            "source": source,
            "conflict_count": len(upserted_conflicts),
            "conflicts": upserted_conflicts,
        }

    def resolve_conflict(self, conflict_id: str, request: ResolveConflictRequest) -> dict[str, Any] | None:
        chosen_source = request.chosen_source.value if request.chosen_source else None
        return self.repository.resolve_conflict(
            conflict_id=conflict_id,
            resolution_reason=request.resolution_reason,
            chosen_source=chosen_source,
            resolver=request.resolver,
        )

    def get_unresolved_conflicts_by_clinic(self, clinic_id: str) -> dict[str, Any]:
        rows = self.repository.get_unresolved_patients_by_clinic(clinic_id)
        return {
            "clinic_id": clinic_id,
            "patients_with_unresolved_conflicts": len(rows),
            "patients": rows,
        }

    def get_conflict_summary_30d(self, min_conflicts: int = 2) -> dict[str, Any]:
        return {
            "window_days": 30,
            "minimum_conflicts": min_conflicts,
            "results": self.repository.get_30d_conflict_summary(min_conflicts=min_conflicts),
        }

    def get_patient_history(self, patient_id: str) -> dict[str, Any]:
        snapshots = self.repository.get_patient_history(patient_id)
        return {
            "patient_id": patient_id,
            "versions": [
                {
                    "snapshot_id": row["_id"],
                    "source": row["source"],
                    "version": row["version"],
                    "captured_at": row["captured_at"],
                    "medications": row["medications"],
                }
                for row in snapshots
            ],
        }
