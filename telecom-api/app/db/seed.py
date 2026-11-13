"""Deterministic demo data, including deliberately MESSY records that the
normalisers (app/services/normalizers.py) clean on the way in:

* ported-out subscribers still marked 'active'        -> status reconciled to 'ported_out'
* the same complaint logged via app AND call centre    -> second one linked via duplicate_of_id
* data usage reported in MB by some systems, GB by others -> stored normalised to MB
"""
import logging
import random
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.db.models import (
    Circle,
    Complaint,
    Plan,
    PlanChange,
    Recharge,
    Subscriber,
    UsageRecord,
    User,
    utcnow,
)
from app.services.normalizers import find_duplicate, normalize_usage_to_mb, parse_usage_string, reconcile_status

logger = logging.getLogger("app.seed")

CIRCLES = [
    ("GJ", "Gujarat", "Gujarat"),
    ("MH", "Maharashtra", "Maharashtra"),
    ("DL", "Delhi NCR", "Delhi"),
    ("KA", "Karnataka", "Karnataka"),
    ("TN", "Tamil Nadu", "Tamil Nadu"),
    ("RJ", "Rajasthan", "Rajasthan"),
    ("UP", "Uttar Pradesh", "Uttar Pradesh"),
    ("WB", "West Bengal", "West Bengal"),
]

# name, price, GB/day, validity, 5G, OTT, circle code (None = national), active
PLANS = [
    ("Entry 149", 149, 1.0, 24, False, None, None, True),
    ("Saver 199", 199, 1.5, 28, False, None, None, True),
    ("Daily 299", 299, 2.0, 28, False, None, None, True),
    ("Plus 349", 349, 2.5, 28, False, "Music app", None, True),
    ("Max 5G 399", 399, 3.0, 28, True, "Video app", None, True),
    ("IPL Cricket Pack", 399, 3.0, 28, True, "Live cricket streaming", None, True),
    ("Quarterly 719", 719, 1.5, 84, False, None, None, True),
    ("Quarterly Plus 859", 859, 2.0, 84, False, "Music app", None, True),
    ("5G Quarterly 999", 999, 2.0, 84, True, "Video app", None, True),
    ("Annual 2399", 2399, 2.0, 365, False, None, None, True),
    ("Annual 5G 3599", 3599, 2.5, 365, True, "Video app + Music app", None, True),
    ("Gujarat Local 179", 179, 1.0, 28, False, None, "GJ", True),
    ("Legacy 99", 99, 0.5, 14, False, None, None, False),
]

FIRST = ["Aarav", "Vivaan", "Diya", "Anaya", "Rohan", "Kavya", "Isha", "Arjun", "Meera", "Nikhil", "Priya", "Karan",
         "Sneha", "Rahul", "Pooja", "Amit", "Neha", "Yash", "Tanvi", "Harsh"]
LAST = ["Patel", "Shah", "Mehta", "Desai", "Joshi", "Sharma", "Iyer", "Nair", "Reddy", "Singh", "Gupta", "Trivedi"]
COMPLAINTS = {
    "network": "Mobile data keeps dropping and calls disconnect in my area since two days.",
    "billing": "I was charged twice for my last recharge and the amount is not reflected.",
    "plan": "My plan benefits are not activated even though the recharge was successful.",
    "other": "I want to update my KYC details but the app shows an error on submit.",
}


