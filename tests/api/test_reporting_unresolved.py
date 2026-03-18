from datetime import datetime, timezone


def test_unresolved_conflicts_report_by_clinic(client):
    patient_response = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": "clinic-z",
            "first_name": "Lara",
            "last_name": "Jade",
            "date_of_birth": "1977-05-14T00:00:00Z",
        },
    )
    patient_id = patient_response.json()["id"]

    client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "clinic_emr",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "Warfarin",
                    "dose_value": 5,
                    "dose_unit": "mg",
                    "status": "active",
                    "drug_class": "anticoagulant",
                }
            ],
        },
    )

    client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "patient_reported",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "Ibuprofen",
                    "dose_value": 400,
                    "dose_unit": "mg",
                    "status": "active",
                    "drug_class": "nsaid",
                }
            ],
        },
    )

    report = client.get("/api/v1/reports/clinics/clinic-z/unresolved-conflicts")
    assert report.status_code == 200
    body = report.json()

    assert body["patients_with_unresolved_conflicts"] == 1
    assert body["patients"][0]["patient_id"] == patient_id
    assert body["patients"][0]["conflict_count"] >= 1
