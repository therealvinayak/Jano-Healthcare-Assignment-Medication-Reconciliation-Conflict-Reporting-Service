from datetime import datetime, timezone


def test_resolution_manual_override_requires_resolver(client):
    patient = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": "clinic-res",
            "first_name": "Mia",
            "last_name": "Grant",
            "date_of_birth": "1980-01-01T00:00:00Z",
        },
    )
    patient_id = patient.json()["id"]

    client.post(
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
                }
            ],
        },
    )

    ingest_with_conflict = client.post(
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
                }
            ],
        },
    )

    conflict_id = ingest_with_conflict.json()["conflicts"][0]["_id"]
    response = client.patch(
        f"/api/v1/conflicts/{conflict_id}/resolve",
        json={
            "resolution_reason": "manual_override",
            "chosen_source": "clinic_emr",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "resolver_required"


def test_resolution_response_includes_severity(client):
    patient = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": "clinic-res",
            "first_name": "Ria",
            "last_name": "Parker",
            "date_of_birth": "1986-01-01T00:00:00Z",
        },
    )
    patient_id = patient.json()["id"]

    client.post(
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
                }
            ],
        },
    )

    ingest_with_conflict = client.post(
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
                }
            ],
        },
    )

    conflict = ingest_with_conflict.json()["conflicts"][0]
    conflict_id = conflict["_id"]

    resolved = client.patch(
        f"/api/v1/conflicts/{conflict_id}/resolve",
        json={
            "resolution_reason": "clinician_reviewed",
            "chosen_source": "clinic_emr",
            "resolver": "dr.jones",
        },
    )

    assert resolved.status_code == 200
    assert resolved.json()["severity"] in {"high", "medium", "low", "critical"}
