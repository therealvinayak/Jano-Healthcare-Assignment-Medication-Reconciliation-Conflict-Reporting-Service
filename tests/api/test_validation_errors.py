from datetime import datetime, timezone


def test_ingest_missing_required_source_returns_structured_validation_error(client):
    create_patient = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": "clinic-val",
            "first_name": "Mina",
            "last_name": "Vale",
            "date_of_birth": "1991-04-11T00:00:00Z",
        },
    )
    patient_id = create_patient.json()["id"]

    response = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [],
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"


def test_ingest_malformed_datetime_returns_validation_error(client):
    create_patient = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": "clinic-val",
            "first_name": "Nita",
            "last_name": "Kane",
            "date_of_birth": "1988-02-20T00:00:00Z",
        },
    )
    patient_id = create_patient.json()["id"]

    response = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "clinic_emr",
            "captured_at": "not-a-date",
            "medications": [],
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
