"""
Layer 5 — Trust Safeguards: SLA Guardian + appeal handling.

Tracks BOTH deadlines that actually apply to a U.S. credit card dispute --
not one number pretending to cover both relationships:
  - FCBA/Regulation Z (issuer-to-card-member): acknowledge within 30 days,
    resolve within two billing cycles, no more than 90 days.
  - Amex's own reason-code framework (issuer-to-merchant): a 120-day window
    to raise a dispute, a 20-day window for the merchant to challenge it.
"""

import datetime

FCBA_ACKNOWLEDGE_DAYS = 30
FCBA_RESOLVE_DAYS = 90
MERCHANT_CHALLENGE_DAYS = 20
MERCHANT_DISPUTE_WINDOW_DAYS = 120


def compute_sla_deadlines(filed_at: datetime.datetime) -> dict:
    return {
        "issuer_acknowledge_by": (filed_at + datetime.timedelta(days=FCBA_ACKNOWLEDGE_DAYS)).isoformat(),
        "issuer_resolve_by": (filed_at + datetime.timedelta(days=FCBA_RESOLVE_DAYS)).isoformat(),
        "merchant_challenge_by": (filed_at + datetime.timedelta(days=MERCHANT_CHALLENGE_DAYS)).isoformat(),
        "merchant_dispute_window_ends": (filed_at + datetime.timedelta(days=MERCHANT_DISPUTE_WINDOW_DAYS)).isoformat(),
    }


def compliance_status(filed_at: datetime.datetime, resolved_at: datetime.datetime | None, now: datetime.datetime | None = None) -> dict:
    now = now or datetime.datetime.utcnow()
    end = resolved_at or now
    days_elapsed = (end - filed_at).days

    issuer_deadline_met = days_elapsed <= FCBA_RESOLVE_DAYS if resolved_at else now <= filed_at + datetime.timedelta(days=FCBA_RESOLVE_DAYS)
    days_remaining = FCBA_RESOLVE_DAYS - days_elapsed

    return {
        "days_elapsed": days_elapsed,
        "days_remaining_on_issuer_clock": max(days_remaining, 0),
        "issuer_deadline_at_risk": days_remaining <= 10 and resolved_at is None,
        "issuer_deadline_met": issuer_deadline_met,
    }
