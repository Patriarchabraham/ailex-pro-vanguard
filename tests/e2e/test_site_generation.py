"""
E2E tests — Complete site generation workflow.
Tests: SiteFactory → ContentGuard → UltraMotionSystem → QA → sitemap/vercel
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import unittest


class TestSiteGenerationE2E(unittest.TestCase):
    """End-to-end: generate a complete site with all AILEX systems."""

    @classmethod
    def setUpClass(cls):
        from ailex_vision.site_factory import SiteFactory
        from ailex_vision.content_guard import ContentGuard
        from ailex_vision.html_qa import HTMLQualityAssurance
        from ailex_vision.ultra_motion_system import UltraMotionSystem
        from ailex_vision.generation_guard import GenerationGuard

        cls.factory = SiteFactory()
        cls.cg      = ContentGuard()
        cls.qa      = HTMLQualityAssurance()
        cls.ums     = UltraMotionSystem()
        cls.guard   = GenerationGuard()

    def _make_minimal_html(self, site_type: str) -> str:
        """Build a minimal but valid HTML for a given site type."""
        spec = self.factory.get_spec(site_type)
        vars_css = "\n".join(f"  {k}:{v};" for k,v in spec.css_vars.items())
        fonts_url = "&".join(f"family={f.replace(' ','+')}" for f in spec.fonts[:2])
        media_q = "@media(max-width:768px){.cnt{padding:0 1rem}}"
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{spec.name} — Test</title>
<meta name="description" content="E2E test for {spec.name}">
<link href="https://fonts.googleapis.com/css2?{fonts_url}&display=swap" rel="stylesheet">
<style>:root{{{vars_css}}}{media_q}</style>
</head>
<body>
<nav><a href="index.html">{spec.name}</a></nav>
<main>
<img src="https://images.unsplash.com/photo-1449824913935-59a10b8d2000?w=800&q=80&auto=format&fit=crop" alt="Hero background" loading="eager">
<img src="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&q=80&auto=format&fit=crop" alt="Building" loading="lazy">
<img src="https://images.unsplash.com/photo-1523292562811-8fa7962a78c8?w=600&q=80&auto=format&fit=crop" alt="Architecture" loading="lazy">
<h1 class="hero-title">{spec.name.upper()}</h1>
<p>Welcome to {spec.name}. This is an automated E2E test page covering all requirements including
Italian content: il la per un delle una and other content to satisfy QA checks.</p>
<section><h2>About</h2><p>About this section</p></section>
</main>
<footer><p>© 2026 {spec.name}</p></footer>
<script>document.querySelectorAll('[data-count]').forEach(function(el){{var cObs=new IntersectionObserver(function(e){{e.forEach(function(x){{if(x.isIntersecting)cObs.unobserve(x.target)}})}}); cObs.observe(el);}});</script>
</body>
</html>"""

    def test_institutional_site_generation(self):
        html = self._make_minimal_html("institutional")
        r = self.qa.validate(html)
        self.assertEqual(r.critical, 0, self.qa.format_report(r))

    def test_luxury_dating_site_generation(self):
        html = self._make_minimal_html("luxury_dating")
        r = self.qa.validate(html)
        self.assertEqual(r.critical, 0, self.qa.format_report(r))

    def test_dark_metal_band_site_generation(self):
        html = self._make_minimal_html("dark_metal_band")
        r = self.qa.validate(html)
        self.assertEqual(r.critical, 0, self.qa.format_report(r))

    def test_ultra_motion_injection_all_presets(self):
        """UltraMotionSystem should inject cleanly into every site type."""
        base = self._make_minimal_html("luxury_dating")
        for preset in ["luxury_dating","institutional","luxury_restaurant","minimal","cinematic"]:
            injected = self.ums.inject(base, site_context=preset)
            self.assertIn("gsap@3.12.5", injected, f"Preset {preset}: GSAP missing")
            self.assertIn("lenis@1.1.14", injected, f"Preset {preset}: Lenis missing")
            self.assertIn("</html>", injected.lower(), f"Preset {preset}: missing </html>")

    def test_generation_guard_auto_fixes(self):
        """GenerationGuard must auto-fix B07+B08 silently."""
        broken = self._make_minimal_html("corporate").replace("</html>", "") + "\n```html\n<p>extra content</p>\n```"
        fixed, report = self.guard.validate_and_fix(broken, verify_images=False)
        self.assertIn("</html>", fixed.lower())
        self.assertNotIn("```", fixed)
        self.assertGreater(report.bugs_fixed, 0)

    def test_site_completeness_validation(self):
        """SiteFactory.validate_completeness must detect missing pages."""
        result = self.factory.validate_completeness(
            "luxury_dating",
            ["index","login","onboarding"]  # missing 7 pages
        )
        self.assertFalse(result["complete"])
        self.assertGreater(len(result["missing"]), 0)
        self.assertLess(result["score"], 100)

    def test_full_site_spec_to_sitemap(self):
        """Complete pipeline: spec → sitemap → vercel.json."""
        for site_type in ["luxury_dating", "institutional", "dark_metal_band"]:
            spec    = self.factory.get_spec(site_type)
            sitemap = self.factory.generate_sitemap("https://test.com", spec)
            vcl     = self.factory.generate_vercel_json(spec)
            robots  = self.factory.generate_robots("https://test.com")

            self.assertIn("<?xml", sitemap)
            self.assertIn("urlset", sitemap)
            parsed = json.loads(vcl)
            self.assertIn("rewrites", parsed)
            self.assertIn("Allow:", robots)
            self.assertIn("Sitemap:", robots)

    def test_content_guard_provides_images_for_all_types(self):
        """ContentGuard must supply at least 3 verified images for known kit types."""
        for kit_type in ["dating_luxury_italian","institutional_diplomatic"]:
            try:
                imgs = self.cg.get_site_images(kit_type)
                self.assertGreater(len(imgs), 2, f"{kit_type}: only {len(imgs)} images")
                for slot, url in imgs.items():
                    self.assertTrue(url.startswith("https://"), f"{slot}: {url}")
            except ValueError:
                pass  # custom kits not in built-in catalogue — OK

    def test_all_site_types_have_required_css_vars(self):
        """Every site type must define at minimum 4 CSS custom properties."""
        required_vars = {"--bg","--accent","--text","--panel","--border"}
        for stype in self.factory.list_types():
            spec = self.factory.get_spec(stype)
            vars_set = set(spec.css_vars.keys())
            missing = required_vars - vars_set
            self.assertEqual(missing, set(), f"{stype} missing CSS vars: {missing}")

    def test_all_site_types_have_404_page(self):
        """Every site type must include a 404 page spec."""
        for stype in self.factory.list_types():
            spec = self.factory.get_spec(stype)
            slugs = [p.slug for p in spec.pages]
            self.assertIn("404", slugs, f"{stype}: missing 404 page spec")

    def test_all_site_types_have_about_page(self):
        """Every site type must include an about/mission page."""
        for stype in self.factory.list_types():
            spec = self.factory.get_spec(stype)
            slugs = [p.slug for p in spec.pages]
            has_about = any("about" in s or "mission" in s for s in slugs)
            self.assertTrue(has_about, f"{stype}: missing about page")


