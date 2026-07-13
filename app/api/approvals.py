from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.refund_service import execute_refund_for_approval
from app.auth.security import require_admin
from app.services.approval_service import list_pending_approvals, review_approval
from app.services.logging_service import save_approval_message, write_audit_log


router = APIRouter(
    prefix="/admin/approvals",
    tags=["approvals"],
)


class ReviewApprovalRequest(BaseModel):
    approved: bool


@router.get("")
def get_pending_approvals(
    current_user: dict = Depends(require_admin),
):
    return {
        "items": list_pending_approvals()
    }


@router.post("/{approval_id}/review")
def review(
    approval_id: str,
    request: ReviewApprovalRequest,
    current_user: dict = Depends(require_admin),
):
    result = review_approval(
        approval_id=approval_id,
        reviewer_id=current_user["id"],
        approved=request.approved,
    )

    if not result["found"]:
        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )

    refund_result = None

    if request.approved and result["action_type"] == "refund":
        refund_result = execute_refund_for_approval(approval_id)

    save_approval_message(
        thread_id=result["thread_id"],
        reviewer_id=current_user["id"],
        approval_id=approval_id,
        approved=request.approved,
        refund_result=refund_result,
    )

    write_audit_log(
        user_id=current_user["id"],
        action="approval.review",
        resource_type="approval",
        resource_id=approval_id,
        metadata={
            "approved": request.approved,
            "status": result["status"],
            "refund_result": refund_result,
        },
    )

    return {
        **result,
        "refund_result": refund_result,
    }
