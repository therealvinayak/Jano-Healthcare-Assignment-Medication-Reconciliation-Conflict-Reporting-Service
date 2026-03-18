from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.api.deps import get_medication_service, get_repository
from app.domain.services import MedicationService
from app.main import app
from app.persistence.repositories import InMemoryRepository


def run_smoke() -> dict:
    repository = InMemoryRepository()
    rules = json.loads(Path("config/conflict_rules.json").read_text(encoding="utf-8"))
    service = MedicationService(repository=repository, rules=rules)

    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_medication_service] = lambda: service

    now = datetime.now(timezone.utc).isoformat()

    with TestClient(app) as client:
        create_patient = client.post(
            "/api/v1/patients",
            json={
                "clinic_id": "clinic-demo",
                "first_name": "Nora",
                "last_name": "Miles",
                "date_of_birth": "1982-06-21T00:00:00Z",
            },
        )
        patient_id = create_patient.json()["id"]

        ingest_clinic = client.post(
            "/api/v1/medications/ingest",
            json={
                "patient_id": patient_id,
                "source": "clinic_emr",
                "captured_at": now,
                "medications": [
                    {
                        "name": "Lisinopril",
                        "dose_value": 10,
                        "dose_unit": "mg",
                        "status": "active",
                        "drug_class": "ace inhibitor",
                    },
                    {
                        "name": "Warfarin",
                        "dose_value": 5,
                        "dose_unit": "mg",
                        "status": "active",
                        "drug_class": "anticoagulant",
                    },
                ],
            },
        )

        ingest_hospital = client.post(
            "/api/v1/medications/ingest",
            json={
                "patient_id": patient_id,
                "source": "hospital_discharge",
                "captured_at": now,
                "medications": [
                    {
                        "name": "Lisinopril",
                        "dose_value": 20,
                        "dose_unit": "mg",
                        "status": "active",
                        "drug_class": "ace inhibitor",
                    },
                    {
                        "name": "Warfarin",
                        "dose_value": 5,
                        "dose_unit": "mg",
                        "status": "stopped",
                        "drug_class": "anticoagulant",
                    },
                    {
                        "name": "Ibuprofen",
                        "dose_value": 400,
                        "dose_unit": "mg",
                        "status": "active",
                        "drug_class": "nsaid",
                    },
                ],
            },
        )

        unresolved_before = client.get(
            "/api/v1/reports/clinics/clinic-demo/unresolved-conflicts"
        )

        first_conflict_id = unresolved_before.json()["patients"][0]["conflicts"][0]["id"]
        resolve = client.patch(
            f"/api/v1/conflicts/{first_conflict_id}/resolve",
            json={
                "resolution_reason": "Reviewed by clinician",
                "chosen_source": "clinic_emr",
                "resolver": "nurse.alex",
            },
        )

        unresolved_after = client.get(
            "/api/v1/reports/clinics/clinic-demo/unresolved-conflicts"
        )
        summary_30d = client.get("/api/v1/reports/conflicts-30d?min_conflicts=2")
        history = client.get(f"/api/v1/patients/{patient_id}/history")

        invalid_ingest = client.post(
            "/api/v1/medications/ingest",
            json={
                "patient_id": "missing-patient",
                "source": "clinic_emr",
                "captured_at": now,
                "medications": [],
            },
        )

    app.dependency_overrides.clear()

    return {
        "create_patient": {
            "status": create_patient.status_code,
            "body": create_patient.json(),
        },
        "ingest_clinic": {
            "status": ingest_clinic.status_code,
            "body": ingest_clinic.json(),
        },
        "ingest_hospital": {
            "status": ingest_hospital.status_code,
            "body": ingest_hospital.json(),
        },
        "unresolved_before": {
            "status": unresolved_before.status_code,
            "body": unresolved_before.json(),
        },
        "resolve_first_conflict": {
            "status": resolve.status_code,
            "body": resolve.json(),
        },
        "unresolved_after": {
            "status": unresolved_after.status_code,
            "body": unresolved_after.json(),
        },
        "summary_30d": {
            "status": summary_30d.status_code,
            "body": summary_30d.json(),
        },
        "history": {
            "status": history.status_code,
            "body": history.json(),
        },
        "invalid_ingest_missing_patient": {
            "status": invalid_ingest.status_code,
            "body": invalid_ingest.json(),
        },
    }


def write_markdown_report(results: dict) -> None:
    lines = [
        "# Manual API Smoke Evidence",
        "",
        "Note: Local MongoDB was unavailable on this machine during this run, so this smoke pass uses the same API endpoints with dependency-overridden in-memory repository.",
        "",
    ]

    for key, value in results.items():
        lines.append(f"## {key}")
        lines.append(f"Status: {value['status']}")
        lines.append("```json")
        lines.append(json.dumps(value["body"], indent=2, default=str))
        lines.append("```")
        lines.append("")

    Path("docs/smoke_evidence.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    output = run_smoke()
    write_markdown_report(output)
    print("Smoke evidence written to docs/smoke_evidence.md")
