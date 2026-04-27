"""
AILEX — site_factory.py
Complete site generation factory for 8+ site types.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every site type comes with:
  - Complete design system (CSS variables)
  - Required sub-pages list
  - ContentGuard image kit mapping
  - MotionSystem preset
  - QA checklist overrides
  - Sitemap.xml + robots.txt
  - vercel.json routes

Site types:
  luxury_dating        — ROMA Prestige (done)
  institutional        — SIIC Court (done)
  luxury_restaurant    — fine dining
  dark_metal_band      — MANIPULATOR style
  corporate            — B2B company
  portfolio            — agency / freelancer
  e_commerce           — product shop
  healthcare           — clinic / medical
  nonprofit            — charity / foundation
  news_media           — news / magazine
  education            — university / school
  saas_product         — software product

Usage:
    from ailex_vision.site_factory import SiteFactory
    factory = SiteFactory()
    spec = factory.get_spec("dark_metal_band")
    # spec.pages, spec.images, spec.preset, spec.css_vars, ...
    site_html = factory.generate(spec, content_brief)
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Site Specification ────────────────────────────────────────────────────────

@dataclass
class PageSpec:
    slug:     str         # filename without .html
    title:    str         # page title
    required: bool = True # must exist for QA to pass
    description: str = ""


@dataclass
class SiteSpec:
    site_type:     str
    name:          str
    description:   str
    motion_preset: str          # UltraMotionSystem preset
    pages:         List[PageSpec]
    image_kit:     str          # ContentGuard.SITE_IMAGE_KITS key or custom
    css_vars:      Dict[str, str]
    fonts:         List[str]    # Google Fonts family names
    nav_items:     List[Dict[str, str]]   # [{label, href}]
    footer_cols:   List[Dict]
    qa_overrides:  Dict[str, Any] = field(default_factory=dict)
    extra_meta:    Dict[str, str] = field(default_factory=dict)


# ── Full Catalogue ─────────────────────────────────────────────────────────────

SITE_CATALOGUE: Dict[str, SiteSpec] = {

    # ── LUXURY DATING ─────────────────────────────────────────────────────────
    "luxury_dating": SiteSpec(
        site_type="luxury_dating",
        name="Luxury Dating Platform",
        description="Premium matchmaking and romantic connection service",
        motion_preset="luxury_dating",
        image_kit="dating_luxury_italian",
        pages=[
            PageSpec("index", "Homepage"),
            PageSpec("login", "Login"),
            PageSpec("onboarding", "Create Profile"),
            PageSpec("dashboard", "My Matches"),
            PageSpec("profile", "Profile Detail"),
            PageSpec("events", "Exclusive Events"),
            PageSpec("event-detail", "Event Detail & Booking"),
            PageSpec("about", "About Us"),
            PageSpec("privacy", "Privacy Policy"),
            PageSpec("404", "Not Found"),
        ],
        css_vars={
            "--bg":     "#060608",
            "--accent": "#B09028",
            "--text":   "#F2EAD8",
            "--panel":  "#161620",
            "--border": "rgba(176,144,40,.2)",
        },
        fonts=["Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,400",
               "Playfair+Display:ital,wght@0,400;0,700",
               "Montserrat:wght@300;400;500;600"],
        nav_items=[
            {"label":"I Cammini","href":"#cammini"},
            {"label":"Profili","href":"dashboard.html"},
            {"label":"Serate","href":"events.html"},
            {"label":"Chi Siamo","href":"about.html"},
            {"label":"Accedi","href":"login.html","class":"nav-acc"},
            {"label":"Iscriviti","href":"onboarding.html","class":"nav-cta"},
        ],
        footer_cols=[
            {"title":"Scopri","links":["I Cammini","Profili","Serate","Chi Siamo"]},
            {"title":"Account","links":["Accedi","Iscriviti","Dashboard"]},
            {"title":"Legale","links":["Privacy","Termini","Cookie"]},
        ],
    ),

    # ── INSTITUTIONAL / COURT ─────────────────────────────────────────────────
    "institutional": SiteSpec(
        site_type="institutional",
        name="International Institution",
        description="Sovereign authority, registry or international organization",
        motion_preset="institutional",
        image_kit="institutional_diplomatic",
        pages=[
            PageSpec("index", "Homepage"),
            PageSpec("services", "Services"),
            PageSpec("file", "Submit Document"),
            PageSpec("verify", "Verify Token"),
            PageSpec("portal", "My Portal"),
            PageSpec("register", "Create Account"),
            PageSpec("login", "Secure Login"),
            PageSpec("about", "About the Institution"),
            PageSpec("404", "Not Found"),
        ],
        css_vars={
            "--bg":     "#04060F",
            "--accent": "#C8A430",
            "--text":   "#EEF1FA",
            "--panel":  "#111830",
            "--border": "rgba(200,164,48,.22)",
        },
        fonts=["Cinzel:wght@400;600;700;900",
               "Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,400",
               "Montserrat:wght@300;400;500;600",
               "Courier+Prime:wght@400;700"],
        nav_items=[
            {"label":"Services","href":"services.html"},
            {"label":"Verify","href":"verify.html"},
            {"label":"File","href":"file.html"},
            {"label":"About","href":"about.html"},
            {"label":"Verify Token","href":"verify.html","class":"nav-v"},
            {"label":"Access Portal","href":"login.html","class":"nav-cta"},
        ],
        footer_cols=[
            {"title":"Services","links":["All Services","File Documents","Verify Tokens","API"]},
            {"title":"Institution","links":["About","Jurisdiction","Members","Report"]},
            {"title":"Legal","links":["Terms","Privacy","Cookie","Accessibility"]},
        ],
    ),

    # ── DARK METAL BAND ───────────────────────────────────────────────────────
    "dark_metal_band": SiteSpec(
        site_type="dark_metal_band",
        name="Metal Band Website",
        description="Official metal band website with music player, videos, store",
        motion_preset="cinematic",
        image_kit="dark_metal_band",
        pages=[
            PageSpec("index", "Homepage"),
            PageSpec("music", "Music Library"),
            PageSpec("videos", "Videos"),
            PageSpec("tour", "Tour Dates"),
            PageSpec("merch", "Merchandise"),
            PageSpec("about", "About the Band"),
            PageSpec("contact", "Contact"),
            PageSpec("404", "Not Found"),
        ],
        css_vars={
            "--bg":     "#000000",
            "--accent": "#cc0000",
            "--text":   "#f0f0f0",
            "--panel":  "#050508",
            "--border": "rgba(204,0,0,.25)",
        },
        fonts=["Orbitron:wght@400;700;900",
               "Inter:wght@300;400;500"],
        nav_items=[
            {"label":"MUSIC","href":"music.html"},
            {"label":"VIDEOS","href":"videos.html"},
            {"label":"TOUR","href":"tour.html"},
            {"label":"MERCH","href":"merch.html"},
            {"label":"ABOUT","href":"about.html"},
        ],
        footer_cols=[
            {"title":"MUSIC","links":["Albums","Singles","Videos","Bandcamp"]},
            {"title":"BAND","links":["About","Members","Press Kit"]},
            {"title":"CONNECT","links":["YouTube","Instagram","Spotify","Contact"]},
        ],
        extra_meta={"theme_color": "#cc0000"},
    ),

    # ── LUXURY RESTAURANT ─────────────────────────────────────────────────────
    "luxury_restaurant": SiteSpec(
        site_type="luxury_restaurant",
        name="Luxury Restaurant",
        description="Fine dining restaurant with reservations and menu",
        motion_preset="luxury_restaurant",
        image_kit="luxury_restaurant",
        pages=[
            PageSpec("index", "Homepage"),
            PageSpec("menu", "Our Menu"),
            PageSpec("reserve", "Make a Reservation"),
            PageSpec("chef", "Our Chef"),
            PageSpec("gallery", "Gallery"),
            PageSpec("about", "Our Story"),
            PageSpec("events", "Private Events"),
            PageSpec("contact", "Contact & Location"),
            PageSpec("404", "Not Found"),
        ],
        css_vars={
            "--bg":     "#060608",
            "--accent": "#C9A84C",
            "--text":   "#F5EEE4",
            "--panel":  "#0E0E12",
            "--border": "rgba(201,168,76,.2)",
        },
        fonts=["Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,400",
               "Montserrat:wght@300;400;500"],
        nav_items=[
            {"label":"Menu","href":"menu.html"},
            {"label":"Reserve","href":"reserve.html"},
            {"label":"Gallery","href":"gallery.html"},
            {"label":"Events","href":"events.html"},
            {"label":"Reserve a Table","href":"reserve.html","class":"nav-cta"},
        ],
        footer_cols=[
            {"title":"Discover","links":["Menu","Gallery","Chef","Awards"]},
            {"title":"Reserve","links":["Reservations","Private Events","Gift Cards"]},
            {"title":"Visit","links":["Location","Hours","Contact","Parking"]},
        ],
    ),

    # ── CORPORATE ─────────────────────────────────────────────────────────────
    "corporate": SiteSpec(
        site_type="corporate",
        name="Corporate Website",
        description="B2B company website with services, team, case studies",
        motion_preset="minimal",
        image_kit="corporate",
        pages=[
            PageSpec("index", "Homepage"),
            PageSpec("services", "Services"),
            PageSpec("about", "About Us"),
            PageSpec("team", "Our Team"),
            PageSpec("case-studies", "Case Studies"),
            PageSpec("blog", "Insights"),
            PageSpec("careers", "Careers"),
            PageSpec("contact", "Contact"),
            PageSpec("privacy", "Privacy Policy"),
            PageSpec("404", "Not Found"),
        ],
        css_vars={
            "--bg":     "#FFFFFF",
            "--accent": "#0066FF",
            "--text":   "#1A1A2E",
            "--panel":  "#F8F9FA",
            "--border": "rgba(0,102,255,.15)",
        },
        fonts=["Inter:wght@300;400;500;600;700",
               "Playfair+Display:wght@400;700"],
        nav_items=[
            {"label":"Services","href":"services.html"},
            {"label":"About","href":"about.html"},
            {"label":"Case Studies","href":"case-studies.html"},
            {"label":"Blog","href":"blog.html"},
            {"label":"Contact","href":"contact.html","class":"nav-cta"},
        ],
        footer_cols=[
            {"title":"Company","links":["About","Team","Careers","Press"]},
            {"title":"Services","links":["Consulting","Development","Strategy","Analytics"]},
            {"title":"Legal","links":["Privacy","Terms","Cookie","Accessibility"]},
        ],
    ),

    # ── PORTFOLIO / AGENCY ────────────────────────────────────────────────────
    "portfolio": SiteSpec(
        site_type="portfolio",
        name="Creative Portfolio",
        description="Designer or agency portfolio with work showcase",
        motion_preset="cinematic",
        image_kit="portfolio",
        pages=[
            PageSpec("index", "Homepage"),
            PageSpec("work", "Our Work"),
            PageSpec("project", "Project Detail"),
            PageSpec("about", "About"),
            PageSpec("services", "Services"),
            PageSpec("contact", "Contact"),
            PageSpec("404", "Not Found"),
        ],
        css_vars={
            "--bg":     "#0A0A0A",
            "--accent": "#FFFFFF",
            "--text":   "#EEEEEE",
            "--panel":  "#111111",
            "--border": "rgba(255,255,255,.1)",
        },
        fonts=["Space+Grotesk:wght@300;400;500;600;700",
               "Playfair+Display:ital,wght@0,400;1,400"],
        nav_items=[
            {"label":"Work","href":"work.html"},
            {"label":"Services","href":"services.html"},
            {"label":"About","href":"about.html"},
            {"label":"Let's Talk","href":"contact.html","class":"nav-cta"},
        ],
        footer_cols=[
            {"title":"Navigate","links":["Work","Services","About","Contact"]},
            {"title":"Social","links":["Instagram","LinkedIn","Dribbble","Behance"]},
        ],
    ),

    # ── E-COMMERCE ────────────────────────────────────────────────────────────
    "e_commerce": SiteSpec(
        site_type="e_commerce",
        name="E-Commerce Store",
        description="Online product store with cart and checkout",
        motion_preset="minimal",
        image_kit="e_commerce",
        pages=[
            PageSpec("index", "Homepage"),
            PageSpec("shop", "Shop"),
            PageSpec("product", "Product Detail"),
            PageSpec("cart", "Shopping Cart"),
            PageSpec("checkout", "Checkout"),
            PageSpec("account", "My Account"),
            PageSpec("orders", "My Orders"),
            PageSpec("about", "About"),
            PageSpec("shipping", "Shipping & Returns"),
            PageSpec("privacy", "Privacy Policy"),
            PageSpec("404", "Not Found"),
        ],
        css_vars={
            "--bg":     "#FFFFFF",
            "--accent": "#000000",
            "--text":   "#1A1A1A",
            "--panel":  "#F5F5F5",
            "--border": "rgba(0,0,0,.1)",
        },
        fonts=["Inter:wght@300;400;500;600",
               "Cormorant+Garamond:ital,wght@0,400;1,400"],
        nav_items=[
            {"label":"Shop","href":"shop.html"},
            {"label":"About","href":"about.html"},
            {"label":"Cart","href":"cart.html","class":"nav-cart"},
            {"label":"Account","href":"account.html","class":"nav-acc"},
        ],
        footer_cols=[
            {"title":"Shop","links":["All Products","New Arrivals","Sale","Bestsellers"]},
            {"title":"Help","links":["Shipping","Returns","Size Guide","FAQ"]},
            {"title":"Company","links":["About","Press","Sustainability","Careers"]},
        ],
    ),

    # ── HEALTHCARE ────────────────────────────────────────────────────────────
    "healthcare": SiteSpec(
        site_type="healthcare",
        name="Healthcare / Clinic",
        description="Medical clinic or healthcare provider website",
        motion_preset="minimal",
        image_kit="healthcare",
        pages=[
            PageSpec("index", "Homepage"),
            PageSpec("services", "Our Services"),
            PageSpec("doctors", "Our Team"),
            PageSpec("appointments", "Book Appointment"),
            PageSpec("patient-portal", "Patient Portal"),
            PageSpec("about", "About"),
            PageSpec("contact", "Contact"),
            PageSpec("privacy", "Privacy & HIPAA"),
            PageSpec("404", "Not Found"),
        ],
        css_vars={
            "--bg":     "#FFFFFF",
            "--accent": "#0057A8",
            "--text":   "#1C2B4A",
            "--panel":  "#F0F4F9",
            "--border": "rgba(0,87,168,.15)",
        },
        fonts=["Inter:wght@300;400;500;600",
               "Merriweather:wght@300;400;700"],
        nav_items=[
            {"label":"Services","href":"services.html"},
            {"label":"Doctors","href":"doctors.html"},
            {"label":"About","href":"about.html"},
            {"label":"Patient Portal","href":"patient-portal.html","class":"nav-acc"},
            {"label":"Book Appointment","href":"appointments.html","class":"nav-cta"},
        ],
        footer_cols=[
            {"title":"Services","links":["General Medicine","Specialists","Emergency","Diagnostics"]},
            {"title":"Patients","links":["Book Appointment","Patient Portal","Insurance","Forms"]},
            {"title":"Legal","links":["Privacy & HIPAA","Terms","Accessibility"]},
        ],
    ),

    # ── NONPROFIT ─────────────────────────────────────────────────────────────
    "nonprofit": SiteSpec(
        site_type="nonprofit",
        name="Nonprofit Organization",
        description="Charity, foundation or NGO website",
        motion_preset="institutional",
        image_kit="nonprofit",
        pages=[
            PageSpec("index", "Homepage"),
            PageSpec("about", "Our Mission"),
            PageSpec("programs", "Programs"),
            PageSpec("impact", "Our Impact"),
            PageSpec("donate", "Donate"),
            PageSpec("events", "Events"),
            PageSpec("blog", "Stories"),
            PageSpec("contact", "Contact"),
            PageSpec("privacy", "Privacy Policy"),
            PageSpec("404", "Not Found"),
        ],
        css_vars={
            "--bg":     "#FFFFFF",
            "--accent": "#2E7D32",
            "--text":   "#1B3A2D",
            "--panel":  "#F1F8E9",
            "--border": "rgba(46,125,50,.2)",
        },
        fonts=["Lora:ital,wght@0,400;0,600;1,400",
               "Inter:wght@300;400;500"],
        nav_items=[
            {"label":"About","href":"about.html"},
            {"label":"Programs","href":"programs.html"},
            {"label":"Impact","href":"impact.html"},
            {"label":"Events","href":"events.html"},
            {"label":"Donate","href":"donate.html","class":"nav-cta"},
        ],
        footer_cols=[
            {"title":"Organization","links":["Mission","Team","Financials","Press"]},
            {"title":"Get Involved","links":["Donate","Volunteer","Partner","Events"]},
            {"title":"Resources","links":["Programs","Stories","Contact","Privacy"]},
        ],
    ),

    # ── SAAS PRODUCT ──────────────────────────────────────────────────────────
    "saas_product": SiteSpec(
        site_type="saas_product",
        name="SaaS Product",
        description="Software as a service product landing page",
        motion_preset="minimal",
        image_kit="saas_product",
        pages=[
            PageSpec("index", "Homepage"),
            PageSpec("features", "Features"),
            PageSpec("pricing", "Pricing"),
            PageSpec("docs", "Documentation"),
            PageSpec("blog", "Blog"),
            PageSpec("about", "About"),
            PageSpec("login", "Sign In"),
            PageSpec("signup", "Start Free Trial"),
            PageSpec("privacy", "Privacy Policy"),
            PageSpec("terms", "Terms of Service"),
            PageSpec("404", "Not Found"),
        ],
        css_vars={
            "--bg":     "#0F172A",
            "--accent": "#6366F1",
            "--text":   "#E2E8F0",
            "--panel":  "#1E293B",
            "--border": "rgba(99,102,241,.25)",
        },
        fonts=["Inter:wght@300;400;500;600;700",
               "Space+Grotesk:wght@400;500;600"],
        nav_items=[
            {"label":"Features","href":"features.html"},
            {"label":"Pricing","href":"pricing.html"},
            {"label":"Docs","href":"docs.html"},
            {"label":"Blog","href":"blog.html"},
            {"label":"Sign In","href":"login.html","class":"nav-acc"},
            {"label":"Start Free","href":"signup.html","class":"nav-cta"},
        ],
        footer_cols=[
            {"title":"Product","links":["Features","Pricing","Changelog","Roadmap"]},
            {"title":"Developers","links":["Documentation","API","Status","SDKs"]},
            {"title":"Company","links":["About","Blog","Careers","Privacy"]},
        ],
    ),

    # ── API BACKEND DOCUMENTATION ─────────────────────────────────────────────
    "api_backend": SiteSpec(
        site_type="api_backend",
        name="API Documentation Portal",
        description="Developer portal for a REST or GraphQL API",
        motion_preset="minimal",
        image_kit="saas_product",
        pages=[
            PageSpec("index",      "Overview"),
            PageSpec("quickstart", "Quick Start"),
            PageSpec("auth",       "Authentication"),
            PageSpec("endpoints",  "API Reference"),
            PageSpec("errors",     "Error Codes"),
            PageSpec("sdks",       "SDKs & Libraries"),
            PageSpec("changelog",  "Changelog"),
            PageSpec("status",     "System Status"),
            PageSpec("about",      "About"),
            PageSpec("404",        "Not Found"),
        ],
        css_vars={
            "--bg":     "#0A0E1A",
            "--accent": "#3B82F6",
            "--text":   "#E2E8F0",
            "--panel":  "#141827",
            "--border": "rgba(59,130,246,.2)",
        },
        fonts=["Inter:wght@300;400;500;600;700",
               "JetBrains+Mono:wght@400;500"],
        nav_items=[
            {"label":"Quick Start","href":"quickstart.html"},
            {"label":"Auth","href":"auth.html"},
            {"label":"API Reference","href":"endpoints.html"},
            {"label":"SDKs","href":"sdks.html"},
            {"label":"Changelog","href":"changelog.html"},
            {"label":"Get API Key","href":"about.html","class":"nav-cta"},
        ],
        footer_cols=[
            {"title":"Docs","links":["Quick Start","Authentication","API Reference","Errors"]},
            {"title":"Resources","links":["SDKs","Changelog","Status","Support"]},
            {"title":"Company","links":["About","Blog","Terms","Privacy"]},
        ],
        extra_meta={"theme_color": "#3B82F6"},
    ),

    # ── FULLSTACK (Frontend + Backend docs) ───────────────────────────────────
    "fullstack": SiteSpec(
        site_type="fullstack",
        name="Full-Stack Application",
        description="Modern full-stack web application with frontend and API",
        motion_preset="minimal",
        image_kit="saas_product",
        pages=[
            PageSpec("index",     "Homepage"),
            PageSpec("features",  "Features"),
            PageSpec("pricing",   "Pricing"),
            PageSpec("api-docs",  "API Docs", required=False),
            PageSpec("about",     "About"),
            PageSpec("login",     "Sign In"),
            PageSpec("signup",    "Sign Up"),
            PageSpec("dashboard", "Dashboard"),
            PageSpec("settings",  "Settings"),
            PageSpec("privacy",   "Privacy Policy"),
            PageSpec("404",       "Not Found"),
        ],
        css_vars={
            "--bg":     "#FFFFFF",
            "--accent": "#6366F1",
            "--text":   "#1E293B",
            "--panel":  "#F8FAFC",
            "--border": "rgba(99,102,241,.15)",
        },
        fonts=["Inter:wght@300;400;500;600;700",
               "Space+Grotesk:wght@400;500;600"],
        nav_items=[
            {"label":"Features","href":"features.html"},
            {"label":"Pricing","href":"pricing.html"},
            {"label":"Docs","href":"api-docs.html"},
            {"label":"Sign In","href":"login.html","class":"nav-acc"},
            {"label":"Get Started","href":"signup.html","class":"nav-cta"},
        ],
        footer_cols=[
            {"title":"Product","links":["Features","Pricing","Changelog","Roadmap"]},
            {"title":"Developers","links":["API Docs","SDKs","Status","GitHub"]},
            {"title":"Company","links":["About","Blog","Careers","Privacy"]},
        ],
    ),
}


# ── Image kit extensions ───────────────────────────────────────────────────────
# Additional image kits for new site types (adds to content_guard.SITE_IMAGE_KITS)

EXTENDED_IMAGE_KITS: Dict[str, Dict[str, str]] = {
    "dark_metal_band": {
        "hero_bg":          "technology_professional",
        "band_photo":       "male_portrait_elegant",
        "venue":            "luxury_lifestyle",
        "album_art":        "technology_professional",
        "tour_bg":          "nature_landscape",
    },
    "corporate": {
        "hero_bg":          "diplomatic_institutional",
        "team_ceo":         "male_portrait_elegant",
        "team_coo":         "female_portrait_elegant",
        "office":           "technology_professional",
        "case_study_bg":    "luxury_lifestyle",
    },
    "portfolio": {
        "hero_bg":          "technology_professional",
        "work_1":           "luxury_lifestyle",
        "work_2":           "technology_professional",
        "about_photo":      "male_portrait_elegant",
    },
    "e_commerce": {
        "hero_bg":          "luxury_lifestyle",
        "product_1":        "luxury_lifestyle",
        "product_2":        "luxury_lifestyle",
        "lifestyle":        "luxury_lifestyle",
    },
    "healthcare": {
        "hero_bg":          "diplomatic_institutional",
        "doctor_1":         "male_portrait_elegant",
        "doctor_2":         "female_portrait_elegant",
        "facility":         "technology_professional",
    },
    "nonprofit": {
        "hero_bg":          "nature_landscape",
        "impact_1":         "nature_landscape",
        "team_1":           "female_portrait_elegant",
        "event_1":          "luxury_lifestyle",
    },
    "saas_product": {
        "hero_bg":          "technology_professional",
        "feature_1":        "technology_professional",
        "feature_2":        "technology_professional",
        "team":             "male_portrait_elegant",
    },
    "institutional_diplomatic": {
        "hero_bg":          "diplomatic_institutional",
        "about_photo":      "diplomatic_institutional",
        "team_1":           "male_portrait_elegant",
        "team_2":           "female_portrait_elegant",
    },
}


# ── Sitemap Generator ─────────────────────────────────────────────────────────

def generate_sitemap(base_url: str, pages: List[PageSpec], lastmod: str = "2026-04-26") -> str:
    """Generate sitemap.xml for a site."""
    urls = []
    priorities = {"index": "1.0", "services": "0.9", "about": "0.8",
                  "privacy": "0.3", "404": "0.1"}
    for p in pages:
        if p.slug == "404":
            continue
        filename = "index.html" if p.slug == "index" else f"{p.slug}.html"
        url = f"{base_url}/{'' if p.slug == 'index' else filename}"
        priority = priorities.get(p.slug, "0.7")
        urls.append(f"""  <url>
    <loc>{url}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>{priority}</priority>
  </url>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""


