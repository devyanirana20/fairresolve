"""
Layer 4 — Transparent Reasoning Layer.

Generates the single plain-language explanation shown to BOTH the card
member and the merchant -- identical wording, identical evidence cited.
This is the bilateral-transparency guarantee: there is no separate
"merchant version" of the reasoning that says something different.
"""

from app.reason_codes import get_reason_code, Tier

_TOP_FEATURE_PHRASES = {
    "delivery_scan_present": "the shipment's delivery scan record",
    "prior_undisputed_txn_count_norm": "this account's history of undisputed transactions with this merchant",
    "card_member_prior": "the card member's overall track record with this merchant",
    "merchant_prior": "this merchant's historical dispute-loss rate",
    "device_id_match": "whether this transaction's device ID matches prior undisputed purchases",
    "ip_address_match": "whether this transaction's IP address matches prior undisputed purchases",
    "shipping_address_match": "whether this transaction's shipping address matches prior undisputed purchases",
    "merchant_historical_loss_rate": "this merchant's historical loss rate on this claim type",
    "repeat_dispute_pattern": "this account's pattern of recent similar disputes despite confirmed prior deliveries",
    "photo_evidence_provided": "the photo evidence submitted by the card member",
    "merchant_counter_evidence": "the merchant's counter-evidence",
    "cancellation_before_charges": "the timing of the card member's cancellation request relative to later charges",
    "merchant_cancellation_log_match": "the merchant's own cancellation-processing log",
    "signed_damages_acknowledgment": "whether a signed capital-damages acknowledgment is on file",
    "charge_within_15pct_estimate": "whether the charge fell within 15% of the original damage estimate",
    "program_enrolled_at_charge_date": "the merchant's Fraud Full Recourse Program enrollment status at the charge date",
    "written_credit_acknowledgment": "the merchant's written acknowledgment of a promised credit",
    "merchant_credit_log_match": "whether the merchant's credit log shows a matching entry",
}


def _describe_top_drivers(feature_attributions: list[dict], max_items: int = 2) -> str:
    phrases = []
    for attr in feature_attributions:
        name = attr["feature"]
        if name in _TOP_FEATURE_PHRASES and not name.startswith("code_"):
            phrases.append(_TOP_FEATURE_PHRASES[name])
        if len(phrases) >= max_items:
            break
    if not phrases:
        return "the evidence gathered for this case"
    if len(phrases) == 1:
        return phrases[0]
    return " and ".join(phrases)


def generate_reasoning(reason_code: str, weighing_result: dict | None, evidence: dict) -> str:
    """
    Builds the single shared-explanation string. For Tier 1 (deterministic)
    codes, weighing_result is None -- reasoning is a direct record-match
    statement instead of a weighed explanation.
    """
    rc = get_reason_code(reason_code)

    if rc.tier == Tier.DETERMINISTIC:
        return (
            f"This is reason code {rc.code} ({rc.name}), which resolves by direct record "
            f"match rather than evidence weighing. The submitted transaction data was checked "
            f"directly against the network's authorization and settlement records."
        )

    if rc.always_human:
        return (
            f"Reason code {rc.code} ({rc.name}) involves a card member-asserted legal right "
            f"specific to their jurisdiction. This category never auto-resolves by design -- "
            f"legal interpretation is structurally out of automation scope, regardless of how "
            f"clear the underlying evidence looks. Routed directly to a human reviewer."
        )

    decision = weighing_result["decision"]
    confidence = weighing_result["confidence_score"]

    if decision == "auto_resolve_card_member":
        drivers = _describe_top_drivers(weighing_result["feature_attributions"], max_items=2)
        return (
            f"Based on {drivers}, this case resolves for the card member "
            f"with {confidence}% confidence. Both the card member and the merchant are shown "
            f"this same explanation."
        )
    elif decision == "auto_resolve_merchant":
        drivers = _describe_top_drivers(weighing_result["feature_attributions"], max_items=2)
        return (
            f"Based on {drivers}, this case resolves for the merchant "
            f"with {100 - confidence:.1f}% confidence in that outcome. Both the card member and "
            f"the merchant are shown this same explanation."
        )
    else:  # escalate_to_human
        # Escalations get one more driver than clean resolutions do -- an
        # ambiguous case needs fuller justification for *why* it's ambiguous,
        # and this is specifically where a signal like "repeat dispute
        # pattern" needs to make the cut even when it's not quite the single
        # top-magnitude driver.
        drivers = _describe_top_drivers(weighing_result["feature_attributions"], max_items=3)
        return (
            f"The evidence for this case is genuinely ambiguous ({confidence}% confidence, "
            f"in the escalation band) -- specifically around {drivers}. Rather than guess, this "
            f"case has been routed to a human reviewer with the full evidence trail attached."
        )
