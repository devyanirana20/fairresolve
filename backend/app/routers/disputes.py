import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dispute, DisputeStatus, Transaction
from app.schemas import FileDisputeRequest, DisputeResponse, AppealRequest
from app.reason_codes import get_reason_code, REASON_CODES
from app.tier_router import file_dispute
from app.sla_guardian import compute_sla_deadlines, compliance_status

router = APIRouter(prefix="/api/disputes", tags=["disputes"])


def _to_response(d: Dispute) -> DisputeResponse:
    rc = get_reason_code(d.reason_code)
    sla_deadlines = compute_sla_deadlines(d.filed_at)
    sla_status = compliance_status(d.filed_at, d.resolved_at)
    attributions = json.loads(d.feature_attributions) if d.feature_attributions else None
    return DisputeResponse(
        id=d.id,
        reason_code=d.reason_code,
        reason_code_name=rc.name,
        tier=d.tier,
        status=d.status.value if hasattr(d.status, "value") else d.status,
        confidence_score=d.confidence_score,
        reasoning_text=d.reasoning_text,
        filed_at=d.filed_at,
        resolved_at=d.resolved_at,
        sla={**sla_deadlines, **sla_status},
        feature_attributions=attributions,
    )


@router.get("/reason-codes")
def list_reason_codes():
    return [
        {"code": rc.code, "name": rc.name, "tier": rc.tier.value, "always_human": rc.always_human}
        for rc in REASON_CODES.values()
    ]


@router.post("", response_model=DisputeResponse)
def create_dispute(payload: FileDisputeRequest, db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(Transaction.id == payload.transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if payload.reason_code not in REASON_CODES:
        raise HTTPException(status_code=400, detail=f"Unknown reason code: {payload.reason_code}")

    dispute = file_dispute(db, transaction, payload.reason_code, payload.card_member_statement)
    return _to_response(dispute)


@router.get("", response_model=list[DisputeResponse])
def list_disputes(db: Session = Depends(get_db)):
    disputes = db.query(Dispute).order_by(Dispute.filed_at.desc()).all()
    return [_to_response(d) for d in disputes]


@router.get("/{dispute_id}", response_model=DisputeResponse)
def get_dispute(dispute_id: str, db: Session = Depends(get_db)):
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return _to_response(dispute)


@router.post("/{dispute_id}/appeal", response_model=DisputeResponse)
def appeal_dispute(dispute_id: str, db: Session = Depends(get_db)):
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    resolved_statuses = {
        DisputeStatus.AUTO_RESOLVED_CARD_MEMBER,
        DisputeStatus.AUTO_RESOLVED_MERCHANT,
        DisputeStatus.HUMAN_REVIEWED,
    }
    if dispute.status not in resolved_statuses:
        raise HTTPException(status_code=400, detail="Only resolved disputes can be appealed")
    if dispute.appeal_requested:
        raise HTTPException(status_code=400, detail="This dispute has already been appealed once")

    dispute.appeal_requested = True
    dispute.status = DisputeStatus.APPEALED
    db.commit()
    db.refresh(dispute)
    return _to_response(dispute)