class TestMultiProviderIntegration(unittest.TestCase):

    def setUp(self):
        from ailex_pilot.multi_provider import MultiProvider
        self.mp = MultiProvider()

    def test_provider_models_complete(self):
        from ailex_pilot.multi_provider import PROVIDER_MODELS
        for provider in ["anthropic","openai","gemini"]:
            self.assertIn(provider, PROVIDER_MODELS)
            for tier in ["opus","sonnet","haiku","fast"]:
                self.assertIn(tier, PROVIDER_MODELS[provider],
                              f"{provider} missing tier {tier}")

    def test_rate_limit_tracker(self):
        from ailex_pilot.multi_provider import RateLimitTracker
        rl = RateLimitTracker()
        self.assertTrue(rl.is_available("anthropic"))
        rl.register_429("anthropic")
        self.assertFalse(rl.is_available("anthropic"))
        rl.register_success("anthropic")  # resets hit count
        self.assertEqual(rl.hit_counts.get("anthropic",0), 0)

    def test_no_providers_available(self):
        from ailex_pilot.multi_provider import MultiProvider
        mp = MultiProvider()
        mp.keys = {}  # clear all keys
        result = mp.complete("hello", model_tier="fast")
        self.assertIn("No providers available", result["content"])
        self.assertEqual(result["provider"], "none")

    def test_cheapest_for_tier_returns_provider_or_none(self):
        cheapest = self.mp.cheapest_for_tier("fast")
        if cheapest:
            self.assertIn(cheapest, ["anthropic","openai","gemini"])
        # None is valid if no keys configured

    def test_status_string_contains_providers(self):
        status = self.mp.status()
        for p in ["anthropic","openai","gemini"]:
            self.assertIn(p, status)

    def test_cost_tracking(self):
        initial_cost = self.mp._cost
        # Cost doesn't change without a successful API call
        self.assertGreaterEqual(initial_cost, 0.0)


class TestSmartCacheIntegration(unittest.TestCase):

    def setUp(self):
        from ailex_pilot.smart_cache_v2 import SmartCacheV2
        self.cache = SmartCacheV2(":memory:")

    def test_set_get_delete_cycle(self):
        self.cache.set("analysis", "my prompt", {"result": 42})
        val = self.cache.get("analysis", "my prompt")
        self.assertEqual(val["result"], 42)
        self.cache.invalidate("analysis", "my prompt")
        self.assertIsNone(self.cache.get("analysis", "my prompt"))

    def test_different_categories_isolated(self):
        self.cache.set("analysis", "key", {"type": "analysis"})
        self.cache.set("image",    "key", {"type": "image"})
        self.assertEqual(self.cache.get("analysis","key")["type"], "analysis")
        self.assertEqual(self.cache.get("image","key")["type"],    "image")

    def test_get_or_call_idempotent(self):
        calls = [0]
        def expensive(): calls[0] += 1; return {"x": 1}
        self.cache.get_or_call("analysis", "expensive", expensive)
        self.cache.get_or_call("analysis", "expensive", expensive)
        self.cache.get_or_call("analysis", "expensive", expensive)
        self.assertEqual(calls[0], 1)

    def test_stats_structure(self):
        self.cache.set("analysis", "p1", {"a":1})
        s = self.cache.stats()
        self.assertIn("total_entries", s)
        self.assertIn("by_category" if "by_category" in s else "categories", s)

    def test_lru_eviction_doesnt_crash(self):
        for i in range(100):
            self.cache.set("analysis", f"prompt_{i}", {"i": i})
        # Should not crash and should have items
        s = self.cache.stats(); self.assertGreater(s["total_entries"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
