"""
Layer 1 — Evidence Collector.

Gathers everything relevant to a disputed transaction: the transaction record
itself, the card member's prior transaction history with this merchant
(network signal), and structured fields extracted from the card member's
free-text dispute statement via spaCy NER.

Where network-provided evidence already exists (this module's job is to
simulate that ingestion point), it's treated as one input rather than
something FairResolve has to independently re-derive.
"""

import datetime

import spacy
from sqlalchemy.orm import Session

from app.models import Transaction, CardMember, Merchant

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def parse_card_member_statement(statement: str) -> dict:
    """
    Extract structured fields (dates, amounts, organizations) from the card
    member's free-text dispute description using spaCy NER.
    """
    if not statement:
        return {"dates": [], "amounts": [], "organizations": []}

    doc = _get_nlp()(statement)
    return {
        "dates": [ent.text for ent in doc.ents if ent.label_ == "DATE"],
        "amounts": [ent.text for ent in doc.ents if ent.label_ == "MONEY"],
        "organizations": [ent.text for ent in doc.ents if ent.label_ == "ORG"],
    }


def collect_evidence(db: Session, transaction: Transaction, card_member_statement: str) -> dict:
    """
    Assemble the full evidence package for a dispute:
      - the transaction record itself (network signal)
      - the card member's prior undisputed transaction history with this merchant
      - the merchant's historical loss rate on disputes
      - whether this card member shows a repeat-dispute pattern (possible
        friendly fraud signal -- surfaced as a flag, not an accusation)
      - structured fields parsed from the card member's statement
    """
    card_member: CardMember = transaction.card_member
    merchant: Merchant = transaction.merchant

    # Identity-signal matching (device/IP/shipping) checks against ALL prior
    # transactions with this merchant, regardless of dispute status --
    # disputing a transaction doesn't change what physical device or address
    # was used to make it. This is a distinct concept from the credibility
    # metric below, which specifically wants a CLEAN history count.
    all_prior_transactions = (
        db.query(Transaction)
        .filter(
            Transaction.card_member_id == card_member.id,
            Transaction.merchant_id == merchant.id,
            Transaction.id != transaction.id,
        )
        .all()
    )
    device_match_count = sum(1 for t in all_prior_transactions if t.device_id == transaction.device_id)
    ip_match_count = sum(1 for t in all_prior_transactions if t.ip_address == transaction.ip_address)
    shipping_match_count = sum(
        1 for t in all_prior_transactions if t.shipping_address == transaction.shipping_address
    )

    # Prior UNDISPUTED transaction count: specifically for the Credibility
    # Prior Engine, which wants a track record of clean history, not just
    # any prior transaction.
    prior_undisputed_count = sum(1 for t in all_prior_transactions if not t.was_disputed)

    # Repeat-dispute pattern: has this card member filed several disputes in
    # the past 90 days where delivery was actually confirmed? This is the
    # signal that should push a case toward escalation rather than letting
    # a confident device/IP match alone auto-resolve it for the merchant --
    # a repeated pattern deserves human judgment either way.
    ninety_days_ago = transaction.created_at - datetime.timedelta(days=90)
    recent_disputed_and_delivered = (
        db.query(Transaction)
        .filter(
            Transaction.card_member_id == card_member.id,
            Transaction.was_disputed == True,  # noqa: E712
            Transaction.delivery_scan_present == True,  # noqa: E712
            Transaction.created_at >= ninety_days_ago,
            Transaction.id != transaction.id,
        )
        .count()
    )
    repeat_dispute_pattern = recent_disputed_and_delivered >= 2

    parsed_statement = parse_card_member_statement(card_member_statement)

    return {
        "transaction": {
            "id": transaction.id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "delivery_scan_present": transaction.delivery_scan_present,
            "device_id": transaction.device_id,
            "ip_address": transaction.ip_address,
            "shipping_address": transaction.shipping_address,
        },
        "prior_undisputed_txn_count": prior_undisputed_count,
        "device_id_match": device_match_count > 0,
        "ip_address_match": ip_match_count > 0,
        "shipping_address_match": shipping_match_count > 0,
        "merchant_historical_loss_rate": merchant.historical_loss_rate,
        "merchant_fraud_program_enrolled": merchant.fraud_full_recourse_enrolled,
        "merchant_fraud_program_enrolled_at": (
            merchant.fraud_full_recourse_enrolled_at.isoformat()
            if merchant.fraud_full_recourse_enrolled_at else None
        ),
        "repeat_dispute_pattern": repeat_dispute_pattern,
        "repeat_disputed_delivered_count": recent_disputed_and_delivered,
        "card_member_statement_parsed": parsed_statement,
    }
