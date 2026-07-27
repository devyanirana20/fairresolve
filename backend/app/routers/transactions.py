from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("")
def list_transactions(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).order_by(Transaction.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "merchant_name": t.merchant.name,
            "amount": t.amount,
            "currency": t.currency,
            "created_at": t.created_at.isoformat(),
            "was_disputed": t.was_disputed,
        }
        for t in transactions
    ]
