"""Seed the database: taxonomy, resources, and a synthetic history for the demo user.

Run from the ``backend/`` directory:

    python -m app.seed                # deterministic demo history (rng seed 42)
    python -m app.seed --seed 7       # a different but still reproducible history
    python -m app.seed --attempts 300 # scale the number of attempts

Log in as  demo@studypath.app / demo-password  to see it. The generation logic
lives in ``app.services.seeding`` (shared with ``POST /api/topics/seed``); this
module is the CLI wrapper plus a readable summary.
"""

from __future__ import annotations

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.algorithm.decay import decayed_mastery
from app.algorithm.priority import rank_topics
from app.algorithm.readiness import readiness_by_section, weighted_readiness
from app.database import SessionLocal, engine
from app.enums import Section
from app.models import Base
from app.models.mastery import TopicMastery
from app.models.topic import Topic
from app.services.analytics import topic_snapshots
from app.services.seeding import seed_database, wipe_all
from app.services.users import DEMO_EMAIL, DEMO_PASSWORD, get_or_create_demo_user
from app.utils.time import utcnow


def print_summary(db: Session, user_id: int) -> None:
    now = utcnow()
    topics = list(
        db.scalars(
            select(Topic).order_by(
                Topic.section, Topic.domain, Topic.frequency_weight.desc(), Topic.skill_name
            )
        )
    )
    mastery_by_topic = {
        m.topic_id: m
        for m in db.scalars(select(TopicMastery).where(TopicMastery.user_id == user_id))
    }
    snapshots = topic_snapshots(db, user_id)
    by_section = readiness_by_section(snapshots, now)
    total_attempts = sum(m.attempts_count for m in mastery_by_topic.values())

    print(f"\n  {len(topics)} topics · {total_attempts} synthetic attempts\n")
    for section in (Section.MATH, Section.READING_WRITING):
        section_topics = [t for t in topics if t.section == section]
        print(f"  ══ {section.label} " + "═" * (70 - len(section.label)))
        current_domain = ""
        for topic in section_topics:
            if topic.domain != current_domain:
                current_domain = topic.domain
                print(f"  {current_domain}")
            m = mastery_by_topic.get(topic.id)
            if m is None:
                shown, last = "  --  ", "never"
            else:
                decayed = decayed_mastery(m.mastery_score, m.last_practiced, now)
                shown = f"{m.mastery_score * 100:3.0f}% → {decayed * 100:3.0f}%"
                last = f"{(now - m.last_practiced).days}d ago" if m.last_practiced else "never"
            count = m.attempts_count if m else 0
            print(f"    {topic.skill_name:<54}{count:>3} att{shown:>14}{last:>9}")

        print(f"    → readiness (frequency-weighted, decayed): {by_section[section] * 100:.0f}%\n")

    print(f"  Overall readiness: {weighted_readiness(snapshots, now) * 100:.0f}%\n")
    print("  ── Today's study plan (top 5) " + "─" * 43)
    for i, rec in enumerate(rank_topics(snapshots, now=now, limit=5), start=1):
        print(f"  {i}. {rec.skill_name}")
        print(f"     {rec.reason}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed SAT StudyPath with synthetic data.")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    parser.add_argument(
        "--attempts", type=int, default=None, help="approx. total attempts to generate"
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        wipe_all(db)
        demo = get_or_create_demo_user(db)
        db.commit()
        result = seed_database(
            db, user_id=demo.id, rng_seed=args.seed, target_attempts=args.attempts
        )
        print(f"Loaded taxonomy: {result.topics_created} topics.")
        print(f"Generated {result.attempts_created} attempts for {DEMO_EMAIL} (rng {args.seed}).")
        print(f"Log in with:  {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print_summary(db, demo.id)
    finally:
        db.close()


if __name__ == "__main__":
    main()
