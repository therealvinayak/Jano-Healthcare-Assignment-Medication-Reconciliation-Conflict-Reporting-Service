from __future__ import annotations

import re
from typing import Any

from app.domain.models import CanonicalMedication, IncomingMedication


_DOSE_PATTERN = re.compile(r"^(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]+)$")


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().lower().split())
    return cleaned or None


def normalize_unit(unit: str | None, unit_aliases: dict[str, str]) -> str | None:
    normalized = normalize_text(unit)
    if normalized is None:
        return None
    return unit_aliases.get(normalized, normalized)


def parse_dose_value_unit(item: IncomingMedication, unit_aliases: dict[str, str]) -> tuple[float | None, str | None]:
    if item.dose_value is not None:
        return item.dose_value, normalize_unit(item.dose_unit, unit_aliases)

    dose_text = normalize_text(item.dose_text)
    if not dose_text:
        return None, None

    match = _DOSE_PATTERN.match(dose_text)
    if not match:
        return None, None

    value = float(match.group("value"))
    unit = normalize_unit(match.group("unit"), unit_aliases)
    return value, unit


def build_dose_signature(value: float | None, unit: str | None) -> str | None:
    if value is None and unit is None:
        return None
    if value is None:
        return unit
    if unit is None:
        return str(value)
    return f"{value:g} {unit}"


def normalize_medication(item: IncomingMedication, unit_aliases: dict[str, str]) -> CanonicalMedication:
    dose_value, dose_unit = parse_dose_value_unit(item, unit_aliases)
    return CanonicalMedication(
        drug_name=normalize_text(item.name) or "unknown",
        dose_value=dose_value,
        dose_unit=dose_unit,
        dose_signature=build_dose_signature(dose_value, dose_unit),
        frequency=normalize_text(item.frequency),
        route=normalize_text(item.route),
        status=item.status,
        drug_class=normalize_text(item.drug_class),
    )


def stable_medication_payload(meds: list[CanonicalMedication]) -> list[dict[str, Any]]:
    serialized = [med.model_dump(mode="json") for med in meds]
    return sorted(serialized, key=lambda x: (x["drug_name"], x.get("dose_signature") or "", x.get("status") or ""))
