"""Verify Robot 1.5 scored topics in database."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.database import SessionLocal
from src.models.seed_topic import SeedTopic

def verify_scored_topics():
    """Check scored topics and their LLM data."""
    db = SessionLocal()
    try:
        # Get all scored topics
        scored = db.query(SeedTopic).filter(
            SeedTopic.status == 'scored'
        ).all()

        print(f"Found {len(scored)} scored topics:\n")
        print("=" * 80)

        for topic in scored:
            print(f"\nTopic: {topic.topic[:60]}...")
            print(f"  Source: {topic.source.value}")
            print(f"  Niche: {topic.niche}")
            print(f"  Raw Score: {topic.raw_score}")
            print(f"  LLM Score: {topic.llm_score}/100")
            print(f"  Final Score: {topic.final_score}/100")
            print(f"  Status: {topic.status}")
            print(f"  LLM Provider: {topic.llm_provider}")
            print(f"  Scored At: {topic.scored_at}")
            if topic.profit_angle:
                print(f"  Profit Angle: {topic.profit_angle[:100]}...")
            if topic.llm_reasoning:
                print(f"  LLM Reasoning: {topic.llm_reasoning[:100]}...")
            print("-" * 80)

        # Summary
        print(f"\nSUMMARY:")
        print(f"  Total Scored: {len(scored)}")
        if scored:
            avg_llm = sum(t.llm_score for t in scored) / len(scored)
            avg_final = sum(t.final_score for t in scored) / len(scored)
            print(f"  Average LLM Score: {avg_llm:.1f}/100")
            print(f"  Average Final Score: {avg_final:.1f}/100")

    finally:
        db.close()

if __name__ == "__main__":
    verify_scored_topics()
