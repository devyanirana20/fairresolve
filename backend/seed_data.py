"""
Seeds the database with sample card members, merchants, transaction history,
and the Case A / Case B disputes -- the same worked examples used throughout
the FairResolve proposal and prototype, now backed by real data and a real
model run instead of hardcoded UI state.

Run:  python seed_data.py
"""

import datetime

from app.database import SessionLocal, init_db
from app.models import CardMember, Merchant, Transaction
from app.tier_router import file_dispute


def seed():
    init_db()
    db = SessionLocal()

    # Clear existing data for a clean re-seed.
    from app.models import Dispute, EvidenceItem
    db.query(EvidenceItem).delete()
    db.query(Dispute).delete()
    db.query(Transaction).delete()
    db.query(Merchant).delete()
    db.query(CardMember).delete()
    db.commit()

    alex = CardMember(name="Alex Whitfield", email="alex.whitfield@example.com")
    jamie = CardMember(name="Jamie Torres", email="jamie.torres@example.com")
    db.add_all([alex, jamie])
    db.commit()

    nova = Merchant(name="Nova Home Goods", historical_loss_rate=0.06)
    skyline = Merchant(name="Skyline Electronics", historical_loss_rate=0.04)
    db.add_all([nova, skyline])
    db.commit()

    now = datetime.datetime.utcnow()

    # --- Alex's clean 2-year history with Nova Home Goods (14 prior undisputed txns) ---
    for i in range(14):
        db.add(Transaction(
            card_member_id=alex.id, merchant_id=nova.id,
            amount=round(40 + i * 7.5, 2), currency="USD",
            created_at=now - datetime.timedelta(days=730 - i * 45),
            device_id="device-alex-01", ip_address="203.0.113.10",
            shipping_address="14 Birchwood Ave, Springfield",
            delivery_scan_present=True, was_disputed=False,
        ))
    db.commit()

    # Case A's disputed transaction: no delivery scan.
    case_a_txn = Transaction(
        card_member_id=alex.id, merchant_id=nova.id,
        amount=340.00, currency="USD",
        created_at=now - datetime.timedelta(days=9),
        device_id="device-alex-01", ip_address="203.0.113.10",
        shipping_address="14 Birchwood Ave, Springfield",
        delivery_scan_present=False, was_disputed=True,
    )
    db.add(case_a_txn)
    db.commit()

    # --- Jamie's pattern with Skyline: 4 similar disputes in 90 days, all delivered ---
    for i in range(4):
        db.add(Transaction(
            card_member_id=jamie.id, merchant_id=skyline.id,
            amount=round(150 + i * 20, 2), currency="USD",
            created_at=now - datetime.timedelta(days=90 - i * 20),
            device_id="device-jamie-01", ip_address="198.51.100.7",
            shipping_address="88 Windmere Court, Rivertown",
            delivery_scan_present=True, was_disputed=(i < 3),  # 3 prior disputes, all delivered
        ))
    db.commit()

    case_b_txn = Transaction(
        card_member_id=jamie.id, merchant_id=skyline.id,
        amount=212.50, currency="USD",
        created_at=now - datetime.timedelta(days=2),
        device_id="device-jamie-01", ip_address="198.51.100.7",
        shipping_address="88 Windmere Court, Rivertown",
        delivery_scan_present=True, was_disputed=True,
    )
    db.add(case_b_txn)
    db.commit()

    # --- File Case A and Case B through the real pipeline ---
    case_a = file_dispute(
        db, case_a_txn, "4554",
        "I never received this order. The tracking still says label created from 9 days ago.",
    )
    case_b = file_dispute(
        db, case_b_txn, "4554",
        "This package never arrived either, same as my last few orders from this merchant.",
    )

    db.commit()

    print(f"Seeded 2 card members, 2 merchants, {14+1+4+1} transactions.")
    print(f"Case A dispute id={case_a.id}  status={case_a.status}  confidence={case_a.confidence_score}")
    print(f"Case B dispute id={case_b.id}  status={case_b.status}  confidence={case_b.confidence_score}")
    print(f"\nCase A transaction_id (for filing new test disputes): {case_a_txn.id}")

    db.close()


if __name__ == "__main__":
    seed()
