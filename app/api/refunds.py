from fastapi import APIRouter, Depends

from app.auth.security import require_admin
from app.services.refund_service import list_refund_transactions


router = APIRouter(
    prefix="/admin/refunds",
    tags=["refunds"],
)


@router.get("")
def get_refunds(
    limit: int = 50,
    current_user: dict = Depends(require_admin),
):
    return {
        "items": list_refund_transactions(limit=limit),
    }
