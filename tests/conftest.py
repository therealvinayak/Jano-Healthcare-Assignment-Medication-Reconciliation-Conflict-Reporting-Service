import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_medication_service, get_repository
from app.domain.services import MedicationService
from app.main import app
from app.persistence.repositories import InMemoryRepository


@pytest.fixture()
def repository():
    return InMemoryRepository()


@pytest.fixture()
def rules():
    rules_path = Path("config/conflict_rules.json")
    return json.loads(rules_path.read_text(encoding="utf-8"))


@pytest.fixture()
def service(repository, rules):
    return MedicationService(repository=repository, rules=rules)


@pytest.fixture()
def client(repository, service):
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_medication_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
