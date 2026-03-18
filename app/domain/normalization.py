from __future__ import annotations

import json
import re
from typing import Any

from app.domain.models import CanonicalMedication, IncomingMedication


_DOSE_PATTERN = re.compile(r"^(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]+)$")
_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
_MG_CONVERSION_FACTORS = {
    "mg": 1.0,
    "mcg": 0.001,
    "g": 1000.0,
}
_FREQUENCY_ALIASES = {
    "od": "once daily",
    "qd": "once daily",
    "once daily": "once daily",
    "daily": "once daily",
    "bid": "twice daily",
    "bd": "twice daily",
    "twice daily": "twice daily",
    "tid": "three times daily",
    "t.i.d": "three times daily",
    "three times daily": "three times daily",
}


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().lower().split())
    return cleaned or None


def normalize_drug_name(value: str | None, aliases: dict[str, str]) -> str | None:
    normalized = normalize_text(value)
    if normalized is None:
        return None
    compact = _NON_ALNUM_PATTERN.sub(" ", normalized)
    compact = " ".join(compact.split())
    if compact in aliases:
        return aliases[compact]
    return compact


def normalize_unit(unit: str | None, unit_aliases: dict[str, str]) -> str | None:
    normalized = normalize_text(unit)
    if normalized is None:
        return None
    return unit_aliases.get(normalized, normalized)


def normalize_frequency(value: str | None) -> str | None:
    normalized = normalize_text(value)
    if normalized is None:
        return None
    return _FREQUENCY_ALIASES.get(normalized, normalized)


def convert_to_mg(value: float | None, unit: str | None) -> tuple[float | None, str | None]:
    if value is None or unit is None:
        return value, unit
    factor = _MG_CONVERSION_FACTORS.get(unit)
    if factor is None:
        return value, unit
    return value * factor, "mg"


def parse_dose_value_unit(item: IncomingMedication, unit_aliases: dict[str, str]) -> tuple[float | None, str | None]:
    if item.dose_value is not None:
        return convert_to_mg(item.dose_value, normalize_unit(item.dose_unit, unit_aliases))

    dose_text = normalize_text(item.dose_text)
    if not dose_text:
        return None, None

    match = _DOSE_PATTERN.match(dose_text)
    if not match:
        return None, None

    value = float(match.group("value"))
    unit = normalize_unit(match.group("unit"), unit_aliases)
    return convert_to_mg(value, unit)


def build_dose_signature(value: float | None, unit: str | None) -> str | None:
    if value is None and unit is None:
        return None
    if value is None:
        return unit
    if unit is None:
        return str(value)
    return f"{value:g} {unit}"


def normalize_medication(
    item: IncomingMedication,
    unit_aliases: dict[str, str],
    drug_aliases: dict[str, str] | None = None,
) -> CanonicalMedication:
    dose_value, dose_unit = parse_dose_value_unit(item, unit_aliases)
    aliases = drug_aliases or {}
    return CanonicalMedication(
        drug_name=normalize_drug_name(item.name, aliases) or "unknown",
        dose_value=dose_value,
        dose_unit=dose_unit,
        dose_signature=build_dose_signature(dose_value, dose_unit),
        frequency=normalize_frequency(item.frequency),
        route=normalize_text(item.route),
        status=item.status,
        drug_class=normalize_text(item.drug_class),
    )


def stable_medication_payload(meds: list[CanonicalMedication]) -> list[dict[str, Any]]:
    serialized = [med.model_dump(mode="json") for med in meds]
    return sorted(
        serialized,
        key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")),
    )
