from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from itertools import groupby

from app.domain.models import (
    CanonicalMedication,
    ConflictCandidate,
    ConflictSeverity,
    ConflictType,
    MedicationStatus,
    SourceType,
)


def _active_medications_by_drug(
    source_medications: dict[SourceType, list[CanonicalMedication]],
) -> dict[str, list[tuple[SourceType, CanonicalMedication]]]:
    by_drug: dict[str, list[tuple[SourceType, CanonicalMedication]]] = defaultdict(list)
    for source, meds in source_medications.items():
        for med in meds:
            # UNKNOWN status should not be treated as active for high-confidence mismatches.
            if med.status == MedicationStatus.ACTIVE:
                by_drug[med.drug_name].append((source, med))
    return by_drug


class ConflictRule(ABC):
    @abstractmethod
    def evaluate(
        self,
        source_medications: dict[SourceType, list[CanonicalMedication]],
        blacklisted_class_combinations: list[list[str]],
    ) -> list[ConflictCandidate]:
        raise NotImplementedError


class DoseMismatchRule(ConflictRule):
    def evaluate(
        self,
        source_medications: dict[SourceType, list[CanonicalMedication]],
        blacklisted_class_combinations: list[list[str]],
    ) -> list[ConflictCandidate]:
        return detect_dose_mismatches(source_medications)


class FrequencyMismatchRule(ConflictRule):
    def evaluate(
        self,
        source_medications: dict[SourceType, list[CanonicalMedication]],
        blacklisted_class_combinations: list[list[str]],
    ) -> list[ConflictCandidate]:
        return detect_frequency_mismatches(source_medications)


class DuplicateEntryRule(ConflictRule):
    def evaluate(
        self,
        source_medications: dict[SourceType, list[CanonicalMedication]],
        blacklisted_class_combinations: list[list[str]],
    ) -> list[ConflictCandidate]:
        return detect_duplicate_entries(source_medications)


class StoppedMismatchRule(ConflictRule):
    def evaluate(
        self,
        source_medications: dict[SourceType, list[CanonicalMedication]],
        blacklisted_class_combinations: list[list[str]],
    ) -> list[ConflictCandidate]:
        return detect_stopped_mismatches(source_medications)


class ClassCombinationRule(ConflictRule):
    def evaluate(
        self,
        source_medications: dict[SourceType, list[CanonicalMedication]],
        blacklisted_class_combinations: list[list[str]],
    ) -> list[ConflictCandidate]:
        return detect_blacklisted_class_combinations(source_medications, blacklisted_class_combinations)


def detect_dose_mismatches(
    source_medications: dict[SourceType, list[CanonicalMedication]],
) -> list[ConflictCandidate]:
    conflicts: list[ConflictCandidate] = []
    by_drug = _active_medications_by_drug(source_medications)

    for drug_name, values in by_drug.items():
        if len(values) < 2:
            continue

        observed_doses = {
            source.value: (med.dose_signature or "unknown") for source, med in values
        }
        dose_set = set(observed_doses.values())
        has_known_dose = any(value != "unknown" for value in dose_set)
        if len(dose_set) <= 1 or not has_known_dose:
            continue

        sources = sorted({source for source, _ in values}, key=lambda s: s.value)
        conflicts.append(
            ConflictCandidate(
                conflict_type=ConflictType.DOSE_MISMATCH,
                severity=ConflictSeverity.HIGH,
                involved_drugs=[drug_name],
                involved_sources=sources,
                summary=f"Dose mismatch for {drug_name}",
                details={
                    "doses": sorted(dose_set),
                    "observed_by_source": observed_doses,
                },
            )
        )

    return conflicts


def detect_frequency_mismatches(
    source_medications: dict[SourceType, list[CanonicalMedication]],
) -> list[ConflictCandidate]:
    conflicts: list[ConflictCandidate] = []
    by_drug = _active_medications_by_drug(source_medications)

    for drug_name, values in by_drug.items():
        if len(values) < 2:
            continue

        observed_frequencies = {
            source.value: (med.frequency or "unknown") for source, med in values
        }
        frequency_set = set(observed_frequencies.values())
        has_known_frequency = any(value != "unknown" for value in frequency_set)
        if len(frequency_set) <= 1 or not has_known_frequency:
            continue

        sources = sorted({source for source, _ in values}, key=lambda s: s.value)
        conflicts.append(
            ConflictCandidate(
                conflict_type=ConflictType.FREQUENCY_MISMATCH,
                severity=ConflictSeverity.MEDIUM,
                involved_drugs=[drug_name],
                involved_sources=sources,
                summary=f"Frequency mismatch for {drug_name}",
                details={
                    "frequencies": sorted(frequency_set),
                    "observed_by_source": observed_frequencies,
                },
            )
        )

    return conflicts


