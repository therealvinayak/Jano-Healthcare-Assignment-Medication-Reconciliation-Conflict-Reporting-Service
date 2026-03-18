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


def _conflict_key(conflict_type: str, involved_drugs: list[str], involved_sources: list[str]) -> str:
    content = {
        "type": conflict_type,
        "drugs": sorted(involved_drugs),
        "sources": sorted(involved_sources),
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
        normalized_medications = [normalize_medication(item, unit_aliases) for item in request.medications]
        stable_payload = stable_medication_payload(normalized_medications)
        payload_hash = _stable_hash(stable_payload)

        source = request.source.value
        latest = self.repository.get_latest_snapshot(request.patient_id, source)
        created_new_version = True

        if latest and latest.get("payload_hash") == payload_hash:
            snapshot = latest
            created_new_version = False
        else:
            version = 1 if not latest else latest["version"] + 1
            snapshot = self.repository.create_snapshot(
                {
                    "patient_id": request.patient_id,
                    "clinic_id": patient["clinic_id"],
                    "source": source,
                    "version": version,
                    "captured_at": request.captured_at.astimezone(timezone.utc),
                    "source_reference": request.source_reference,
                    "payload_hash": payload_hash,
                    "medications": stable_payload,
                }
            )

        latest_snapshots = self.repository.get_latest_snapshots_for_patient(request.patient_id)
        source_medications = {}
        for snapshot_source, latest_snapshot in latest_snapshots.items():
            source_medications[SourceType(snapshot_source)] = [
                CanonicalMedication.model_validate(med)
                for med in latest_snapshot.get("medications", [])
            ]

        source_medications[request.source] = normalized_medications

        blacklisted_combinations = self.rules.get("blacklisted_class_combinations", [])
        detected = detect_conflicts(source_medications, blacklisted_combinations)

        active_keys: set[str] = set()
        upserted_conflicts: list[dict[str, Any]] = []

        for conflict in detected:
            involved_sources = [src.value for src in conflict.involved_sources]
            conflict_key = _conflict_key(
                conflict.conflict_type.value,
                conflict.involved_drugs,
                involved_sources,
            )
            active_keys.add(conflict_key)
            saved = self.repository.upsert_conflict(
                {
                    "patient_id": request.patient_id,
                    "clinic_id": patient["clinic_id"],
                    "conflict_type": conflict.conflict_type.value,
                    "involved_drugs": sorted(conflict.involved_drugs),
                    "involved_sources": sorted(involved_sources),
                    "summary": conflict.summary,
                    "details": conflict.details,
                    "conflict_key": conflict_key,
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
