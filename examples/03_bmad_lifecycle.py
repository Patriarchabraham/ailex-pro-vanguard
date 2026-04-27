"""AILEX Pro Vanguard — Example 3: BMAD 4-Phase Lifecycle"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ailex_pilot.bmad_integration import bmad_run, bmad_stories

# Run all 4 phases
project = bmad_run(
    "Stripe Payment Gateway",
    "Stripe integration with webhooks, idempotency keys, PCI-DSS compliance, FastAPI"
)

print(project.summary())
print("\n--- PRD (Phase 2) ---")
print(project.prd[:500] if project.prd else "Run with API key for real content")

# Generate sprint stories from PRD
if project.prd:
    stories = bmad_stories(project.prd, "Payment Processing Epic", n=3)
    print("\n--- Sprint Stories ---")
    for s in stories:
        print(f"[{s.story_points}pts] {s.title}")
