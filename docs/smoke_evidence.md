# Manual API Smoke Evidence

Note: Local MongoDB was unavailable on this machine during this run, so this smoke pass uses the same API endpoints with dependency-overridden in-memory repository.

## create_patient
Status: 200
```json
{
  "id": "7e4d4aa7-6c10-4288-8644-0ac630669d3a",
  "clinic_id": "clinic-demo",
  "first_name": "Nora",
  "last_name": "Miles",
  "date_of_birth": "1982-06-21T00:00:00Z",
  "created_at": "2026-03-18T04:40:33.223114Z"
}
```

## ingest_clinic
Status: 200
```json
{
  "snapshot_id": "46219b28-02d3-47ca-adbc-d1b7c954f390",
  "snapshot_version": 1,
  "created_new_version": true,
  "patient_id": "7e4d4aa7-6c10-4288-8644-0ac630669d3a",
  "source": "clinic_emr",
  "conflict_count": 0,
  "conflicts": []
}
```

## ingest_hospital
Status: 200
```json
{
  "snapshot_id": "b028a0b5-b409-431f-b55c-f9c7ac562841",
  "snapshot_version": 1,
  "created_new_version": true,
  "patient_id": "7e4d4aa7-6c10-4288-8644-0ac630669d3a",
  "source": "hospital_discharge",
  "conflict_count": 3,
  "conflicts": [
    {
      "_id": "ba14c714-5596-4e0a-a8bb-9ce1221bcecd",
      "created_at": "2026-03-18T04:40:33.230852+00:00",
      "last_seen_at": "2026-03-18T04:40:33.230852+00:00",
      "resolved": false,
      "resolution_reason": null,
      "chosen_source": null,
      "resolved_at": null,
      "patient_id": "7e4d4aa7-6c10-4288-8644-0ac630669d3a",
      "clinic_id": "clinic-demo",
      "conflict_type": "dose_mismatch",
      "involved_drugs": [
        "lisinopril"
      ],
      "involved_sources": [
        "clinic_emr",
        "hospital_discharge"
      ],
      "summary": "Dose mismatch for lisinopril",
      "details": {
        "doses": [
          "10 mg",
          "20 mg"
        ]
      },
      "conflict_key": "e0615aedaa894cd633407c8b8e258158e0b7f62666e469ef5ec9e0c920249229"
    },
    {
      "_id": "375ab2d6-fa28-485e-91d7-8d37894fb88e",
      "created_at": "2026-03-18T04:40:33.230979+00:00",
      "last_seen_at": "2026-03-18T04:40:33.230979+00:00",
      "resolved": false,
      "resolution_reason": null,
      "chosen_source": null,
      "resolved_at": null,
      "patient_id": "7e4d4aa7-6c10-4288-8644-0ac630669d3a",
      "clinic_id": "clinic-demo",
      "conflict_type": "stopped_mismatch",
      "involved_drugs": [
        "warfarin"
      ],
      "involved_sources": [
        "clinic_emr",
        "hospital_discharge"
      ],
      "summary": "warfarin is active in one source and stopped in another",
      "details": {
        "statuses": [
          {
            "source": "clinic_emr",
            "status": "active"
          },
          {
            "source": "hospital_discharge",
            "status": "stopped"
          }
        ]
      },
      "conflict_key": "a29bd9f476904b30f92a17dad9e673d54d60880ed858a4f566dbca17f11c47d8"
    },
    {
      "_id": "02b515ac-a5e5-4b5f-b184-845247533eba",
      "created_at": "2026-03-18T04:40:33.231068+00:00",
      "last_seen_at": "2026-03-18T04:40:33.231068+00:00",
      "resolved": false,
      "resolution_reason": null,
      "chosen_source": null,
      "resolved_at": null,
      "patient_id": "7e4d4aa7-6c10-4288-8644-0ac630669d3a",
      "clinic_id": "clinic-demo",
      "conflict_type": "class_combination",
      "involved_drugs": [
        "ibuprofen",
        "warfarin"
      ],
      "involved_sources": [
        "clinic_emr",
        "hospital_discharge"
      ],
      "summary": "Blacklisted class combination detected: anticoagulant + nsaid",
      "details": {
        "class_pair": [
          "anticoagulant",
          "nsaid"
        ]
      },
      "conflict_key": "1a98fd38907d4977abb5bcff04f113e7d898a322fc6e6da56a58904c415ca8c5"
    }
  ]
}
```

