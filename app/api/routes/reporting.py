from fastapi import APIRouter, Depends, Query

from app.api.deps import get_repository

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/clinics/{clinic_id}/unresolved-conflicts")
def unresolved_conflicts_by_clinic(clinic_id: str, repository=Depends(get_repository)):
    rows = repository.get_unresolved_patients_by_clinic(clinic_id)
    return {
        "clinic_id": clinic_id,
        "patients_with_unresolved_conflicts": len(rows),
        "patients": rows,
    }


@router.get("/conflicts-30d")
def conflict_summary_30d(
    min_conflicts: int = Query(default=2, ge=1),
    repository=Depends(get_repository),
):
    return {
        "window_days": 30,
        "minimum_conflicts": min_conflicts,
        "results": repository.get_30d_conflict_summary(min_conflicts=min_conflicts),
    }
