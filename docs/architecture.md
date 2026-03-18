# Architecture Diagram

This one-page view shows the runtime request path and how conflict/reporting data is stored for auditability.

```mermaid
flowchart TD
    Nurse[Nurse / Clinician]
    Client[API Client / Swagger / Postman]
    FastAPI[FastAPI App\nRouters + DTO Validation]
    Service[Medication Service\nNormalization + Versioning + Conflict Detection]
    Rules[Conflict Rules JSON\nunit aliases + class blacklist]
    Repo[Repository Layer\nMongoRepository]

    subgraph MongoDB
      P[(patients)]
      S[(medication_snapshots)]
      C[(medication_conflicts)]
    end

    Nurse --> Client
    Client --> FastAPI
    FastAPI --> Service
    Service --> Rules
    Service --> Repo

    Repo --> P
    Repo --> S
    Repo --> C

    S --> Service
    C --> FastAPI

    FastAPI --> Reports[Reports API\n- unresolved conflicts by clinic\n- 30-day threshold summary]
    Reports --> Client

    FastAPI --> History[History API\npatient timeline by source/version]
    History --> Client

    FastAPI --> Resolution[Resolve Conflict API\nreason + chosen source + timestamp]
    Resolution --> C
```

## Notes
- Snapshot versions are immutable per patient+source and only increment on semantic payload changes.
- Conflict records are stored as separate documents for reporting performance and audit trail clarity.
- Resolution is explicit and auditable via reason, selected source, resolver, and timestamp.
