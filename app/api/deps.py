from functools import lru_cache

from app.core.config import get_settings
from app.core.database import get_database
from app.domain.services import MedicationService
from app.persistence.repositories import MongoRepository


@lru_cache(maxsize=1)
def get_repository() -> MongoRepository:
    repo = MongoRepository(get_database())
    repo.ensure_indexes()
    return repo


def get_medication_service() -> MedicationService:
    settings = get_settings()
    return MedicationService.from_rules_file(get_repository(), settings.conflict_rules_path)
