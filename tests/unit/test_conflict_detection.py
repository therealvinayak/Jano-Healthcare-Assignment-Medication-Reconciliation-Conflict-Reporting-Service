from app.domain.conflict_detection import detect_conflicts
from app.domain.models import CanonicalMedication, MedicationStatus, SourceType


def test_detects_dose_mismatch_and_stopped_mismatch():
    source_medications = {
        SourceType.CLINIC_EMR: [
            CanonicalMedication(
                drug_name="lisinopril",
                dose_value=10,
                dose_unit="mg",
                dose_signature="10 mg",
                status=MedicationStatus.ACTIVE,
                drug_class="ace inhibitor",
            ),
            CanonicalMedication(
                drug_name="warfarin",
                dose_value=5,
                dose_unit="mg",
                dose_signature="5 mg",
                status=MedicationStatus.ACTIVE,
                drug_class="anticoagulant",
            )
        ],
        SourceType.HOSPITAL_DISCHARGE: [
            CanonicalMedication(
                drug_name="lisinopril",
                dose_value=20,
                dose_unit="mg",
                dose_signature="20 mg",
                status=MedicationStatus.ACTIVE,
                drug_class="ace inhibitor",
            ),
            CanonicalMedication(
                drug_name="warfarin",
                dose_value=5,
                dose_unit="mg",
                dose_signature="5 mg",
                status=MedicationStatus.STOPPED,
                drug_class="anticoagulant",
            )
        ],
    }

    conflicts = detect_conflicts(source_medications, blacklisted_class_combinations=[])
    conflict_types = {c.conflict_type.value for c in conflicts}

    assert "dose_mismatch" in conflict_types
    assert "stopped_mismatch" in conflict_types


def test_detects_blacklisted_class_combination():
    source_medications = {
        SourceType.CLINIC_EMR: [
            CanonicalMedication(
                drug_name="lisinopril",
                status=MedicationStatus.ACTIVE,
                drug_class="ace inhibitor",
            )
        ],
        SourceType.PATIENT_REPORTED: [
            CanonicalMedication(
                drug_name="losartan",
                status=MedicationStatus.ACTIVE,
                drug_class="arb",
            )
        ],
    }

    conflicts = detect_conflicts(
        source_medications,
        blacklisted_class_combinations=[["ace inhibitor", "arb"]],
    )

    assert any(c.conflict_type.value == "class_combination" for c in conflicts)


def test_detects_frequency_mismatch():
    source_medications = {
        SourceType.CLINIC_EMR: [
            CanonicalMedication(
                drug_name="metformin",
                dose_signature="500 mg",
                frequency="once daily",
                status=MedicationStatus.ACTIVE,
            )
        ],
        SourceType.HOSPITAL_DISCHARGE: [
            CanonicalMedication(
                drug_name="metformin",
                dose_signature="500 mg",
                frequency="twice daily",
                status=MedicationStatus.ACTIVE,
            )
        ],
    }

    conflicts = detect_conflicts(source_medications, blacklisted_class_combinations=[])
    assert any(c.conflict_type.value == "frequency_mismatch" for c in conflicts)


def test_detects_duplicate_entries_in_single_source():
    source_medications = {
        SourceType.PATIENT_REPORTED: [
            CanonicalMedication(
                drug_name="atorvastatin",
                dose_signature="40 mg",
                frequency="once daily",
                route="oral",
                status=MedicationStatus.ACTIVE,
            ),
            CanonicalMedication(
                drug_name="atorvastatin",
                dose_signature="40 mg",
                frequency="once daily",
                route="oral",
                status=MedicationStatus.ACTIVE,
            ),
        ]
    }

    conflicts = detect_conflicts(source_medications, blacklisted_class_combinations=[])
    duplicate_conflicts = [c for c in conflicts if c.conflict_type.value == "duplicate_entry"]

    assert len(duplicate_conflicts) == 1
    assert duplicate_conflicts[0].details["duplicate_count"] == 2
