from datetime import datetime, timezone


def test_ingest_route_creates_conflicts(client):
    create_patient_response = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": "clinic-a",
            "first_name": "Mia",
            "last_name": "Stone",
            "date_of_birth": "1980-01-01T00:00:00Z",
        },
    )
    assert create_patient_response.status_code == 200
    patient_id = create_patient_response.json()["id"]

    first_ingest = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "clinic_emr",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "Lisinopril",
                    "dose_value": 10,
                    "dose_unit": "mg",
                    "status": "active",
                    "drug_class": "ace inhibitor",
                }
            ],
        },
    )
    assert first_ingest.status_code == 200

    second_ingest = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "hospital_discharge",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "Lisinopril",
                    "dose_value": 20,
                    "dose_unit": "mg",
                    "status": "active",
                    "drug_class": "ace inhibitor",
                }
            ],
        },
    )

    assert second_ingest.status_code == 200
    assert second_ingest.json()["conflict_count"] >= 1
