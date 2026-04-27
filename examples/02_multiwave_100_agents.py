"""AILEX Pro Vanguard — Example 2: 100 Specialized Agents"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ailex_pilot.multiwave_performer import mwp_run, MultiWavePerformer

# List all 100 agents
mwp = MultiWavePerformer(verbose=False)
print(mwp.describe())

# Run with up to 20 agents
result = mwp_run("Design real-time collaborative editor with AI autocomplete", max_agents=20)
print(result.executive_summary())
print("\nTop performers:")
print(result.top_performers())
