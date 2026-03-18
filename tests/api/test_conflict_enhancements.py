from datetime import datetime, timezone


def _create_patient(client, clinic_id: str = "clinic-enh") -> str:
    response = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": clinic_id,
            "first_name": "Kira",
            "last_name": "Moore",
            "date_of_birth": "1984-07-09T00:00:00Z",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_ingest_detects_frequency_mismatch_conflict(client):
    patient_id = _create_patient(client)

    first_ingest = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "clinic_emr",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "Metformin",
                    "dose_value": 500,
                    "dose_unit": "mg",
                    "frequency": "OD",
                    "status": "active",
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
                    "name": "Metformin",
                    "dose_value": 500,
                    "dose_unit": "mg",
                    "frequency": "BID",
                    "status": "active",
                }
            ],
        },
    )

    assert second_ingest.status_code == 200
    conflict_types = {c["conflict_type"] for c in second_ingest.json()["conflicts"]}
    assert "frequency_mismatch" in conflict_types
    assert all("severity" in c for c in second_ingest.json()["conflicts"])


def test_ingest_detects_duplicate_entries_in_single_source(client):
    patient_id = _create_patient(client)

    response = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "patient_reported",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "Atorvastatin",
                    "dose_value": 40,
                    "dose_unit": "mg",
                    "frequency": "once daily",
                    "route": "oral",
                    "status": "active",
                },
                {
                    "name": "Atorvastatin",
                    "dose_value": 40,
                    "dose_unit": "mg",
                    "frequency": "once daily",
                    "route": "oral",
                    "status": "active",
                },
            ],
        },
    )

    assert response.status_code == 200
    conflicts = response.json()["conflicts"]
    duplicate = [c for c in conflicts if c["conflict_type"] == "duplicate_entry"]
    assert len(duplicate) == 1
    assert duplicate[0]["details"]["duplicate_count"] == 2


def test_ingest_normalizes_drug_name_punctuation_to_avoid_false_conflicts(client):
    patient_id = _create_patient(client)

    clinic_ingest = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "clinic_emr",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "Metformin-ER",
                    "dose_value": 500,
                    "dose_unit": "mg",
                    "frequency": "twice daily",
                    "status": "active",
                }
            ],
        },
    )
    assert clinic_ingest.status_code == 200

    hospital_ingest = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "hospital_discharge",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "metformin er",
                    "dose_value": 500,
                    "dose_unit": "mg",
                    "frequency": "twice daily",
                    "status": "active",
                }
            ],
        },
    )

    assert hospital_ingest.status_code == 200
    assert hospital_ingest.json()["conflict_count"] == 0


def test_ingest_equivalent_dose_units_do_not_create_mismatch(client):
    patient_id = _create_patient(client)

    clinic_ingest = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "clinic_emr",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "Levothyroxine",
                    "dose_text": "0.5 g",
                    "status": "active",
                }
            ],
        },
    )
    assert clinic_ingest.status_code == 200

    hospital_ingest = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "hospital_discharge",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "medications": [
                {
                    "name": "Levothyroxine",
                    "dose_value": 500,
                    "dose_unit": "mg",
                    "status": "active",
                }
            ],
        },
    )

    assert hospital_ingest.status_code == 200
    conflict_types = {c["conflict_type"] for c in hospital_ingest.json()["conflicts"]}
    assert "dose_mismatch" not in conflict_types


def test_ingest_same_payload_is_idempotent_for_snapshot_version(client):
    patient_id = _create_patient(client)

    payload = {
        "patient_id": patient_id,
        "source": "clinic_emr",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "medications": [
            {
                "name": "Amlodipine",
                "dose_value": 5,
                "dose_unit": "mg",
                "status": "active",
            }
        ],
    }

    first = client.post("/api/v1/medications/ingest", json=payload)
    second = client.post("/api/v1/medications/ingest", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["snapshot_version"] == second.json()["snapshot_version"]
    assert second.json()["created_new_version"] is False
