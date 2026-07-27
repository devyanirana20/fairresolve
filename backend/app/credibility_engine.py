"""
Layer 2 — Credibility Prior Engine.

Generalizes Visa's CE 3.0 historical-footprint logic (currently scoped to
one fraud reason code, merchant-side only) to both parties, across every
Tier 2 reason code. Produces a *prior* -- a confidence adjustment -- not a
verdict. It feeds into the Fair-Weighing Model (Layer 3), which combines it
with the reason-code-specific evidence.

Bidirectional by design:
  - Card member prior: does this account have a track record of undisputed
    transactions with this exact merchant (device/IP/shipping-address match)?
  - Merchant prior: does this merchant have a track record of accurate
    fulfillment (a low historical loss rate on disputes)?

New accounts on either side default to a neutral prior (0.5) rather than
being penalized for lacking history.
"""

NEUTRAL_PRIOR = 0.5


def card_member_credibility_prior(evidence: dict) -> float:
    """
    Returns a 0-1 score: higher means stronger track record with this merchant.
    Based on prior undisputed transactions and identity-signal matches --
    the same kind of signal CE 3.0 uses for merchants, applied here to the
    card member's side.
    """
    prior_txn_count = evidence["prior_undisputed_txn_count"]
    if prior_txn_count == 0:
        return NEUTRAL_PRIOR  # genuinely new relationship -- neutral, not penalized

    match_signals = sum([
        evidence["device_id_match"],
        evidence["ip_address_match"],
        evidence["shipping_address_match"],
    ])

    # More prior undisputed transactions + more matching identity signals
    # -> higher credibility, saturating so a handful of transactions doesn't
    # already max out the score.
    txn_component = min(prior_txn_count / 10.0, 1.0)
    match_component = match_signals / 3.0
    return round(0.5 * txn_component + 0.5 * match_component, 3)


def merchant_credibility_prior(evidence: dict) -> float:
    """
    Returns a 0-1 score: higher means a cleaner historical loss rate
    (fewer disputes lost against this merchant historically).
    """
    loss_rate = evidence["merchant_historical_loss_rate"]
    # Invert: a low loss rate -> high credibility.
    return round(max(0.0, min(1.0, 1.0 - (loss_rate / 0.5))), 3)


def compute_credibility_priors(evidence: dict) -> dict:
    return {
        "card_member_prior": card_member_credibility_prior(evidence),
        "merchant_prior": merchant_credibility_prior(evidence),
    }
