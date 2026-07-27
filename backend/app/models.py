"""
Database models for FairResolve.

Uses SQLite locally for zero-setup development (`sqlite:///./fairresolve.db`).
Swap DATABASE_URL to a Postgres connection string for production ---
SQLAlchemy's ORM layer means no model code changes are needed to do that.
"""

import datetime
import enum
import uuid

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Enum as SAEnum, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime.datetime:
    return datetime.datetime.utcnow()


class CardMember(Base):
    __tablename__ = "card_members"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    account_created_at = Column(DateTime, default=_now)

    disputes = relationship("Dispute", back_populates="card_member")
    transactions = relationship("Transaction", back_populates="card_member")


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    # Rolling stat used by the Credibility Prior Engine: what fraction of this
    # merchant's disputes (for a given reason code family) have historically
    # been lost by the merchant. A low number is a mild point in their favor.
    historical_loss_rate = Column(Float, default=0.05)
    fraud_full_recourse_enrolled = Column(Boolean, default=False)
    fraud_full_recourse_enrolled_at = Column(DateTime, nullable=True)

    transactions = relationship("Transaction", back_populates="merchant")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=_uuid)
    card_member_id = Column(String, ForeignKey("card_members.id"), nullable=False)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    created_at = Column(DateTime, default=_now)

    # Signals the Credibility Prior Engine and Fair-Weighing Model read.
    device_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    shipping_address = Column(String, nullable=True)
    delivery_scan_present = Column(Boolean, default=True)
    was_disputed = Column(Boolean, default=False)

    card_member = relationship("CardMember", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")


class DisputeStatus(str, enum.Enum):
    FILED = "filed"
    EVIDENCE_COLLECTED = "evidence_collected"
    TIER_ROUTED = "tier_routed"
    WEIGHED = "weighed"
    AUTO_RESOLVED_CARD_MEMBER = "auto_resolved_card_member"
    AUTO_RESOLVED_MERCHANT = "auto_resolved_merchant"
    FLAGGED_FOR_REVIEW = "flagged_for_review"
    HUMAN_REVIEWED = "human_reviewed"
    APPEALED = "appealed"


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(String, primary_key=True, default=_uuid)
    reason_code = Column(String, nullable=False)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    card_member_id = Column(String, ForeignKey("card_members.id"), nullable=False)

    card_member_statement = Column(Text, nullable=True)  # free-text intake, parsed by spaCy

    status = Column(SAEnum(DisputeStatus), default=DisputeStatus.FILED)
    tier = Column(String, nullable=True)  # set once routed

    confidence_score = Column(Float, nullable=True)  # 0-100, set by the weighing model
    reasoning_text = Column(Text, nullable=True)  # the Transparent Reasoning Layer's output
    feature_attributions = Column(Text, nullable=True)  # JSON-encoded Captum attributions

    filed_at = Column(DateTime, default=_now)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    appeal_requested = Column(Boolean, default=False)

    card_member = relationship("CardMember", back_populates="disputes")
    transaction = relationship("Transaction")
    evidence_items = relationship("EvidenceItem", back_populates="dispute")


class EvidenceItem(Base):
    """A single piece of evidence gathered by the Evidence Collector (Layer 1)."""
    __tablename__ = "evidence_items"

    id = Column(String, primary_key=True, default=_uuid)
    dispute_id = Column(String, ForeignKey("disputes.id"), nullable=False)
    source = Column(String, nullable=False)  # e.g. "network", "merchant", "card_member_intake"
    field_name = Column(String, nullable=False)  # e.g. "delivery_scan_present"
    value = Column(String, nullable=False)
    collected_at = Column(DateTime, default=_now)

    dispute = relationship("Dispute", back_populates="evidence_items")
