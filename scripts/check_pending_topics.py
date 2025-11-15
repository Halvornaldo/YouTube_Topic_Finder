"""Check how many pending topics we have for Robot 1.5 to score."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.database import SessionLocal
from src.models.seed_topic import SeedTopic

def check_pending_topics():
    """Check pending topics in database."""
    db = SessionLocal()
    try:
        # Count all topics
        total = db.query(SeedTopic).count()
        print(f"Total topics in database: {total}")

        # Count by status
        pending = db.query(SeedTopic).filter(SeedTopic.status == 'pending').count()
        scored = db.query(SeedTopic).filter(SeedTopic.status == 'scored').count()
        rejected = db.query(SeedTopic).filter(SeedTopic.status == 'rejected').count()

        print(f"  - Pending (ready for Robot 1.5): {pending}")
        print(f"  - Scored (passed Robot 1.5): {scored}")
        print(f"  - Rejected (filtered by Robot 1.5): {rejected}")

        # Show sample pending topics
        if pending > 0:
            print("\nSample pending topics:")
            samples = db.query(SeedTopic).filter(
                SeedTopic.status == 'pending'
            ).limit(5).all()

            for topic in samples:
                print(f"  - {topic.topic[:60]}... (niche: {topic.niche}, source: {topic.source.value})")

        return pending

    finally:
        db.close()

if __name__ == "__main__":
    pending_count = check_pending_topics()
    if pending_count == 0:
        print("\n[ACTION NEEDED] No pending topics found. Run Robot 1 first to discover topics.")
        sys.exit(1)
    else:
        print(f"\n[READY] {pending_count} pending topics ready for Robot 1.5 scoring!")
        sys.exit(0)
