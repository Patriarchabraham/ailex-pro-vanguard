"""AILEX Pro Vanguard — Example 4: Backend Generation"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ailex_pilot.backend_generator import BackendGenerator

gen = BackendGenerator()
print(gen.describe())

# Generate FastAPI project (in memory — inspect without writing)
project = gen.generate("fastapi", "auth-service",
                        "JWT auth with refresh tokens and Redis blacklist")
print(f"\nGenerated {len(project.files)} files:")
for f in project.files[:8]:
    print(f"  {f.path}")
print("  ...")
print(f"\nCommands:")
for k, v in project.commands.items():
    print(f"  {k}: {v}")

# To write to disk:
# project.write_to("~/projects/auth-service")
