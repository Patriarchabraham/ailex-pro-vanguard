"""AILEX Vision v6.0.0 — public API."""
from .visual_pipeline    import VisualPipeline, VisualReport
from .web_capture        import WebCapture, WebSnapshot
from .visual_analyzer    import VisualAnalyzer, VisualAnalysis
from .image_craft        import ImageCraft, GenerationResult
from .video_craft        import VideoCraft, VideoResult
from .claude_design      import ClaudeDesign, DesignOutput
from .browser            import BrowserCapture, BrowserSnapshot
from .design_system      import DesignSystemExtractor, DesignTokens, ComponentLibraryGenerator
from .design_to_code     import DesignToCode, DesignToCodeResult
from .diagram            import DiagramGenerator, DiagramResult
from .accessibility      import AccessibilityAuditor, AccessibilityReport
from .site_architect     import SiteArchitect, SiteSpec, PageSpec, GeneratedSite, GeneratedPage

__version__ = "6.0.0"
__all__ = [
    "VisualPipeline", "VisualReport",
    "WebCapture", "WebSnapshot",
    "VisualAnalyzer", "VisualAnalysis",
    "ImageCraft", "GenerationResult",
    "VideoCraft", "VideoResult",
    "ClaudeDesign", "DesignOutput",
    "BrowserCapture", "BrowserSnapshot",
    "DesignSystemExtractor", "DesignTokens", "ComponentLibraryGenerator",
    "DesignToCode", "DesignToCodeResult",
    "DiagramGenerator", "DiagramResult",
    "AccessibilityAuditor", "AccessibilityReport",
    "SiteArchitect", "SiteSpec", "PageSpec", "GeneratedSite", "GeneratedPage",
]

from .luxury_generator      import LuxuryGenerator, LuxuryDesignTokens, LuxuryResult, UNSPLASH_LIBRARY
from .html_qa               import HTMLQualityAssurance, QAReport, QACheck, qa_before_deploy, ensure_qa
from .content_guard         import ContentGuard, VERIFIED_LIBRARY, SITE_IMAGE_KITS
from .motion_system         import MotionSystem, PRESETS as MOTION_PRESETS
from .ultra_motion_system   import UltraMotionSystem, ultra_inject
from .image_generator       import ImageGenerator, GeneratedImage, CATEGORY_PROMPTS
from .generation_guard      import GenerationGuard, guard_html, enrich, get_guard, BUG_CATALOGUE
from .site_factory          import (SiteFactory, SiteSpec, PageSpec, SITE_CATALOGUE,
                                     generate_sitemap, generate_robots, generate_vercel_json,
                                     get_factory)
from .max_effects_system    import (MaxEffects, max_inject, get_max_effects,
                                     generate_package_json, CDNS as MAX_EFFECT_CDNS)