def seed(session: Session, settings: Settings, rng_seed: int = 42) -> dict:
    if session.scalar(select(func.count(Circle.id))):
        return {}
    rng = random.Random(rng_seed)
    report = {"status_reconciled": 0, "duplicate_complaints_linked": 0, "usage_rows_normalised_from_gb": 0}
    now = utcnow()

    # --- reference data ---------------------------------------------------------------
    circles = {code: Circle(code=code, name=name, state=state) for code, name, state in CIRCLES}
    session.add_all(circles.values())
    session.flush()
    plans = []
    for name, price, gb, days, g5, ott, circle, active in PLANS:
        plans.append(
            Plan(
                name=name, price_inr=price, data_gb_per_day=gb, validity_days=days, is_5g=g5, ott_benefits=ott,
                circle_id=circles[circle].id if circle else None, active=active,
            )
        )
    session.add_all(plans)
    session.flush()
    active_national = [p for p in plans if p.active and p.circle_id is None]

    # --- subscribers (incl. messy ported-out-but-active rows) ----------------------------
    subscribers: list[Subscriber] = []
    used_numbers: set[str] = set()
    codes = ["GJ"] * 4 + [c[0] for c in CIRCLES]
    for i in range(60):
        while True:
            msisdn = str(rng.choice("6789")) + "".join(rng.choice("0123456789") for _ in range(9))
            if msisdn not in used_numbers:
                used_numbers.add(msisdn)
                break
        status, ported_at = "active", None
        if i >= 3:  # first three stay clean: they back the demo user logins
            if i % 10 == 0:
                status, ported_at = "active", date.today() - timedelta(days=rng.randint(5, 90))  # MESSY
            elif i % 17 == 0:
                status, ported_at = "ported_out", date.today() - timedelta(days=rng.randint(5, 90))
            elif i % 13 == 0:
                status = "suspended"
            elif i % 11 == 0:
                status = "inactive"
        corrected, changed = reconcile_status(status, ported_at)
        report["status_reconciled"] += int(changed)
        circle = circles[rng.choice(codes)]
        plan = rng.choice(active_national)
        subscribers.append(
            Subscriber(
                msisdn=msisdn,
                full_name=f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                email=f"user{i + 1}@example.com" if i % 3 else None,
                circle_id=circle.id,
                plan_id=plan.id,
                status=corrected,
                ported_out_at=ported_at,
                balance_inr=rng.randint(0, 500),
                plan_valid_until=now + timedelta(days=rng.randint(-10, plan.validity_days)),
                created_at=now - timedelta(days=rng.randint(30, 900)),
            )
        )
    session.add_all(subscribers)
    session.flush()

    # --- usage with mixed MB / GB units -------------------------------------------------
    for sub in subscribers[:40]:
        for d in range(5):
            if rng.random() < 0.5:
                raw = f"{round(rng.uniform(0.3, 3.0), 2)} GB"
            else:
                raw = f"{rng.randint(300, 3000)}MB"
            value, unit = parse_usage_string(raw)
            report["usage_rows_normalised_from_gb"] += int(unit == "GB")
            session.add(
                UsageRecord(
                    subscriber_id=sub.id,
                    recorded_on=date.today() - timedelta(days=d),
                    data_mb=normalize_usage_to_mb(value, unit),
                    raw_value=value,
                    raw_unit=unit,
                )
            )

    # --- complaints, with duplicates from both channels -----------------------------------
    created: list[Complaint] = []
    for i in range(25):
        sub = subscribers[i]
        category = rng.choice(list(COMPLAINTS))
        t0 = now - timedelta(days=rng.randint(1, 20), hours=rng.randint(0, 20))
        batch = [("app", t0)]
        if i % 3 == 0:  # same customer also phones the call centre a few hours later
            batch.append(("call_centre", t0 + timedelta(hours=rng.randint(1, 5))))
        for channel, when in batch:
            candidates = [c for c in created if c.subscriber_id == sub.id and c.category == category
                          and c.status in ("open", "in_progress") and c.duplicate_of_id is None]
            original = find_duplicate(candidates, when)
            c = Complaint(
                subscriber_id=sub.id, category=category, description=COMPLAINTS[category], channel=channel,
                status=rng.choice(["open", "open", "in_progress", "resolved"]) if not original else "open",
                created_at=when, updated_at=when,
            )
            session.add(c)
            session.flush()
            if original:
                c.duplicate_of_id = original.id
                report["duplicate_complaints_linked"] += 1
            created.append(c)

    # --- plan changes and recharges -------------------------------------------------------
    for sub in subscribers[:15]:
        new_plan = rng.choice([p for p in active_national if p.id != sub.plan_id])
        session.add(PlanChange(subscriber_id=sub.id, from_plan_id=sub.plan_id, to_plan_id=new_plan.id,
                               reason="Needs more data", created_at=now - timedelta(days=rng.randint(1, 60))))
    for sub in subscribers[:40]:
        for _ in range(2):
            plan = rng.choice(active_national)
            when = now - timedelta(days=rng.randint(1, 120))
            session.add(Recharge(subscriber_id=sub.id, plan_id=plan.id, amount_inr=plan.price_inr,
                                 payment_mode=rng.choice(["upi", "card", "netbanking", "wallet"]),
                                 status="success", created_at=when, valid_until=when + timedelta(days=plan.validity_days)))

    # --- users --------------------------------------------------------------------------------
    rounds = settings.bcrypt_rounds
    session.add(User(username="admin", password_hash=hash_password(settings.seed_admin_password, rounds), role="admin"))
    session.add(User(username="staff", password_hash=hash_password(settings.seed_staff_password, rounds), role="staff"))
    user_hash = hash_password(settings.seed_user_password, rounds)
    for n in range(1, 4):
        session.add(User(username=f"user{n}", password_hash=user_hash, role="user", subscriber_id=subscribers[n - 1].id))
    session.commit()
    logger.info("seeded demo data", extra={"report": report})
    return report
