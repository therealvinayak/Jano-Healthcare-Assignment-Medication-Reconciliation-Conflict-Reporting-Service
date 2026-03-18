from app.domain.models import IncomingMedication
from app.domain.normalization import normalize_medication


def test_normalize_converts_grams_to_mg_equivalent_signature():
    med = IncomingMedication(name="Levothyroxine", dose_text="0.5 g")
    normalized = normalize_medication(med, unit_aliases={"g": "g"})

    assert normalized.dose_unit == "mg"
    assert normalized.dose_value == 500
    assert normalized.dose_signature == "500 mg"


def test_normalize_frequency_aliases_bid_to_twice_daily():
    med = IncomingMedication(name="Metformin", frequency="BID")
    normalized = normalize_medication(med, unit_aliases={})

    assert normalized.frequency == "twice daily"


def test_normalize_parses_free_text_dose_with_suffix_text():
    med = IncomingMedication(name="Metformin", dose_text="500 mg tablet")
    normalized = normalize_medication(med, unit_aliases={"mg": "mg"})

    assert normalized.dose_value == 500
    assert normalized.dose_unit == "mg"
    assert normalized.dose_signature == "500 mg"
