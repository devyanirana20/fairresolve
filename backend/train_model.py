"""
Generates a synthetic training set for the Fair-Weighing Model and trains it.

Each reason code's synthetic-label rule mirrors the evidence logic documented
in the Reason Code Coverage appendix (e.g. for 4554, "no delivery scan favors
the card member"). This isn't real production data -- it's a stand-in so the
model learns genuinely sensible, explainable per-code patterns rather than
being trained on nothing. A documented, honest tradeoff (see README):
a neural scorer needs more data than a gradient-boosted alternative to reach
the same reliability on a small dataset -- this script exists specifically
to make that training data concrete and inspectable, not hidden.

Run directly:  python train_model.py
"""

import os
import random

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from app.weighing_model import (
    FairWeighingModel, FEATURE_NAMES, N_FEATURES, MODEL_WEIGHTS_PATH, REASON_CODE_ONE_HOT_NAMES
)

random.seed(42)
torch.manual_seed(42)

N_SAMPLES_PER_CODE = 600
LABEL_NOISE = 0.08  # fraction of labels randomly flipped, so the model
                     # doesn't learn a trivially perfect rule


def _vec(**overrides) -> dict:
    """
    Base feature vector with EVERY field populated with a plausible random
    background value first, then overridden by the caller's code-specific
    (label-correlated) values. This matters: a real dispute has all these
    signals present regardless of which reason code is being filed, even if
    only some of them actually drive that code's outcome. If irrelevant
    fields were left at a constant 0, the model would never see them vary
    for that code and would fall back on patterns learned from OTHER codes
    when a real (nonzero) value shows up at inference time -- exactly the
    bug this function exists to prevent.
    """
    base = {
        "card_member_prior": random.uniform(0.2, 0.9),
        "merchant_prior": random.uniform(0.2, 0.9),
        "device_id_match": float(random.random() < 0.5),
        "ip_address_match": float(random.random() < 0.5),
        "shipping_address_match": float(random.random() < 0.5),
        "prior_undisputed_txn_count_norm": random.uniform(0.0, 1.0),
        "delivery_scan_present": float(random.random() < 0.5),
        "merchant_historical_loss_rate": random.uniform(0.01, 0.3),
        "repeat_dispute_pattern": float(random.random() < 0.15),
        "photo_evidence_provided": float(random.random() < 0.5),
        "merchant_counter_evidence": float(random.random() < 0.5),
        "cancellation_before_charges": float(random.random() < 0.5),
        "merchant_cancellation_log_match": float(random.random() < 0.5),
        "signed_damages_acknowledgment": float(random.random() < 0.5),
        "charge_within_15pct_estimate": float(random.random() < 0.5),
        "program_enrolled_at_charge_date": float(random.random() < 0.5),
        "written_credit_acknowledgment": float(random.random() < 0.5),
        "merchant_credit_log_match": float(random.random() < 0.5),
    }
    for name in REASON_CODE_ONE_HOT_NAMES:
        base[name] = 0.0
    base.update(overrides)
    return base


def _maybe_flip(label: int) -> int:
    return 1 - label if random.random() < LABEL_NOISE else label


def gen_4513(n):
    """Credit Not Presented: card member wins if credit was promised in writing
    but the merchant's own log shows no matching credit applied."""
    rows = []
    for _ in range(n):
        acknowledgment = random.random() < 0.6
        log_match = random.random() < 0.5
        prior_txn = random.randint(0, 20)
        label = 1 if (acknowledgment and not log_match) else 0
        row = _vec(
            written_credit_acknowledgment=float(acknowledgment),
            merchant_credit_log_match=float(log_match),
            card_member_prior=min(prior_txn / 10, 1.0),
            merchant_prior=random.uniform(0.3, 0.9),
            prior_undisputed_txn_count_norm=min(prior_txn / 10, 1.0),
        )
        row["code_4513"] = 1.0
        rows.append((row, _maybe_flip(label)))
    return rows


def gen_4540(n):
    """Card Not Present: card member wins if device/IP/shipping DON'T match
    any prior undisputed transaction (genuine fraud signal); merchant wins
    if they do (looks like the same person -- CE 3.0 historical footprint)."""
    rows = []
    for _ in range(n):
        device_match = random.random() < 0.4
        ip_match = random.random() < 0.4
        ship_match = random.random() < 0.4
        match_count = sum([device_match, ip_match, ship_match])
        prior_txn = random.randint(0, 20)
        label = 0 if match_count >= 2 else 1
        row = _vec(
            device_id_match=float(device_match),
            ip_address_match=float(ip_match),
            shipping_address_match=float(ship_match),
            prior_undisputed_txn_count_norm=min(prior_txn / 10, 1.0),
            card_member_prior=min(prior_txn / 10, 1.0) * 0.5,
            merchant_prior=random.uniform(0.3, 0.9),
        )
        row["code_4540"] = 1.0
        rows.append((row, _maybe_flip(label)))
    return rows


def gen_4544(n):
    """Cancellation of Recurring: card member wins if their cancellation
    predates subsequent charges AND the merchant's own log confirms receipt."""
    rows = []
    for _ in range(n):
        before = random.random() < 0.55
        log_match = random.random() < 0.5
        label = 1 if (before and log_match) else 0
        row = _vec(
            cancellation_before_charges=float(before),
            merchant_cancellation_log_match=float(log_match),
            card_member_prior=random.uniform(0.3, 0.9),
            merchant_prior=random.uniform(0.3, 0.9),
        )
        row["code_4544"] = 1.0
        rows.append((row, _maybe_flip(label)))
    return rows


