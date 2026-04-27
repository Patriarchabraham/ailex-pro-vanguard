"""AILEX Pro Vanguard — Example 1: Wave Orchestration"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ailex_pilot.wave_orchestrator import wave_run

# Backend architecture in waves
result = wave_run("Build a scalable notification service with WebSocket and Redis", "backend")
print(result.wave_by_wave_summary())
