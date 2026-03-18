from fastapi import APIRouter, Depends

from app.api.deps import get_repository

router = APIRouter(prefix="/patients", tags=["history"])


@router.get("/{patient_id}/history")
def patient_history(patient_id: str, repository=Depends(get_repository)):
    snapshots = repository.get_patient_history(patient_id)
    return {
        "patient_id": patient_id,
        "versions": [
            {
                "snapshot_id": row["_id"],
                "source": row["source"],
                "version": row["version"],
                "captured_at": row["captured_at"],
                "medications": row["medications"],
            }
            for row in snapshots
        ],
    }
