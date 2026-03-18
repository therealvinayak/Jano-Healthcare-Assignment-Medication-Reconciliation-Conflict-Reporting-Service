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


def test_ingest_rejects_blank_medication_name(client):
    create_patient = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": "clinic-val",
            "first_name": "Ira",
            "last_name": "Lane",
            "date_of_birth": "1990-01-01T00:00:00Z",
        },
    )
    patient_id = create_patient.json()["id"]

    response = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "clinic_emr",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "   ",
                    "dose_value": 10,
                    "dose_unit": "mg",
                }
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_ingest_rejects_non_positive_dose_value(client):
    create_patient = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": "clinic-val",
            "first_name": "Pia",
            "last_name": "Shaw",
            "date_of_birth": "1992-03-01T00:00:00Z",
        },
    )
    patient_id = create_patient.json()["id"]

    response = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "clinic_emr",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "Lisinopril",
                    "dose_value": 0,
                    "dose_unit": "mg",
                }
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_ingest_rejects_timezone_less_captured_at(client):
    create_patient = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": "clinic-val",
            "first_name": "Noa",
            "last_name": "Price",
            "date_of_birth": "1993-05-21T00:00:00Z",
        },
    )
    patient_id = create_patient.json()["id"]

    response = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "clinic_emr",
            "captured_at": "2026-03-18T10:00:00",
            "medications": [
                {
                    "name": "Aspirin",
                    "dose_value": 75,
                    "dose_unit": "mg",
                }
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_ingest_rejects_empty_medication_list(client):
    create_patient = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": "clinic-val",
            "first_name": "Rae",
            "last_name": "York",
            "date_of_birth": "1994-06-15T00:00:00Z",
        },
    )
    patient_id = create_patient.json()["id"]

    response = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "clinic_emr",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
