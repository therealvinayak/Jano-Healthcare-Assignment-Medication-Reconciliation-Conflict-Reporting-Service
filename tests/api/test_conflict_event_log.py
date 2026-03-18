from datetime import datetime, timezone


def _create_patient(client, clinic_id: str = "clinic-events") -> str:
    response = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": clinic_id,
            "first_name": "Nora",
            "last_name": "Bell",
            "date_of_birth": "1982-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_conflict_event_log_tracks_detect_resolve_reopen_autoresolve(client, repository):
    patient_id = _create_patient(client)

    first = client.post(
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
    assert first.status_code == 200

    second = client.post(
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
    assert second.status_code == 200
    conflict_id = second.json()["conflicts"][0]["_id"]

    resolved = client.patch(
        f"/api/v1/conflicts/{conflict_id}/resolve",
        json={
            "resolution_reason": "clinician_reviewed",
            "chosen_source": "clinic_emr",
            "resolver": "dr.stone",
        },
    )
    assert resolved.status_code == 200

    reopened = client.post(
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
    assert reopened.status_code == 200

    auto_resolved = client.post(
        "/api/v1/medications/ingest",
        json={
            "patient_id": patient_id,
            "source": "hospital_discharge",
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
    assert auto_resolved.status_code == 200

    events = repository.get_conflict_events(patient_id)
    event_types = {event["event_type"] for event in events}

    assert "detected_new" in event_types
    assert "resolved_manual" in event_types
    assert "detected_reopened" in event_types
    assert "resolved_auto" in event_types


def test_contention_metrics_are_exposed(repository):
    metrics = repository.get_contention_metrics()
    assert "snapshot_retry_count" in metrics
    assert "snapshot_contention_failures" in metrics
