from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_medication_service
from app.domain.models import ResolveConflictRequest
from app.domain.services import MedicationService

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.patch("/{conflict_id}/resolve")
def resolve_conflict(
    conflict_id: str,
    request: ResolveConflictRequest,
    service: MedicationService = Depends(get_medication_service),
):
    updated = service.resolve_conflict(conflict_id, request)
    if not updated:
        raise HTTPException(status_code=404, detail="Conflict not found")
    return {
        "conflict_id": updated["_id"],
        "resolved": updated["resolved"],
        "resolution_reason": updated.get("resolution_reason"),
        "chosen_source": updated.get("chosen_source"),
        "resolved_at": updated.get("resolved_at"),
    }
