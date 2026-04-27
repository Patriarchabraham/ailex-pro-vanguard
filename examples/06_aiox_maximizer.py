"""AILEX Pro Vanguard — Example 6: AIoX Maximizer"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ailex_pilot.aiox_maximizer import AIoXMaximizer, aiox_status

print(aiox_status())
print()

# Enhanced mode: + Security + Quality + RecursiveImprovement
mx = AIoXMaximizer(verbose=True, mode="enhanced")
result = mx.run("Implement JWT authentication with Redis session store", "backend")
print()
print(result.full_report())
