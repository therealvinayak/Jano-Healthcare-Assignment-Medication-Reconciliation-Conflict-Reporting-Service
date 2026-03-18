from fastapi import APIRouter, Depends

from app.api.deps import get_medication_service
from app.domain.services import MedicationService

router = APIRouter(prefix="/patients", tags=["history"])


@router.get("/{patient_id}/history")
def patient_history(
    patient_id: str,
    service: MedicationService = Depends(get_medication_service),
):
    return service.get_patient_history(patient_id)
