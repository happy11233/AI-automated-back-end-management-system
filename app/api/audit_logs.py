from fastapi import APIRouter, Depends

from app.auth.security import require_admin
from app.services.logging_service import list_audit_logs


router = APIRouter(
    prefix="/admin/audit-logs",
    tags=["audit-logs"],
)


@router.get("")
def get_audit_logs(
    limit: int = 50,
    current_user: dict = Depends(require_admin),
):
    return {
        "items": list_audit_logs(limit=limit),
    }
