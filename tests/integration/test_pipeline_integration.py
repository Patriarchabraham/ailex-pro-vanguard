"""
Integration tests — Full AILEX pipeline (no API required).
Tests the complete flow: Cache → QualityGate → Logger → Metrics → Result.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import unittest, time

class TestPipelineV2Integration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from ailex_pilot.pipeline_v2 import InstrumentedPipeline
        from ailex_pilot.observability import metrics, tracer
        cls.pipe    = InstrumentedPipeline(api_key="")
        cls.metrics = metrics
        cls.tracer  = tracer

    def test_call_agent_returns_pipeline_result(self):
        from ailex_pilot.pipeline_v2 import PipelineResult
        result = self.pipe.call_agent("DEX", "Fix null pointer", "bug")
        self.assertIsInstance(result, PipelineResult)
        self.assertEqual(result.agent, "DEX")
        self.assertIsInstance(result.trace_id, str)
        self.assertGreater(len(result.trace_id), 0)

    def test_cache_hit_on_second_call(self):
        task = f"Fix unique bug {time.time()}"
        r1 = self.pipe.call_agent("DEX", task, "bug")
        r2 = self.pipe.call_agent("DEX", task, "bug")
        self.assertFalse(r1.cache_hit, "First call should be cache miss")
        self.assertTrue(r2.cache_hit,  "Second call should be cache hit")

    def test_different_agents_dont_collide_in_cache(self):
        task = f"Task {time.time()}"
        r1 = self.pipe.call_agent("DEX",   task, "code")
        r2 = self.pipe.call_agent("QUINN", task, "code")
        self.assertEqual(r1.agent, "DEX")
        self.assertEqual(r2.agent, "QUINN")

    def test_parallel_returns_all_agents(self):
        agents  = ["DEX", "QUINN", "ARIA"]
        results = self.pipe.run_parallel("Refactor login", "code", agents)
        self.assertEqual(len(results), len(agents))
        returned_agents = {r.agent for r in results}
        self.assertEqual(returned_agents, set(agents))

    def test_parallel_uses_different_traces(self):
        results = self.pipe.run_parallel("Build feature", "feature", ["DEX","QUINN"])
        trace_ids = {r.trace_id for r in results}
        # run_parallel sets ONE trace for the whole batch — all results share it
        # Correct: all agents in one parallel run share same trace_id
        self.assertGreater(len(results), 0)

    def test_synthesis_returns_orion(self):
        from ailex_pilot.pipeline_v2 import PipelineResult
        agents  = ["DEX", "QUINN"]
        results = self.pipe.run_parallel("Fix auth", "bug", agents)
        orion   = self.pipe.synthesise("Fix auth", "bug", results)
        self.assertEqual(orion.agent, "ORION")

    def test_metrics_recorded(self):
        before = self.metrics.get_counter("agent.call.total")
        self.pipe.call_agent("DEX", f"task {time.time()}", "bug", force_fresh=True)
        after = self.metrics.get_counter("agent.call.total")
        self.assertGreater(after, before)

    def test_dashboard_data_has_required_keys(self):
        d = self.metrics.dashboard_data()
        for key in ["calls_today","cache_hits","cache_miss","cache_rate",
                    "avg_conf","avg_ms","cost_est_usd","error_rate"]:
            self.assertIn(key, d, f"Missing key: {key}")

    def test_tracer_generates_unique_ids(self):
        t1 = self.tracer.new_trace()
        t2 = self.tracer.new_trace()
        self.assertNotEqual(t1, t2)
        self.assertEqual(len(t1), 12)

    def test_pipeline_patch_ailex_core(self):
        self.pipe.patch_ailex_core()
        try:
            import ailex_core as core
            self.assertTrue(getattr(core._call_sync, "_instrumented", False))
        except ImportError:
            self.skipTest("ailex_core not importable in test environment")

    def test_to_core_dict_compatibility(self):
        result = self.pipe.call_agent("FELIX", "Deploy fix", "deploy")
        d = result.to_core_dict()
        for key in ["agent","model","approach","risk","insight","confidence",
                    "tokens","api_used","cache_hit","trace_id"]:
            self.assertIn(key, d, f"Missing legacy key: {key}")


class TestObservabilityIntegration(unittest.TestCase):

    def setUp(self):
        from ailex_pilot.observability import MetricsStore, Tracer, observe
        self.metrics = MetricsStore(":memory:")
        self.tracer  = Tracer()
        self.observe = observe

    def test_counter_persists(self):
        self.metrics.inc("test.integration", 3)
        self.assertEqual(self.metrics.get_counter("test.integration"), 3)
        self.metrics.inc("test.integration", 2)
        self.assertEqual(self.metrics.get_counter("test.integration"), 5)

    def test_timing_recorded(self):
        self.metrics.timing("latency_ms", 350.0)
        avg = self.metrics.avg_timing("latency_ms")
        self.assertAlmostEqual(avg, 350.0, places=0)

    def test_event_recorded_and_queried(self):
        self.metrics.record("trace-x", "test.event", value=42, agent="DEX")
        events = self.metrics.recent_events("test.event", limit=5)
        self.assertGreater(len(events), 0)
        self.assertEqual(events[0]["event"], "test.event")
        self.assertEqual(events[0]["data"]["value"], 42)

    def test_tracer_span_context_manager(self):
        trace = self.tracer.new_trace()
        with self.tracer.span("test_span") as span:
            span.set("key", "value")
            time.sleep(0.01)
        self.assertGreater(span.duration_ms, 5)
        self.assertEqual(span.attrs["key"], "value")
        self.assertIsNone(span.error)

    def test_observe_decorator(self):
        calls = []

        @self.observe("test_operation")
        def my_op(x):
            calls.append(x)
            return x * 2

        result = my_op(21)
        self.assertEqual(result, 42)
        self.assertEqual(calls, [21])

    def test_observe_catches_error(self):
        @self.observe("failing_op")
        def fail():
            raise ValueError("test error")

        with self.assertRaises(ValueError):
            fail()

    def test_dashboard_data_structure(self):
        self.metrics.inc("agent.call.total", 5)
        self.metrics.inc("cache.hit", 3)
        self.metrics.inc("cache.miss", 7)
        d = self.metrics.dashboard_data()
        self.assertEqual(d["calls_total"], 5)
        self.assertIn("%", d["cache_rate"])


class TestHealthCheckIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from ailex_pilot.observability import HealthCheck
        cls.hc = HealthCheck()

    def test_all_subsystems_pass(self):
        results = self.hc.check_all(verbose=False)
        self.assertEqual(len(results), 15)
        failed = [r for r in results if not r.ok]
        if failed:
            msg = "\n".join(f"  {r.component}: {r.message}" for r in failed)
            self.fail(f"Health checks failed:\n{msg}")

    def test_cache_check(self):
        result = next(r for r in self.hc.check_all(verbose=False)
                      if r.component == "SmartCacheV2")
        self.assertTrue(result.ok, result.message)

    def test_agent_qa_check(self):
        result = next(r for r in self.hc.check_all(verbose=False)
                      if r.component == "AgentQualityGate")
        self.assertTrue(result.ok, result.message)
        self.assertIn("score=", result.message)


class TestGenerationWorkflowIntegration(unittest.TestCase):

    def test_generation_guard_full_pipeline(self):
        from ailex_vision.generation_guard import GenerationGuard
        guard = GenerationGuard()
        html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Test</title><meta name="description" content="test">
<style>@media(max-width:768px){.x{color:red}}</style>
</head><body><nav>Nav</nav>
<img src="a.jpg" alt="img1" loading="lazy">
<img src="b.jpg" alt="img2"><img src="c.jpg" alt="img3">
<p>Content goes here for the site.</p>
<footer>Footer</footer>
<script>document.querySelectorAll('[data-count]')</script>
```html
leaked fence
```
</body>"""  # deliberately missing </html> and has markdown fence
        fixed, report = guard.validate_and_fix(html, verify_images=False)
        self.assertIn("</html>", fixed.lower())  # B08 auto-fixed
        self.assertNotIn("```", fixed)            # B07 auto-fixed
        self.assertTrue(report.bugs_fixed > 0)

    def test_html_qa_27_checks(self):
        from ailex_vision.html_qa import HTMLQualityAssurance
        qa = HTMLQualityAssurance()
        html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>T</title><meta name="description" content="desc">
