"""
AILEX Test Suite — run_all.py
Run all AILEX tests and report results.

Usage:
    python ~/.aiox-core/tests/run_all.py
    python ~/.aiox-core/tests/run_all.py --verbose
    python ~/.aiox-core/tests/run_all.py --only content_guard
"""
from __future__ import annotations

import argparse
import importlib
import os
import sys
import time
import unittest

# Add parent paths for imports
HERE   = os.path.dirname(os.path.abspath(__file__))
CORE   = os.path.dirname(HERE)
sys.path.insert(0, CORE)
sys.path.insert(0, os.path.join(HERE, "integration"))
sys.path.insert(0, os.path.join(HERE, "e2e"))

TEST_MODULES = [
    # Unit tests
    "test_structured_output",
    "test_agent_quality_gate",
    "test_smart_cache",
    "test_content_guard",
    "test_html_qa",
    "test_motion_system",
    "test_context_compressor",
    "test_multi_provider",
    # Integration tests
    "integration.test_pipeline_integration",
    # E2E tests
    "e2e.test_site_generation",
]


def run(verbose: bool = False, only: str = "") -> int:
    """Run test suite. Returns exit code (0=pass, 1=fail)."""
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    modules = [m for m in TEST_MODULES if not only or only in m]

    print(f"\n{'═'*60}")
    print(f"  AILEX Test Suite — {len(modules)} test module(s)")
    print(f"{'═'*60}\n")

    for mod_name in modules:
        try:
            mod  = importlib.import_module(mod_name)
            s    = loader.loadTestsFromModule(mod)
            suite.addTests(s)
        except ImportError as e:
            print(f"  ⚠️  Cannot import {mod_name}: {e}")

    t0      = time.perf_counter()
    runner  = unittest.TextTestRunner(
        verbosity=2 if verbose else 1,
        stream=sys.stdout,
        failfast=False,
    )
    result  = runner.run(suite)
    elapsed = time.perf_counter() - t0

    print(f"\n{'─'*60}")
    total  = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed
    # Use wasSuccessful() as the canonical pass/fail indicator
    success = result.wasSuccessful()
    icon    = "✅" if success else "❌"
    print(f"{icon}  {passed}/{total} tests passed in {elapsed:.2f}s")
    if result.failures:
        print(f"   Failures: {len(result.failures)}")
        for f in result.failures[:3]:
            print(f"   ✗ {str(f[0])[:60]}")
    if result.errors:
        print(f"   Errors:   {len(result.errors)}")
        for e in result.errors[:3]:
            print(f"   ✗ {str(e[0])[:60]}")
    print(f"{'─'*60}\n")

    return 0 if success else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="AILEX Test Suite")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--only", default="", help="Run only modules containing this string")
    args = ap.parse_args()
    sys.exit(run(verbose=args.verbose, only=args.only))