def detect_duplicate_entries(
    source_medications: dict[SourceType, list[CanonicalMedication]],
) -> list[ConflictCandidate]:
    conflicts: list[ConflictCandidate] = []

    for source, meds in source_medications.items():
        active = [med for med in meds if med.status != MedicationStatus.STOPPED]
        active.sort(
            key=lambda med: (
                med.drug_name,
                med.dose_signature or "",
                med.frequency or "",
                med.route or "",
            )
        )

        for drug_name, group in groupby(
            active,
            key=lambda med: (
                med.drug_name,
                med.dose_signature or "",
                med.frequency or "",
                med.route or "",
            ),
        ):
            duplicates = list(group)
            if len(duplicates) < 2:
                continue

            signatures = sorted(
                {
                    " | ".join(
                        [
                            med.dose_signature or "unknown dose",
                            med.frequency or "unknown frequency",
                            med.route or "unknown route",
                        ]
                    )
                    for med in duplicates
                }
            )
            conflicts.append(
                ConflictCandidate(
                    conflict_type=ConflictType.DUPLICATE_ENTRY,
                    severity=ConflictSeverity.LOW,
                    involved_drugs=[drug_name[0]],
                    involved_sources=[source],
                    summary=f"Duplicate active entries for {drug_name[0]} in {source.value}",
                    details={
                        "source": source.value,
                        "duplicate_count": len(duplicates),
                        "signatures": signatures,
                    },
                )
            )

    return conflicts


def detect_stopped_mismatches(
    source_medications: dict[SourceType, list[CanonicalMedication]],
) -> list[ConflictCandidate]:
    conflicts: list[ConflictCandidate] = []
    by_drug: dict[str, list[tuple[SourceType, MedicationStatus]]] = defaultdict(list)

    for source, meds in source_medications.items():
        for med in meds:
            by_drug[med.drug_name].append((source, med.status))

    for drug_name, statuses in by_drug.items():
        unique_statuses = {status for _, status in statuses}
        if MedicationStatus.STOPPED in unique_statuses and (MedicationStatus.ACTIVE in unique_statuses):
            sources = sorted({source for source, _ in statuses}, key=lambda s: s.value)
            conflicts.append(
                ConflictCandidate(
                    conflict_type=ConflictType.STOPPED_MISMATCH,
                    severity=ConflictSeverity.HIGH,
                    involved_drugs=[drug_name],
                    involved_sources=sources,
                    summary=f"{drug_name} is active in one source and stopped in another",
                    details={
                        "statuses": [
                            {"source": source.value, "status": status.value}
                            for source, status in sorted(statuses, key=lambda x: x[0].value)
                        ]
                    },
                )
            )

    return conflicts


def detect_blacklisted_class_combinations(
    source_medications: dict[SourceType, list[CanonicalMedication]],
    blacklisted_pairs: list[list[str]],
) -> list[ConflictCandidate]:
    conflicts: list[ConflictCandidate] = []
    class_to_drugs: dict[str, set[str]] = defaultdict(set)
    class_to_sources: dict[str, set[SourceType]] = defaultdict(set)

    for source, meds in source_medications.items():
        for med in meds:
            if med.status == MedicationStatus.STOPPED or not med.drug_class:
                continue
            class_to_drugs[med.drug_class].add(med.drug_name)
            class_to_sources[med.drug_class].add(source)

    for pair in blacklisted_pairs:
        if len(pair) != 2:
            continue
        class_a, class_b = sorted([pair[0].strip().lower(), pair[1].strip().lower()])
        if class_a not in class_to_drugs or class_b not in class_to_drugs:
            continue

        involved_drugs = sorted(class_to_drugs[class_a] | class_to_drugs[class_b])
        involved_sources = sorted(class_to_sources[class_a] | class_to_sources[class_b], key=lambda s: s.value)
        conflicts.append(
            ConflictCandidate(
                conflict_type=ConflictType.CLASS_COMBINATION,
                severity=ConflictSeverity.CRITICAL,
                involved_drugs=involved_drugs,
                involved_sources=involved_sources,
                summary=f"Blacklisted class combination detected: {class_a} + {class_b}",
                details={"class_pair": [class_a, class_b]},
            )
        )

    return conflicts


def detect_conflicts(
    source_medications: dict[SourceType, list[CanonicalMedication]],
    blacklisted_class_combinations: list[list[str]],
) -> list[ConflictCandidate]:
    rules: list[ConflictRule] = [
        DuplicateEntryRule(),
        DoseMismatchRule(),
        FrequencyMismatchRule(),
        StoppedMismatchRule(),
        ClassCombinationRule(),
    ]
    conflicts: list[ConflictCandidate] = []
    for rule in rules:
        conflicts.extend(rule.evaluate(source_medications, blacklisted_class_combinations))
    return conflicts