def gen_4553(n):
    """Not As Described / Defective: genuinely ambiguous -- extra label noise
    reflects that this is the kind of visual-judgment case that should often
    land in the escalation band rather than resolve cleanly."""
    rows = []
    for _ in range(n):
        photo = random.random() < 0.6
        counter = random.random() < 0.4
        label = 1 if (photo and not counter) else 0
        row = _vec(
            photo_evidence_provided=float(photo),
            merchant_counter_evidence=float(counter),
            card_member_prior=random.uniform(0.3, 0.8),
            merchant_prior=random.uniform(0.3, 0.8),
        )
        row["code_4553"] = 1.0
        # Extra noise for this code specifically -- ambiguity is the point.
        flipped = label if random.random() > 0.30 else 1 - label
        rows.append((row, flipped))
    return rows


def gen_4554(n):
    """Goods and Services Not Received: card member wins if there's no
    delivery scan on record; strengthened by a clean prior relationship.
    EXCEPTION: when this card member shows a repeat-dispute pattern (several
    similar disputes in 90 days, all with confirmed delivery), the true
    outcome is genuinely uncertain regardless of this transaction's own
    delivery status -- that's deliberately taught as ~50/50 noise here, so
    the model learns to land in the escalation band rather than confidently
    guess either way. This is what makes the confidence gate flag suspicious
    patterns for human review instead of quietly ruling on them."""
    rows = []
    for _ in range(n):
        delivered = random.random() < 0.45
        prior_txn = random.randint(0, 25)
        loss_rate = random.uniform(0.01, 0.2)
        repeat_pattern = random.random() < 0.15

        if repeat_pattern:
            label = 1 if random.random() < 0.5 else 0  # genuinely ambiguous
        else:
            label = 0 if delivered else 1

        row = _vec(
            delivery_scan_present=float(delivered),
            prior_undisputed_txn_count_norm=min(prior_txn / 10, 1.0),
            card_member_prior=min(0.5 + prior_txn / 30, 1.0),
            merchant_prior=1.0 - loss_rate * 2,
            merchant_historical_loss_rate=loss_rate,
            repeat_dispute_pattern=float(repeat_pattern),
        )
        row["code_4554"] = 1.0
        rows.append((row, _maybe_flip(label) if not repeat_pattern else label))
    return rows


def gen_4750(n):
    """Car Rental Non-Qualified: card member wins if the merchant has no
    signed capital-damages acknowledgment, or the charge exceeds the
    estimate by more than the allowed 15%."""
    rows = []
    for _ in range(n):
        signed = random.random() < 0.5
        within_estimate = random.random() < 0.6
        label = 0 if (signed and within_estimate) else 1
        row = _vec(
            signed_damages_acknowledgment=float(signed),
            charge_within_15pct_estimate=float(within_estimate),
            card_member_prior=random.uniform(0.3, 0.9),
            merchant_prior=random.uniform(0.3, 0.9),
        )
        row["code_4750"] = 1.0
        rows.append((row, _maybe_flip(label)))
    return rows


def gen_4763(n):
    """Fraud Full Recourse: card member wins only if the merchant WAS
    enrolled in the program at the charge date AND the transaction shows
    no identity-match signal (genuine fraud); otherwise the reason code
    doesn't apply and the merchant wins."""
    rows = []
    for _ in range(n):
        enrolled = random.random() < 0.5
        device_match = random.random() < 0.4
        ip_match = random.random() < 0.4
        label = 1 if (enrolled and not device_match and not ip_match) else 0
        row = _vec(
            program_enrolled_at_charge_date=float(enrolled),
            device_id_match=float(device_match),
            ip_address_match=float(ip_match),
            card_member_prior=random.uniform(0.3, 0.9),
            merchant_prior=random.uniform(0.3, 0.9),
        )
        row["code_4763"] = 1.0
        rows.append((row, _maybe_flip(label)))
    return rows


GENERATORS = [gen_4513, gen_4540, gen_4544, gen_4553, gen_4554, gen_4750, gen_4763]


def build_dataset():
    all_rows = []
    for gen in GENERATORS:
        all_rows.extend(gen(N_SAMPLES_PER_CODE))
    random.shuffle(all_rows)

    X = torch.tensor([[row[name] for name in FEATURE_NAMES] for row, _ in all_rows], dtype=torch.float32)
    y = torch.tensor([[label] for _, label in all_rows], dtype=torch.float32)
    return X, y


def train():
    X, y = build_dataset()
    n_val = int(len(X) * 0.15)
    X_train, y_train = X[n_val:], y[n_val:]
    X_val, y_val = X[:n_val], y[:n_val]

    model = FairWeighingModel()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.BCELoss()

    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=32, shuffle=True)

    for epoch in range(40):
        model.train()
        total_loss = 0.0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            pred = model(xb)
            loss = loss_fn(pred, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * xb.size(0)

        if epoch % 10 == 0 or epoch == 39:
            model.eval()
            with torch.no_grad():
                val_pred = model(X_val)
                val_acc = ((val_pred > 0.5).float() == y_val).float().mean().item()
            print(f"epoch {epoch:2d}  train_loss={total_loss/len(X_train):.4f}  val_acc={val_acc:.3f}")

    torch.save(model.state_dict(), MODEL_WEIGHTS_PATH)
    print(f"\nSaved trained weights to {MODEL_WEIGHTS_PATH}")


if __name__ == "__main__":
    train()
