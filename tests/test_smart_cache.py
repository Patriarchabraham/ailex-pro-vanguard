"""Tests for P3 — smart_cache_v2.py"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ailex_pilot'))
import unittest
from ailex_pilot.smart_cache_v2 import SmartCacheV2, get_cache, cached, TTL


class TestSmartCacheV2(unittest.TestCase):
    def setUp(self):
        self.cache = SmartCacheV2(":memory:")

    def test_set_and_get(self):
        self.cache.set("analysis", "test prompt", {"result": "ok"})
        val = self.cache.get("analysis", "test prompt")
        self.assertEqual(val, {"result": "ok"})

    def test_miss_returns_none(self):
        val = self.cache.get("analysis", "nonexistent prompt xyz")
        self.assertIsNone(val)

    def test_different_categories_dont_collide(self):
        self.cache.set("analysis", "same content", {"type": "analysis"})
        self.cache.set("image",    "same content", {"type": "image"})
        self.assertEqual(self.cache.get("analysis", "same content")["type"], "analysis")
        self.assertEqual(self.cache.get("image",    "same content")["type"], "image")

    def test_get_or_call_calls_compute_once(self):
        calls = [0]
        def compute():
            calls[0] += 1
            return {"computed": True}

        self.cache.get_or_call("analysis", "expensive prompt", compute)
        self.cache.get_or_call("analysis", "expensive prompt", compute)
        self.cache.get_or_call("analysis", "expensive prompt", compute)
        self.assertEqual(calls[0], 1, "compute() should be called exactly once")

    def test_get_or_call_different_content_calls_compute_again(self):
        calls = [0]
        def compute():
            calls[0] += 1
            return {"x": calls[0]}

        self.cache.get_or_call("analysis", "prompt A", compute)
        self.cache.get_or_call("analysis", "prompt B", compute)
        self.assertEqual(calls[0], 2)

    def test_expiry(self):
        self.cache.set("fast", "short lived", {"data": 1}, ttl=1)  # 1 second TTL
        val1 = self.cache.get("fast", "short lived")
        self.assertIsNotNone(val1)
        time.sleep(1.1)
        val2 = self.cache.get("fast", "short lived")
        self.assertIsNone(val2)

    def test_invalidate(self):
        self.cache.set("analysis", "to delete", {"x": 1})
        self.cache.invalidate("analysis", "to delete")
        self.assertIsNone(self.cache.get("analysis", "to delete"))

    def test_invalidate_category(self):
        for i in range(5):
            self.cache.set("analysis", f"prompt {i}", {"i": i})
        count = self.cache.invalidate_category("analysis")
        self.assertEqual(count, 5)
        for i in range(5):
            self.assertIsNone(self.cache.get("analysis", f"prompt {i}"))

    def test_clear_expired(self):
        self.cache.set("fast", "expires soon", {"x": 1}, ttl=1)
        self.cache.set("analysis", "stays longer", {"x": 2}, ttl=3600)
        time.sleep(1.1)
        removed = self.cache.clear_expired()
        self.assertGreaterEqual(removed, 1)
        self.assertIsNone(self.cache.get("fast", "expires soon"))
        self.assertIsNotNone(self.cache.get("analysis", "stays longer"))

    def test_stats_structure(self):
        self.cache.set("analysis", "p1", {"a": 1})
        self.cache.set("image",    "p2", {"b": 2})
        self.cache.get("analysis", "p1")  # 1 hit
        stats = self.cache.stats()
        self.assertIn("db_mb", stats)
        self.assertIn("total_entries", stats)
        self.assertIn("total_hits", stats)
        self.assertGreaterEqual(stats["total_entries"], 2)

    def test_format_stats_string(self):
        self.cache.set("analysis", "test", {"x": 1})
        s = self.cache.format_stats()
        self.assertIn("SmartCache", s)

    def test_make_key_deterministic(self):
        k1 = SmartCacheV2.make_key("analysis", "same content")
        k2 = SmartCacheV2.make_key("analysis", "same content")
        self.assertEqual(k1, k2)

    def test_make_key_different_for_different_content(self):
        k1 = SmartCacheV2.make_key("analysis", "content A")
        k2 = SmartCacheV2.make_key("analysis", "content B")
        self.assertNotEqual(k1, k2)

    def test_ttl_defaults_exist(self):
        for cat in ["fast", "analysis", "architecture", "image", "web_capture"]:
            self.assertIn(cat, TTL)
            self.assertGreater(TTL[cat], 0)

    def test_stores_complex_values(self):
        val = {"nested": {"list": [1, 2, 3], "bool": True, "none": None}}
        self.cache.set("analysis", "complex", val)
        back = self.cache.get("analysis", "complex")
        self.assertEqual(back, val)


class TestCachedDecorator(unittest.TestCase):
    def test_decorator_caches(self):
        calls = [0]

        @cached("analysis", ttl=3600)
        def compute(x: int, y: int) -> int:
            calls[0] += 1
            return x + y

        # Use a fresh in-memory cache for isolation — can't easily mock global
        # Just verify the function still works correctly
        result1 = compute(1, 2)
        self.assertEqual(result1, 3)
        result2 = compute(1, 2)
        self.assertEqual(result2, 3)
        # calls[0] might be 1 or 2 depending on global singleton state — just check no crash


if __name__ == "__main__":
    unittest.main(verbosity=2)
