"""Pydantic schemas for API request/response validation."""

import datetime
from pydantic import BaseModel


class FileDisputeRequest(BaseModel):
    transaction_id: str
    reason_code: str
    card_member_statement: str = ""


class DisputeResponse(BaseModel):
    id: str
    reason_code: str
    reason_code_name: str
    tier: str | None
    status: str
    confidence_score: float | None
    reasoning_text: str | None
    filed_at: datetime.datetime
    resolved_at: datetime.datetime | None
    sla: dict
    feature_attributions: list | None = None

    class Config:
        from_attributes = True


class AppealRequest(BaseModel):
    dispute_id: str


class TransactionSummary(BaseModel):
    id: str
    merchant_name: str
    amount: float
    currency: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