## unresolved_before
Status: 200
```json
{
  "clinic_id": "clinic-demo",
  "patients_with_unresolved_conflicts": 1,
  "patients": [
    {
      "patient_id": "7e4d4aa7-6c10-4288-8644-0ac630669d3a",
      "patient_name": "Nora Miles",
      "clinic_id": "clinic-demo",
      "conflict_count": 3,
      "conflicts": [
        {
          "id": "ba14c714-5596-4e0a-a8bb-9ce1221bcecd",
          "type": "dose_mismatch",
          "summary": "Dose mismatch for lisinopril",
          "involved_drugs": [
            "lisinopril"
          ],
          "last_seen_at": "2026-03-18T04:40:33.230852+00:00"
        },
        {
          "id": "375ab2d6-fa28-485e-91d7-8d37894fb88e",
          "type": "stopped_mismatch",
          "summary": "warfarin is active in one source and stopped in another",
          "involved_drugs": [
            "warfarin"
          ],
          "last_seen_at": "2026-03-18T04:40:33.230979+00:00"
        },
        {
          "id": "02b515ac-a5e5-4b5f-b184-845247533eba",
          "type": "class_combination",
          "summary": "Blacklisted class combination detected: anticoagulant + nsaid",
          "involved_drugs": [
            "ibuprofen",
            "warfarin"
          ],
          "last_seen_at": "2026-03-18T04:40:33.231068+00:00"
        }
      ]
    }
  ]
}
```

## resolve_first_conflict
Status: 200
```json
{
  "conflict_id": "ba14c714-5596-4e0a-a8bb-9ce1221bcecd",
  "resolved": true,
  "resolution_reason": "Reviewed by clinician",
  "chosen_source": "clinic_emr",
  "resolved_at": "2026-03-18T04:40:33.235641+00:00"
}
```

## unresolved_after
Status: 200
```json
{
  "clinic_id": "clinic-demo",
  "patients_with_unresolved_conflicts": 1,
  "patients": [
    {
      "patient_id": "7e4d4aa7-6c10-4288-8644-0ac630669d3a",
      "patient_name": "Nora Miles",
      "clinic_id": "clinic-demo",
      "conflict_count": 2,
      "conflicts": [
        {
          "id": "375ab2d6-fa28-485e-91d7-8d37894fb88e",
          "type": "stopped_mismatch",
          "summary": "warfarin is active in one source and stopped in another",
          "involved_drugs": [
            "warfarin"
          ],
          "last_seen_at": "2026-03-18T04:40:33.230979+00:00"
        },
        {
          "id": "02b515ac-a5e5-4b5f-b184-845247533eba",
          "type": "class_combination",
          "summary": "Blacklisted class combination detected: anticoagulant + nsaid",
          "involved_drugs": [
            "ibuprofen",
            "warfarin"
          ],
          "last_seen_at": "2026-03-18T04:40:33.231068+00:00"
        }
      ]
    }
  ]
}
```

## summary_30d
Status: 200
```json
{
  "window_days": 30,
  "minimum_conflicts": 2,
  "results": [
    {
      "clinic_id": "clinic-demo",
      "patients_with_conflicts": 1
    }
  ]
}
```

## history
Status: 200
```json
{
  "patient_id": "7e4d4aa7-6c10-4288-8644-0ac630669d3a",
  "versions": [
    {
      "snapshot_id": "46219b28-02d3-47ca-adbc-d1b7c954f390",
      "source": "clinic_emr",
      "version": 1,
      "captured_at": "2026-03-18T04:40:33.202265+00:00",
      "medications": [
        {
          "drug_name": "lisinopril",
          "dose_value": 10.0,
          "dose_unit": "mg",
          "dose_signature": "10 mg",
          "frequency": null,
          "route": null,
          "status": "active",
          "drug_class": "ace inhibitor"
        },
        {
          "drug_name": "warfarin",
          "dose_value": 5.0,
          "dose_unit": "mg",
          "dose_signature": "5 mg",
          "frequency": null,
          "route": null,
          "status": "active",
          "drug_class": "anticoagulant"
        }
      ]
    },
    {
      "snapshot_id": "b028a0b5-b409-431f-b55c-f9c7ac562841",
      "source": "hospital_discharge",
      "version": 1,
      "captured_at": "2026-03-18T04:40:33.202265+00:00",
      "medications": [
        {
          "drug_name": "ibuprofen",
          "dose_value": 400.0,
          "dose_unit": "mg",
          "dose_signature": "400 mg",
          "frequency": null,
          "route": null,
          "status": "active",
          "drug_class": "nsaid"
        },
        {
          "drug_name": "lisinopril",
          "dose_value": 20.0,
          "dose_unit": "mg",
          "dose_signature": "20 mg",
          "frequency": null,
          "route": null,
          "status": "active",
          "drug_class": "ace inhibitor"
        },
        {
          "drug_name": "warfarin",
          "dose_value": 5.0,
          "dose_unit": "mg",
          "dose_signature": "5 mg",
          "frequency": null,
          "route": null,
          "status": "stopped",
          "drug_class": "anticoagulant"
        }
      ]
    }
  ]
}
```

## invalid_ingest_missing_patient
Status: 404
```json
{
  "error": {
    "code": "patient_not_found",
    "message": "Patient not found",
    "details": null
  }
}
```
