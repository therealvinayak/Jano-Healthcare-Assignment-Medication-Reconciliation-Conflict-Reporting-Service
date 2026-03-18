from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_medication_service
from app.domain.models import IngestMedicationRequest
from app.domain.services import MedicationService

router = APIRouter(prefix="/medications", tags=["medications"])


@router.post("/ingest")
def ingest_medications(
    request: IngestMedicationRequest,
    service: MedicationService = Depends(get_medication_service),
):
    try:
        return service.ingest(request)
    except ValueError as exc:
        if str(exc) == "patient_not_found":
            raise HTTPException(status_code=404, detail="Patient not found") from exc
        raise HTTPException(status_code=400, detail="Invalid ingestion request") from exc
