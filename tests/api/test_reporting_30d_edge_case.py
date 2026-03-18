from datetime import datetime, timezone


def test_conflicts_30d_respects_min_threshold(client):
    patient_response = client.post(
        "/api/v1/patients",
        json={
            "clinic_id": "clinic-threshold",
            "first_name": "Evan",
            "last_name": "Cole",
            "date_of_birth": "1985-09-10T00:00:00Z",
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

    client.post(
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
                },
                {
                    "name": "Warfarin",
                    "dose_value": 5,
                    "dose_unit": "mg",
                    "status": "stopped",
                    "drug_class": "anticoagulant",
                },
            ],
        },
    )

    at_least_two = client.get("/api/v1/reports/conflicts-30d?min_conflicts=2")
    assert at_least_two.status_code == 200
    assert at_least_two.json()["results"] == [
        {"clinic_id": "clinic-threshold", "patients_with_conflicts": 1}
    ]

    at_least_three = client.get("/api/v1/reports/conflicts-30d?min_conflicts=3")
    assert at_least_three.status_code == 200
    assert at_least_three.json()["results"] == []
