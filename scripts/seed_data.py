from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.database import get_database
from app.domain.models import IngestMedicationRequest, IncomingMedication, SourceType
from app.domain.services import MedicationService
from app.persistence.repositories import MongoRepository


def build_seed_service() -> MedicationService:
    repository = MongoRepository(get_database())
    repository.ensure_indexes()
    return MedicationService.from_rules_file(repository, "config/conflict_rules.json")


def run_seed() -> None:
    service = build_seed_service()

    patient_ids: list[str] = []
    clinics = ["clinic-a", "clinic-b"]

    for index in range(12):
        created = service.create_patient(
            {
                "clinic_id": clinics[index % len(clinics)],
                "first_name": f"Patient{index + 1}",
                "last_name": "Demo",
                "date_of_birth": datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=index * 365),
            }
        )
        patient_ids.append(created["_id"])

    for i, patient_id in enumerate(patient_ids):
        service.ingest(
            IngestMedicationRequest(
                patient_id=patient_id,
                source=SourceType.CLINIC_EMR,
                captured_at=datetime.now(timezone.utc),
                medications=[
                    IncomingMedication(
                        name="Lisinopril",
                        dose_value=10,
                        dose_unit="mg",
                        status="active",
                        drug_class="ace inhibitor",
                    ),
                    IncomingMedication(
                        name="Warfarin",
                        dose_value=5,
                        dose_unit="mg",
                        status="active",
                        drug_class="anticoagulant",
                    ),
                ],
            )
        )

        if i % 2 == 0:
            service.ingest(
                IngestMedicationRequest(
                    patient_id=patient_id,
                    source=SourceType.HOSPITAL_DISCHARGE,
                    captured_at=datetime.now(timezone.utc),
                    medications=[
                        IncomingMedication(
                            name="Lisinopril",
                            dose_value=20,
                            dose_unit="mg",
                            status="active",
                            drug_class="ace inhibitor",
                        )
                    ],
                )
            )

        if i % 3 == 0:
            service.ingest(
                IngestMedicationRequest(
                    patient_id=patient_id,
                    source=SourceType.PATIENT_REPORTED,
                    captured_at=datetime.now(timezone.utc),
                    medications=[
                        IncomingMedication(
                            name="Ibuprofen",
                            dose_value=400,
                            dose_unit="mg",
                            status="active",
                            drug_class="nsaid",
                        ),
                        IncomingMedication(
                            name="Warfarin",
                            dose_value=5,
                            dose_unit="mg",
                            status="stopped",
                            drug_class="anticoagulant",
                        ),
                    ],
                )
            )

    print("Seed complete: created 12 patients with mixed conflict scenarios.")


if __name__ == "__main__":
    run_seed()
