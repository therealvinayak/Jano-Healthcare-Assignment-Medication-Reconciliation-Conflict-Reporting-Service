# Medication Reconciliation and Conflict Reporting Service

FastAPI + MongoDB MVP for ingesting multi-source medication lists, detecting unresolved conflicts, and reporting conflicts at clinic level.

## Setup (Under 5 Minutes)
1. Create and activate virtual environment.
2. Install dependencies.
3. Start MongoDB locally.
4. Copy .env.example to .env and adjust values if needed.
5. Run API server.

### Commands
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

API root: http://127.0.0.1:8000
OpenAPI docs: http://127.0.0.1:8000/docs

## Seed Data
```bash
python scripts/seed_data.py
```
Creates 12 synthetic patients across two clinics with mixed conflict scenarios.

## Test
```bash
pytest
```

## Architecture Overview
The system is structured into four layers.

1. API layer
- FastAPI routers and request/response contracts.

2. Domain layer
- Normalization and conflict detection business rules.
- Service orchestrates versioning, conflict lifecycle, and ingest flow.

3. Persistence layer
- Mongo repository implementation with index initialization and reporting queries.

4. Config/data
- Static conflict rules JSON and environment settings.

Request flow:
- Ingest request -> normalize medications -> compare against latest source snapshot -> create version only on semantic change -> detect conflicts across latest sources -> upsert unresolved conflicts -> auto-resolve no-longer-detected conflicts -> return summary.

## Clinical Assumptions and Trade-offs
1. Dose conflict rule
- Same normalized drug name with differing dose signatures across active sources is flagged.

2. Class combination rule
- Static blacklisted class pairs in config/conflict_rules.json represent unsafe combinations.
- This is a simplification and not a substitute for a real drug-interaction database.

3. Stopped mismatch rule
- A medication marked active in one source and stopped in another is flagged.

4. Truth source policy
- No single source is considered globally authoritative.
- Conflicts remain unresolved until explicitly resolved by clinician action or auto-resolved when no longer detected in latest source state.

5. Versioning policy
- Immutable source snapshots with payload-hash deduplication.

## API Endpoints
- POST /api/v1/patients
- POST /api/v1/medications/ingest
- GET /api/v1/reports/clinics/{clinic_id}/unresolved-conflicts
- GET /api/v1/reports/conflicts-30d?min_conflicts=2
- GET /api/v1/patients/{patient_id}/history
- PATCH /api/v1/conflicts/{conflict_id}/resolve

## Failure Modes and Handling
- Missing patient on ingest: 404.
- Invalid payload shape: 422 (Pydantic validation).
- Unparseable dose text: stored without dose signature; does not crash ingest.
- Duplicate ingest payload for same source: no new snapshot version.

## Known Limitations and Next Steps
1. Uses static rule file, not a clinical drug ontology.
2. No authentication/authorization.
3. Conflict severity scoring is not implemented.
4. Next steps:
- Add user identity and audit trail per action.
- Add richer normalization (brand/generic mapping).
- Add pagination and cursor-based reporting APIs.

## AI Usage Disclosure
1. AI used for
- Initial scaffold planning, boilerplate route/repository generation, and test case brainstorming.

2. Manually reviewed and changed
- Conflict identity logic, snapshot versioning behavior, and unresolved-reporting query shape.

3. One disagreement with AI output
- Rejected a proposed approach that embedded conflicts directly inside snapshots because it would complicate clinic-level unresolved conflict reporting and indexing.
