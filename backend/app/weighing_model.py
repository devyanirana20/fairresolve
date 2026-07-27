"""
Layer 3 — Fair-Weighing Model.

A compact PyTorch scorer, reason-code-conditioned, with Captum providing
per-feature attribution for every decision -- the same "not a black box"
guarantee SHAP would give a tree-based model, kept consistent with the
PyTorch-backed NLP layer.

Only invoked for Tier 2 (fairness-narrative) codes -- Tier 1 codes resolve
via direct record match (see tier_router.py) and never reach this model.

Feature vector layout (see FEATURE_NAMES) combines:
  - the two Layer 2 credibility priors
  - evidence signals relevant across the 8 Tier 2 reason codes
  - a one-hot reason-code indicator, so the model can learn code-specific
    weighting rather than treating all Tier 2 disputes identically
"""

import os

import torch
import torch.nn as nn
from captum.attr import IntegratedGradients

from app.reason_codes import all_codes_by_tier, Tier

TIER2_CODES = [rc.code for rc in all_codes_by_tier(Tier.FAIRNESS_NARRATIVE) if not rc.always_human]
# -> ["4513", "4540", "4544", "4553", "4554", "4750", "4763"]  (4754 excluded: always_human)

EVIDENCE_FEATURE_NAMES = [
    "card_member_prior",
    "merchant_prior",
    "device_id_match",
    "ip_address_match",
    "shipping_address_match",
    "prior_undisputed_txn_count_norm",
    "delivery_scan_present",
    "merchant_historical_loss_rate",
    "repeat_dispute_pattern",
    "photo_evidence_provided",
    "merchant_counter_evidence",
    "cancellation_before_charges",
    "merchant_cancellation_log_match",
    "signed_damages_acknowledgment",
    "charge_within_15pct_estimate",
    "program_enrolled_at_charge_date",
    "written_credit_acknowledgment",
    "merchant_credit_log_match",
]
REASON_CODE_ONE_HOT_NAMES = [f"code_{c}" for c in TIER2_CODES]
FEATURE_NAMES = EVIDENCE_FEATURE_NAMES + REASON_CODE_ONE_HOT_NAMES
N_FEATURES = len(FEATURE_NAMES)

MODEL_WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "..", "weighing_model.pt")

# Confidence thresholds for the decision gate.
AUTO_RESOLVE_HIGH = 0.72   # P(favor card member) above this -> auto-resolve for card member
AUTO_RESOLVE_LOW = 0.28    # below this -> auto-resolve for merchant
# Between the two thresholds -> escalate to human review.


class FairWeighingModel(nn.Module):
    """Small feed-forward scorer. Deliberately compact: this is meant to be
    fast to train on a synthetic dataset for a hackathon/portfolio timeline,
    not a production-scale network."""

    def __init__(self, n_features: int = N_FEATURES):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 24),
            nn.ReLU(),
            nn.Linear(24, 12),
            nn.ReLU(),
            nn.Linear(12, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.net(x)


def build_feature_vector(evidence: dict, priors: dict, reason_code: str) -> list[float]:
    """
    Assemble the fixed-length feature vector for a Tier 2 dispute from the
    Evidence Collector's output (evidence), the Credibility Prior Engine's
    output (priors), and the reason code being disputed.
    """
    vec = {name: 0.0 for name in FEATURE_NAMES}

    vec["card_member_prior"] = priors["card_member_prior"]
    vec["merchant_prior"] = priors["merchant_prior"]
    vec["device_id_match"] = float(evidence.get("device_id_match", False))
    vec["ip_address_match"] = float(evidence.get("ip_address_match", False))
    vec["shipping_address_match"] = float(evidence.get("shipping_address_match", False))
    vec["prior_undisputed_txn_count_norm"] = min(evidence.get("prior_undisputed_txn_count", 0) / 10.0, 1.0)
    vec["delivery_scan_present"] = float(evidence["transaction"].get("delivery_scan_present", False))
    vec["merchant_historical_loss_rate"] = evidence.get("merchant_historical_loss_rate", 0.05)
    vec["repeat_dispute_pattern"] = float(evidence.get("repeat_dispute_pattern", False))

    # Reason-code-specific evidence fields (populated by the caller for the
    # relevant code; default to 0.0 / not applicable otherwise).
    for key in (
        "photo_evidence_provided", "merchant_counter_evidence",
        "cancellation_before_charges", "merchant_cancellation_log_match",
        "signed_damages_acknowledgment", "charge_within_15pct_estimate",
        "program_enrolled_at_charge_date",
        "written_credit_acknowledgment", "merchant_credit_log_match",
    ):
        if key in evidence:
            vec[key] = float(evidence[key])

    code_key = f"code_{reason_code}"
    if code_key in vec:
        vec[code_key] = 1.0

    return [vec[name] for name in FEATURE_NAMES]


_model_instance = None


def get_model() -> FairWeighingModel:
    global _model_instance
    if _model_instance is None:
        model = FairWeighingModel()
        if os.path.exists(MODEL_WEIGHTS_PATH):
            model.load_state_dict(torch.load(MODEL_WEIGHTS_PATH, map_location="cpu"))
        else:
            raise FileNotFoundError(
                f"No trained weights at {MODEL_WEIGHTS_PATH}. Run `python train_model.py` first."
            )
        model.eval()
        _model_instance = model
    return _model_instance


def score_dispute(evidence: dict, priors: dict, reason_code: str) -> dict:
    """
    Runs the Fair-Weighing Model on a Tier 2 dispute and returns the
    confidence score plus per-feature Captum attributions.
    """
    model = get_model()
    features = build_feature_vector(evidence, priors, reason_code)
    input_tensor = torch.tensor([features], dtype=torch.float32)

    with torch.no_grad():
        raw_score = model(input_tensor).item()

    ig = IntegratedGradients(model)
    baseline = torch.zeros_like(input_tensor)
    attributions, _ = ig.attribute(input_tensor, baseline, return_convergence_delta=True)
    attributions = attributions.squeeze(0).tolist()

    feature_attributions = sorted(
        [
            {"feature": name, "value": features[i], "attribution": round(attributions[i], 4)}
            for i, name in enumerate(FEATURE_NAMES)
            if features[i] != 0.0 or abs(attributions[i]) > 0.001
        ],
        key=lambda a: abs(a["attribution"]),
        reverse=True,
    )

    if raw_score >= AUTO_RESOLVE_HIGH:
        decision = "auto_resolve_card_member"
    elif raw_score <= AUTO_RESOLVE_LOW:
        decision = "auto_resolve_merchant"
    else:
        decision = "escalate_to_human"

    return {
        "confidence_score": round(raw_score * 100, 1),
        "decision": decision,
        "feature_attributions": feature_attributions[:6],  # top 6 drivers
    }
