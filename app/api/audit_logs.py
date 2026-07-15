from fastapi import APIRouter, Depends
from fastapi import Query

from app.auth.security import require_admin
from app.services.logging_service import list_audit_logs


router = APIRouter(
    prefix="/admin/audit-logs",
    tags=["audit-logs"],
)


@router.get("")
def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None, max_length=80),
    resource_type: str | None = Query(default=None, max_length=40),
    position: str | None = Query(default=None, pattern="^(operations|customer_service|finance)$"),
    current_user: dict = Depends(require_admin),
):
    return {
        "items": list_audit_logs(
            limit=limit,
            action=action,
            resource_type=resource_type,
            position=position,
        ),
    }
