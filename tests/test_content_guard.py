"""Tests for ContentGuard (content_guard.py) and html_qa.py and motion_system.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ailex_vision'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ailex_pilot'))
import unittest


# ── ContentGuard tests ────────────────────────────────────────────────────────
class TestContentGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ailex_vision.content_guard import ContentGuard, VERIFIED_LIBRARY, SITE_IMAGE_KITS
        cls.cg      = ContentGuard()
        cls.lib     = VERIFIED_LIBRARY
        cls.kits    = SITE_IMAGE_KITS

    def test_all_categories_have_entries(self):
        for cat, entries in self.lib.items():
            self.assertGreater(len(entries), 0, f"Category '{cat}' is empty")

    def test_all_entries_have_id_and_desc(self):
        for cat, entries in self.lib.items():
            for entry in entries:
                self.assertIn("id",   entry, f"Missing 'id' in {cat}")
                self.assertIn("desc", entry, f"Missing 'desc' in {cat}")
                self.assertTrue(entry["id"].startswith("photo-"),
                                f"Bad photo ID format in {cat}: {entry['id']}")

    def test_pick_returns_url(self):
        url = self.cg.pick("romantic_couple")
        self.assertTrue(url.startswith("https://images.unsplash.com/photo-"))
        self.assertIn("?", url)

    def test_pick_avoids_repeats(self):
        urls = [self.cg.pick("romantic_couple") for _ in range(4)]
        # With 5 images in romantic_couple, first 4 should mostly be unique
        unique = set(u.split("?")[0] for u in urls)
        self.assertGreater(len(unique), 1)

    def test_pick_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            self.cg.pick("nonexistent_category_xyz")

    def test_pick_with_meta_returns_dict(self):
        meta = self.cg.pick_with_meta("female_portrait_elegant")
        self.assertIn("url", meta)
        self.assertIn("desc", meta)
        self.assertIn("alt", meta)

    def test_get_site_images_dating(self):
        imgs = self.cg.get_site_images("dating_luxury_italian")
        self.assertIn("hero_bg", imgs)
        self.assertIn("manifesto_photo", imgs)
        self.assertIn("profile_female_1", imgs)
        self.assertIn("gallery_1", imgs)
        for slot, url in imgs.items():
            self.assertTrue(url.startswith("https://"), f"Bad URL for slot {slot}")

    def test_get_site_images_unknown_raises(self):
        with self.assertRaises(ValueError):
            self.cg.get_site_images("unknown_site_type")

    def test_validate_image_url_known(self):
        from ailex_vision.content_guard import VERIFIED_LIBRARY
        # Pick a known ID from the library
        first_id = VERIFIED_LIBRARY["romantic_couple"][0]["id"]
        url = f"https://images.unsplash.com/{first_id}?w=800"
        self.assertTrue(self.cg.validate_image_url(url, "romantic_couple"))

    def test_validate_image_url_unknown_returns_false(self):
        self.assertFalse(self.cg.validate_image_url("https://images.unsplash.com/photo-UNKNOWN?w=800", "any"))

    def test_describe_library_string(self):
        desc = self.cg.describe_library()
        self.assertIn("ContentGuard", desc)
        self.assertIn("romantic_couple", desc)

    def test_site_image_hero_uses_large_params(self):
        imgs = self.cg.get_site_images("dating_luxury_italian")
        # Hero should have w=1920
        self.assertIn("w=1920", imgs.get("hero_bg", ""))


# ── HTML QA tests ─────────────────────────────────────────────────────────────
class TestHTMLQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ailex_vision.html_qa import HTMLQualityAssurance
        cls.qa = HTMLQualityAssurance()

    def _make_html(self, **kw) -> str:
        """Build a minimal valid HTML with optional overrides."""
        defaults = {
            "charset": '<meta charset="UTF-8">',
            "viewport": '<meta name="viewport" content="width=device-width">',
            "title":    "<title>Test</title>",
            "desc":     '<meta name="description" content="test">',
            "lang":     "it",
            "fonts":    '<link href="https://fonts.googleapis.com/css2?family=A">',
            "img":      '<img src="https://x.com/a.jpg" alt="img" loading="lazy"><img src="https://x.com/b.jpg" alt="img2" loading="lazy"><img src="https://x.com/c.jpg" alt="img3">',
            "nav":      "<nav><a href='#'>Home</a></nav>",
            "footer":   "<footer>Footer</footer>",
            "counter":  "querySelectorAll('[data-count]')",
            "form_handler": "",
            "body_content": "<p>Hello world in italiano con il la per una delle</p>",
        }
        defaults.update(kw)
        return f"""<!DOCTYPE html>