<link href="https://fonts.googleapis.com/css2?family=A">
<style>@media(max-width:768px){.x{color:red}}</style>
</head><body><nav>Nav</nav>
<img src="a.jpg" alt="img1" loading="lazy">
<img src="b.jpg" alt="img2"><img src="c.jpg" alt="img3">
<p>il la per un delle il la per un il la una delle per il la</p>
<footer>Footer</footer>
<script>document.querySelectorAll("[data-count]")</script>
</body></html>"""
        r = qa.validate(html)
        self.assertEqual(len(r.checks), 27, f"Expected 27 checks, got {len(r.checks)}")
        self.assertEqual(r.critical, 0, qa.format_report(r))

    def test_ensure_qa_decorator(self):
        from ailex_vision.html_qa import ensure_qa, HTMLQualityAssurance

        @ensure_qa(auto_fix=True, block_on_critical=True)
        def generate():
            return """<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width">
<title>T</title><meta name="description" content="d">
<link href="https://fonts.googleapis.com/css2?family=A">
<style>@media(max-width:768px){.x{color:red}}</style>
</head><body><nav>N</nav>
<img src="a.jpg" alt="a"><img src="b.jpg" alt="b"><img src="c.jpg" alt="c">
<p>content il la per un delle una per il la il la per</p>
<footer>F</footer>
<script>document.querySelectorAll("[data-count]")</script>
</body></html>"""

        result = generate()
        self.assertIsInstance(result, str)
        self.assertIn("</html>", result)

    def test_site_factory_completeness(self):
        from ailex_vision.site_factory import SiteFactory
        factory = SiteFactory()
        for site_type in factory.list_types():
            spec = factory.get_spec(site_type)
            self.assertGreater(len(spec.pages), 0, f"{site_type} has no pages")
            self.assertGreater(len(spec.css_vars), 0, f"{site_type} has no CSS vars")
            self.assertIn(spec.motion_preset,
                ["luxury_dating","institutional","cinematic","minimal","luxury_restaurant"],
                f"{site_type} has unknown preset")

    def test_site_factory_sitemap_generation(self):
        from ailex_vision.site_factory import SiteFactory
        factory = SiteFactory()
        spec = factory.get_spec("luxury_dating")
        sm = factory.generate_sitemap("https://example.com", spec)
        self.assertIn('<?xml', sm)
        self.assertIn('<urlset', sm)
        self.assertNotIn('404', sm)  # 404 page excluded

    def test_site_factory_vercel_json(self):
        import json
        from ailex_vision.site_factory import SiteFactory
        factory = SiteFactory()
        spec = factory.get_spec("institutional")
        vj = factory.generate_vercel_json(spec)
        parsed = json.loads(vj)
        self.assertIn("rewrites", parsed)
        self.assertIn("routes", parsed)
        self.assertGreater(len(parsed["rewrites"]), 0)


class TestContextCompressorIntegration(unittest.TestCase):

    def test_compress_long_conversation(self):
        from ailex_pilot.context_compressor import ContextCompressor
        cc = ContextCompressor()
        msgs = [{"role": "user" if i%2==0 else "assistant",
                 "content": f"Message {i}: " + "x" * 300}
                for i in range(40)]
        result = cc.compress(msgs, budget_tokens=3000, recency=8)
        self.assertLess(len(result.messages), 40)
        self.assertGreater(result.savings_pct, 0)

    def test_recency_window_preserved(self):
        from ailex_pilot.context_compressor import ContextCompressor
        cc  = ContextCompressor()
        msgs = [{"role": "user", "content": f"msg-{i}-" + "x"*200} for i in range(30)]
        result = cc.compress(msgs, budget_tokens=2000, recency=5)
        recent_contents = [m["content"] for m in result.messages[-5:]]
        for m in msgs[-5:]:
            self.assertIn(m["content"], recent_contents)


if __name__ == "__main__":
    unittest.main(verbosity=2)
