from fastapi import APIRouter, Depends

from app.api.deps import get_medication_service
from app.domain.models import PatientCreateRequest, PatientResponse
from app.domain.services import MedicationService

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientResponse)
def create_patient(
    request: PatientCreateRequest,
    service: MedicationService = Depends(get_medication_service),
):
    created = service.create_patient(
        {
            "clinic_id": request.clinic_id,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "date_of_birth": request.date_of_birth,
        }
    )
    return {
        "id": created["_id"],
        "clinic_id": created["clinic_id"],
        "first_name": created["first_name"],
        "last_name": created["last_name"],
        "date_of_birth": created["date_of_birth"],
        "created_at": created["created_at"],
    }