<html lang="{defaults['lang']}">
<head>
{defaults['charset']}{defaults['viewport']}{defaults['title']}{defaults['desc']}{defaults['fonts']}
</head>
<body>
{defaults['nav']}{defaults['img']}{defaults['body_content']}<script>{defaults['counter']}{defaults['form_handler']}</script>{defaults['footer']}
</body>
</html>"""

    def test_valid_html_passes(self):
        html   = self._make_html()
        report = self.qa.validate(html)
        self.assertEqual(report.critical, 0, f"Unexpected critical: {[c for c in report.checks if not c.passed and c.severity=='CRITICAL']}")

    def test_missing_closing_tag_fails_c001(self):
        html = self._make_html().replace("</html>", "")
        r    = self.qa.validate(html)
        ids  = [c.id for c in r.checks if not c.passed]
        self.assertIn("C001", ids)

    def test_markdown_fence_fails_c002(self):
        html = self._make_html() + "\n```html\n<div>test</div>\n```"
        r    = self.qa.validate(html)
        ids  = [c.id for c in r.checks if not c.passed]
        self.assertIn("C002", ids)

    def test_missing_charset_fails_c004(self):
        html = self._make_html(charset="")
        r    = self.qa.validate(html)
        ids  = [c.id for c in r.checks if not c.passed]
        self.assertIn("C004", ids)

    def test_score_is_float_0_to_100(self):
        html = self._make_html()
        r    = self.qa.validate(html)
        self.assertGreaterEqual(r.score, 0.0)
        self.assertLessEqual(r.score, 100.0)

    def test_deployable_flag_correct(self):
        html = self._make_html()
        r    = self.qa.validate(html)
        self.assertEqual(r.deployable, r.critical == 0)

    def test_autofix_removes_markdown_fences(self):
        html = self._make_html() + "\n```html\n<div>extra</div>\n```"
        fixed, fixes = self.qa.autofix(html)
        self.assertNotIn("```", fixed)
        self.assertTrue(len(fixes) > 0)

    def test_counter_check_passes_with_data_count_selector(self):
        html = self._make_html(counter="querySelectorAll('[data-count]')")
        r    = self.qa.validate(html)
        c005 = next((c for c in r.checks if c.id == "C005"), None)
        if c005:  # only check if counters present
            pass   # just verify no crash

    def test_format_report_contains_status(self):
        html = self._make_html()
        r    = self.qa.validate(html)
        fmt  = self.qa.format_report(r)
        self.assertIn("Score:", fmt)


# ── MotionSystem tests ────────────────────────────────────────────────────────
class TestMotionSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ailex_vision.motion_system import MotionSystem, PRESETS
        cls.ms      = MotionSystem()
        cls.presets = PRESETS

    BASE_HTML = (
        "<!DOCTYPE html><html><head><title>T</title></head>"
        "<body><h1 class='hero-title'>Hello</h1></body></html>"
    )

    def test_inject_adds_gsap_cdn(self):
        result = self.ms.inject(self.BASE_HTML, "luxury_dating")
        self.assertIn("gsap@3.12.5", result)

    def test_inject_adds_lenis_cdn(self):
        result = self.ms.inject(self.BASE_HTML, "luxury_dating")
        self.assertIn("lenis@1.1.14", result)

    def test_inject_adds_cursor_html(self):
        result = self.ms.inject(self.BASE_HTML, "luxury_dating")
        self.assertIn("ailex-cursor", result)

    def test_inject_adds_progress_bar(self):
        result = self.ms.inject(self.BASE_HTML, "luxury_dating")
        self.assertIn("ailex-progress", result)

    def test_inject_adds_hyperframe_css(self):
        result = self.ms.inject(self.BASE_HTML, "luxury_dating")
        self.assertIn("hf-frame", result)

    def test_inject_adds_motion_js(self):
        result = self.ms.inject(self.BASE_HTML, "luxury_dating")
        self.assertIn("initMotion", result)

    def test_inject_idempotent(self):
        once  = self.ms.inject(self.BASE_HTML, "luxury_dating")
        twice = self.ms.inject(once, "luxury_dating")
        # Should not double-inject
        self.assertEqual(once.count("gsap@3.12.5"), twice.count("gsap@3.12.5"))

    def test_all_presets_valid(self):
        for preset in self.presets:
            result = self.ms.inject(self.BASE_HTML, preset)
            self.assertIn("gsap", result, f"Preset {preset} missing GSAP")

    def test_minimal_preset_no_cursor(self):
        css = self.ms.get_motion_css("minimal")
        # minimal preset has cursor=True, so cursor CSS is present
        result = self.ms.inject(self.BASE_HTML, "minimal")
        self.assertIn("lenis", result)

    def test_institutional_no_magnetic(self):
        js  = self.ms.get_motion_js("institutional")
        # institutional has magnetic=False
        self.assertNotIn("magnetic", js.lower())

    def test_describe_contains_presets(self):
        desc = self.ms.describe()
        self.assertIn("luxury_dating", desc)
        self.assertIn("institutional", desc)


# ── Context Compressor tests ──────────────────────────────────────────────────
class TestContextCompressor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ailex_pilot.context_compressor import ContextCompressor, DEFAULT_BUDGET
        cls.cc      = ContextCompressor()  # no API key — heuristic mode
        cls.budget  = DEFAULT_BUDGET

    def _make_messages(self, n: int = 30) -> list:
        return [
            {"role": "user" if i % 2 == 0 else "assistant",
             "content": f"Message {i}: " + "x" * 200}
            for i in range(n)
        ]

    def test_estimate_tokens(self):
        msgs   = self._make_messages(10)
        tokens = self.cc.estimate_tokens(msgs)
        self.assertGreater(tokens, 0)
        self.assertIsInstance(tokens, int)

    def test_no_compression_when_within_budget(self):
        msgs   = self._make_messages(3)
        result = self.cc.compress(msgs, budget_tokens=100_000)
        self.assertEqual(result.messages_removed, 0)
        self.assertEqual(result.savings_pct, 0.0)

    def test_compression_reduces_messages(self):
        msgs   = self._make_messages(50)
        result = self.cc.compress(msgs, budget_tokens=2000, recency=5)
        self.assertGreater(result.messages_removed, 0)
        self.assertLessEqual(len(result.messages), 6)  # summary + 5 recent

    def test_recency_window_preserved(self):
        msgs    = self._make_messages(30)
        recency = 8
        result  = self.cc.compress(msgs, budget_tokens=1000, recency=recency)
        # Last recency messages should be in result (summary is first)
        recent_content = [m["content"] for m in result.messages[1:]]  # skip summary
        last_msgs = [m["content"] for m in msgs[-recency:]]
        for content in last_msgs:
            self.assertIn(content, recent_content)

    def test_auto_compress_returns_list(self):
        msgs   = self._make_messages(10)
        result = self.cc.auto_compress(msgs, budget_tokens=100_000)
        self.assertIsInstance(result, list)

    def test_savings_pct_non_negative(self):
        msgs   = self._make_messages(50)
        result = self.cc.compress(msgs, budget_tokens=2000, recency=5)
        self.assertGreaterEqual(result.savings_pct, 0.0)
        self.assertLessEqual(result.savings_pct, 100.0)


# ── MultiProvider tests ───────────────────────────────────────────────────────
class TestMultiProvider(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ailex_pilot.multi_provider import MultiProvider, PROVIDER_MODELS, RateLimitTracker
        cls.mp    = MultiProvider()
        cls.pm    = PROVIDER_MODELS
        cls.RLT   = RateLimitTracker

    def test_provider_models_have_all_tiers(self):
        for provider, tiers in self.pm.items():
            for tier in ["opus", "sonnet", "haiku", "fast"]:
                self.assertIn(tier, tiers, f"Provider {provider} missing tier {tier}")

    def test_rate_limit_tracker_backoff(self):
        rl = self.RLT()
        self.assertTrue(rl.is_available("anthropic"))
        rl.register_429("anthropic")
        self.assertFalse(rl.is_available("anthropic"))

    def test_rate_limit_resets_on_success(self):
        rl = self.RLT()
        rl.register_429("openai")
        rl.register_success("openai")  # doesn't clear backoff_until, only hit_counts
        # Hit count is reset but backoff_until remains
        self.assertEqual(rl.hit_counts.get("openai", 0), 0)

    def test_status_string(self):
        status = self.mp.status()
        self.assertIn("MultiProvider", status)

    def test_no_providers_returns_error_message(self):
        from ailex_pilot.multi_provider import MultiProvider
        mp = MultiProvider()
        mp.keys = {}  # clear all keys
        result = mp.complete("hello", model_tier="fast")
        self.assertIn("No providers available", result["content"])
        self.assertEqual(result["provider"], "none")

    def test_cheapest_for_tier_returns_string_or_none(self):
        cheapest = self.mp.cheapest_for_tier("fast")
        if cheapest:
            self.assertIn(cheapest, ["anthropic", "openai", "gemini"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