def generate_robots(base_url: str) -> str:
    """Generate robots.txt."""
    return f"""User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Sitemap: {base_url}/sitemap.xml
"""


def generate_vercel_json(pages: List[PageSpec], fallback_404: str = "404.html") -> str:
    """Generate vercel.json with clean routes."""
    import json
    rewrites = []
    for p in pages:
        if p.slug in ("index", "404"):
            continue
        rewrites.append({"source": f"/{p.slug}", "destination": f"/{p.slug}.html"})

    routes = [
        {"handle": "filesystem"},
        {"src": "/(.*)", "dest": f"/{fallback_404}", "status": 404},
    ]
    return json.dumps({"rewrites": rewrites, "routes": routes}, indent=2)


# ── Factory ───────────────────────────────────────────────────────────────────

class SiteFactory:
    """
    Complete site generation factory.
    Provides specs, assets, and generation helpers for all site types.

    Example:
        factory = SiteFactory()
        spec = factory.get_spec("luxury_dating")
        images = factory.get_images(spec)
        sitemap = factory.generate_sitemap("https://mysite.com", spec)
    """

    def get_spec(self, site_type: str) -> SiteSpec:
        """Get the complete specification for a site type."""
        spec = SITE_CATALOGUE.get(site_type)
        if not spec:
            available = list(SITE_CATALOGUE.keys())
            raise ValueError(
                f"Unknown site type: '{site_type}'. "
                f"Available: {available}"
            )
        return spec

    def list_types(self) -> List[str]:
        return list(SITE_CATALOGUE.keys())

    def get_images(self, spec: SiteSpec) -> Dict[str, str]:
        """Get verified images for this site type."""
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from content_guard import ContentGuard, SITE_IMAGE_KITS

            cg   = ContentGuard()
            kit_name = spec.image_kit

            # Check built-in kits first
            if kit_name in SITE_IMAGE_KITS:
                return cg.get_site_images(kit_name)

            # Use extended kit
            kit = EXTENDED_IMAGE_KITS.get(kit_name, {})
            if kit:
                return {
                    slot: cg.pick(cat)
                    for slot, cat in kit.items()
                }

            # Fallback: return mix of general images
            return {
                "hero_bg":   cg.pick("luxury_lifestyle"),
                "about":     cg.pick("diplomatic_institutional"),
                "feature_1": cg.pick("technology_professional"),
            }
        except Exception:
            return {}

    def generate_sitemap(self, base_url: str, spec: SiteSpec) -> str:
        return generate_sitemap(base_url, spec.pages)

    def generate_robots(self, base_url: str) -> str:
        return generate_robots(base_url)

    def generate_vercel_json(self, spec: SiteSpec) -> str:
        return generate_vercel_json(spec.pages)

    def get_required_pages(self, site_type: str) -> List[str]:
        """Return list of required page slugs for a site type."""
        spec = self.get_spec(site_type)
        return [p.slug for p in spec.pages if p.required]

    def validate_completeness(
        self,
        site_type: str,
        existing_pages: List[str],
    ) -> Dict[str, Any]:
        """
        Check if a generated site has all required pages.
        Returns: {complete, missing, extra, score}
        """
        spec     = self.get_spec(site_type)
        required = {p.slug for p in spec.pages if p.required}
        existing = set(existing_pages)
        missing  = required - existing
        return {
            "complete": len(missing) == 0,
            "missing":  sorted(missing),
            "present":  sorted(required & existing),
            "extra":    sorted(existing - required),
            "score":    round(100 * (1 - len(missing) / max(1, len(required))), 1),
        }

    def describe(self) -> str:
        lines = ["SiteFactory — Available Site Types", "─" * 50]
        for stype, spec in SITE_CATALOGUE.items():
            pages    = len(spec.pages)
            required = sum(1 for p in spec.pages if p.required)
            lines.append(
                f"  {stype:<22} {pages:>2} pages ({required} required)"
                f"  [{spec.motion_preset}]"
            )
        return "\n".join(lines)


# ── Singleton ─────────────────────────────────────────────────────────────────

_factory: Optional[SiteFactory] = None

def get_factory() -> SiteFactory:
    global _factory
    if _factory is None:
        _factory = SiteFactory()
    return _factory


if __name__ == "__main__":
    factory = SiteFactory()
    print(factory.describe())
    print()

    # Test completeness check
    spec = factory.get_spec("luxury_dating")
    result = factory.validate_completeness(
        "luxury_dating",
        ["index", "login", "onboarding", "dashboard"]  # missing some
    )
    print(f"Completeness: {result['score']}%")
    print(f"Missing: {result['missing']}")
    print()

    # Test sitemap
    sm = factory.generate_sitemap("https://example.com", spec)
    print(f"Sitemap: {sm[:200]}...")
    print()

    # Test vercel.json
    vcl = factory.generate_vercel_json(spec)
    print(f"vercel.json: {vcl[:200]}...")
