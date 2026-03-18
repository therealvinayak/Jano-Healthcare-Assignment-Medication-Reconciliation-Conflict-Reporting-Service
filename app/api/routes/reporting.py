from fastapi import APIRouter, Depends, Query

from app.api.deps import get_medication_service
from app.domain.services import MedicationService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/clinics/{clinic_id}/unresolved-conflicts")
def unresolved_conflicts_by_clinic(
    clinic_id: str,
    service: MedicationService = Depends(get_medication_service),
):
    return service.get_unresolved_conflicts_by_clinic(clinic_id)


@router.get("/conflicts-30d")
def conflict_summary_30d(
    min_conflicts: int = Query(default=2, ge=1),
    service: MedicationService = Depends(get_medication_service),
):
    return service.get_conflict_summary_30d(min_conflicts=min_conflicts)
