"""
Reason code taxonomy for FairResolve.

Source: American Express Chargeback Codes guide (22 Australian merchant reason codes).
Each code is tagged with its tier:
  - Tier 1 (deterministic): a factual record-match with one correct answer.
  - Tier 2 (fairness-narrative): a genuine two-sided disagreement that needs
    the Credibility Prior Engine + Fair-Weighing Model.

For Tier 2 codes, `evidence_fields` lists which structured signals the
Fair-Weighing Model should weight most heavily for that specific dispute type
(mirrors the "what evidence should matter for this dispute type" design
principle from the proposal).
"""

from dataclasses import dataclass, field
from enum import Enum


class Tier(str, Enum):
    DETERMINISTIC = "tier_1_deterministic"
    FAIRNESS_NARRATIVE = "tier_2_fairness_narrative"


@dataclass(frozen=True)
class ReasonCode:
    code: str
    name: str
    tier: Tier
    # For Tier 2 codes: which evidence signals the weighing model should
    # weight most heavily. Ignored for Tier 1 (record-match is uniform).
    evidence_fields: tuple = field(default_factory=tuple)
    # True for codes that must ALWAYS escalate to a human, regardless of
    # confidence (e.g. legal interpretation is out of automation scope by design).
    always_human: bool = False


REASON_CODES: dict[str, ReasonCode] = {
    # ---------------- Tier 1 — Deterministic Verification (14 codes) ----------------
    "4507": ReasonCode("4507", "Incorrect Transaction Amount or PAN Presented", Tier.DETERMINISTIC),
    "4512": ReasonCode("4512", "Multiple Processing", Tier.DETERMINISTIC),
    "4515": ReasonCode("4515", "Paid Through Other Means", Tier.DETERMINISTIC),
    "4516": ReasonCode("4516", "Request For Support Not Fulfilled", Tier.DETERMINISTIC),
    "4517": ReasonCode("4517", "Request For Support Illegible / Incomplete", Tier.DETERMINISTIC),
    "4521": ReasonCode("4521", "Invalid Authorisation", Tier.DETERMINISTIC),
    "4523": ReasonCode("4523", "Unassigned Card Member Account Number", Tier.DETERMINISTIC),
    "4527": ReasonCode("4527", "Missing Imprint", Tier.DETERMINISTIC),
    "4530": ReasonCode("4530", "Currency Discrepancy", Tier.DETERMINISTIC),
    "4534": ReasonCode("4534", "Multiple ROCs", Tier.DETERMINISTIC),
    "4536": ReasonCode("4536", "Late Presentment", Tier.DETERMINISTIC),
    "4752": ReasonCode("4752", "Credit / Debit Presentment Error", Tier.DETERMINISTIC),
    "4755": ReasonCode("4755", "No Valid Authorisation", Tier.DETERMINISTIC),
    "4798": ReasonCode("4798", "Fraud Liability Shift \u2014 Counterfeit", Tier.DETERMINISTIC),

    # ---------------- Tier 2 — Fairness-Narrative Disputes (8 codes) ----------------
    "4513": ReasonCode(
        "4513", "Credit Not Presented", Tier.FAIRNESS_NARRATIVE,
        evidence_fields=("merchant_credit_log_match", "written_credit_acknowledgment", "merchant_credit_loss_rate"),
    ),
    "4540": ReasonCode(
        "4540", "Card Not Present", Tier.FAIRNESS_NARRATIVE,
        evidence_fields=("device_id_match", "ip_address_match", "shipping_address_match", "prior_undisputed_txn_count"),
    ),
    "4544": ReasonCode(
        "4544", "Cancellation Of Recurring Goods / Services", Tier.FAIRNESS_NARRATIVE,
        evidence_fields=("cancellation_request_timestamp", "merchant_cancellation_log_match", "charges_after_cancellation"),
    ),
    "4553": ReasonCode(
        "4553", "Not As Described Or Defective Merchandise", Tier.FAIRNESS_NARRATIVE,
        evidence_fields=("photo_evidence_provided", "listing_description_match", "merchant_counter_evidence"),
    ),
    "4554": ReasonCode(
        "4554", "Goods And Services Not Received", Tier.FAIRNESS_NARRATIVE,
        evidence_fields=("delivery_scan_present", "prior_undisputed_txn_count", "merchant_loss_rate_this_code"),
    ),
    "4750": ReasonCode(
        "4750", "Car Rental Charge Non Qualified or Unsubstantiated", Tier.FAIRNESS_NARRATIVE,
        evidence_fields=("signed_damages_acknowledgment", "charge_within_15pct_estimate"),
    ),
    "4754": ReasonCode(
        "4754", "Local Regulatory / Legal Dispute", Tier.FAIRNESS_NARRATIVE,
        evidence_fields=("statute_citation_provided",),
        always_human=True,
    ),
    "4763": ReasonCode(
        "4763", "Fraud Full Recourse", Tier.FAIRNESS_NARRATIVE,
        evidence_fields=("program_enrollment_at_charge_date", "device_id_match", "ip_address_match"),
    ),
}


def get_reason_code(code: str) -> ReasonCode:
    if code not in REASON_CODES:
        raise KeyError(f"Unknown reason code: {code!r}")
    return REASON_CODES[code]


def all_codes_by_tier(tier: Tier) -> list[ReasonCode]:
    return [rc for rc in REASON_CODES.values() if rc.tier == tier]
