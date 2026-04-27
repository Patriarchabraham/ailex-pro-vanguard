"""
AILEX — max_effects_system.py
ALL visual libraries permanently integrated in every project.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERMANENT STANDARD: Every AILEX-generated site includes ALL of these.

Libraries (all CDN, all MIT/free):
  ✦ Tailwind CSS 3      — utility classes + luxury custom config
  ✦ Three.js r169       — WebGL 3D (already in UltraMotion)
  ✦ GSAP 3.12.5         — animation (already in UltraMotion)
  ✦ Lenis 1.1.14        — smooth scroll (already in UltraMotion)
  ✦ D3.js 7             — data visualizations, SVG, force graphs
  ✦ anime.js 3.2        — micro-animations, timeline sequences
  ✦ tsParticles 3       — GPU particle system (replaces canvas 2D)
  ✦ Typed.js 2.1        — typewriter effect with cursor
  ✦ Chart.js 4          — charts: line, bar, doughnut, radar
  ✦ Splitting.js 1.0    — char/word/line text splitting
  ✦ Swiper 11           — touch-enabled slider/carousel
  ✦ VANTA.js 0.5        — animated 3D WebGL backgrounds
  ✦ ScrollReveal 4      — scroll-triggered entrance effects
  ✦ Vivus.js 0.5        — SVG path drawing animation
  ✦ CountUp.js 2        — animated number counters (replaces GSAP counter)
  ✦ Particles.js        — legacy particles (fallback for tsParticles)

Node.js package.json: always included for local builds

Usage:
    from ailex_vision.max_effects_system import MaxEffects
    me = MaxEffects()
    html = me.inject(html, theme="dark_luxury")

    # In UltraMotionSystem (auto-called):
    html = UltraMotionSystem().inject(html)  # already includes MaxEffects
"""

from __future__ import annotations

import re
import json
from typing import Optional


# ── CDN catalogue (all pinned versions) ───────────────────────────────────────

CDNS = {
    # Core (already in UltraMotion)
    "three":       "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.min.js",
    "gsap":        "https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js",
    "gsap_st":     "https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js",
    "lenis":       "https://cdn.jsdelivr.net/npm/lenis@1.1.14/dist/lenis.min.js",

    # New additions
    "tailwind":    "https://cdn.tailwindcss.com",
    "d3":          "https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js",
    "anime":       "https://cdn.jsdelivr.net/npm/animejs@3.2.2/lib/anime.min.js",
    "tsparticles": "https://cdn.jsdelivr.net/npm/tsparticles@3.5.0/tsparticles.bundle.min.js",
    "typed":       "https://cdn.jsdelivr.net/npm/typed.js@2.1.0/dist/typed.umd.js",
    "chartjs":     "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js",
    "splitting_css":"https://cdn.jsdelivr.net/npm/splitting@1.0.6/dist/splitting.min.css",
    "splitting":   "https://cdn.jsdelivr.net/npm/splitting@1.0.6/dist/splitting.min.js",
    "swiper_css":  "https://cdn.jsdelivr.net/npm/swiper@11.1.4/swiper-bundle.min.css",
    "swiper":      "https://cdn.jsdelivr.net/npm/swiper@11.1.4/swiper-bundle.min.js",
    "vanta_three": "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.min.js",
    "vanta":       "https://cdn.jsdelivr.net/npm/vanta@0.5.24/dist/vanta.net.min.js",
    "scrollreveal":"https://unpkg.com/scrollreveal@4.0.9/dist/scrollreveal.min.js",
    "vivus":       "https://cdn.jsdelivr.net/npm/vivus@0.5.2/dist/vivus.min.js",
    "countup":     "https://cdn.jsdelivr.net/npm/countup.js@2.8.0/dist/countUp.umd.js",
    "confetti":    "https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.3/dist/confetti.browser.min.js",
}


# ── Tailwind luxury config ─────────────────────────────────────────────────────

TAILWIND_CONFIG_JS = """
<script>
tailwind.config = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // AILEX luxury palette
        obsidian:  '#050507',
        noir:      '#0C0C10',
        panel:     '#161620',
        gold:      '#B09028',
        'gold-l':  '#C8A840',
        'gold-p':  '#EAD880',
        burgundy:  '#520812',
        crimson:   '#840F28',
        rose:      '#BE4A62',
        'rose-p':  '#E8A8B8',
        ivory:     '#F2EAD8',
        cream:     '#FDFAF5',
        // Brand neutrals
        'muted':   '#686870',
        'muted2':  '#969AA8',
      },
      fontFamily: {
        serif:    ["'Cormorant Garamond'", 'Georgia', 'serif'],
        display:  ["'Playfair Display'", 'serif'],
        heading:  ["'Cinzel'", 'serif'],
        mono:     ["'Courier Prime'", 'monospace'],
        sans:     ["'Montserrat'", 'system-ui', 'sans-serif'],
        orbitron: ["'Orbitron'", 'sans-serif'],
        space:    ["'Space Grotesk'", 'sans-serif'],
      },
      boxShadow: {
        'gold-sm':  '0 0 8px rgba(176,144,40,.4)',
        'gold-md':  '0 0 16px rgba(176,144,40,.4), 0 0 32px rgba(176,144,40,.2)',
        'gold-lg':  '0 0 24px rgba(176,144,40,.5), 0 0 48px rgba(176,144,40,.25)',
        'rose-sm':  '0 0 8px rgba(190,74,98,.4)',
        'neon-gold':'0 0 4px #B09028, 0 0 11px #B09028, 0 0 24px rgba(176,144,40,.4)',
      },
      backgroundImage: {
        'gold-gradient': 'linear-gradient(135deg, #B09028, #C8A840)',
        'dark-gradient': 'linear-gradient(135deg, #050507, #161620)',
        'royal-gradient':'linear-gradient(135deg, #0D1440, #1E2870)',
      },
      animation: {
        'float':      'float 4s ease-in-out infinite',
        'pulse-gold': 'pulseGold 3s ease-in-out infinite',
        'shimmer':    'shimmer 2s linear infinite',
        'spin-slow':  'spin 8s linear infinite',
        'bounce-soft':'bounceSoft 2s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%':      { transform: 'translateY(-10px)' },
        },
        pulseGold: {
          '0%, 100%': { boxShadow: '0 0 8px rgba(176,144,40,.4)' },
          '50%':      { boxShadow: '0 0 24px rgba(176,144,40,.8)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        bounceSoft: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%':      { transform: 'translateY(-5px)' },
        },
      },
    },
  },
  plugins: [],
};
</script>
"""


# ── CSS additions (max effects) ────────────────────────────────────────────────

MAX_CSS = """
/* ══════════════════════════════════════════════════════════════
   AILEX MaxEffects — CSS
   Tailwind + D3 + anime.js + tsParticles + Typed + Swiper + VANTA
   ══════════════════════════════════════════════════════════════ */

/* ── Splitting.js text effects ─── */
.splitting .char { display: inline-block; }
.split-reveal .char {
  opacity: 0; transform: translateY(40px) rotateX(-40deg);
  transition: opacity .5s ease, transform .5s ease;
  transition-delay: calc(var(--char-index) * .025s);
}
.split-reveal.visible .char { opacity: 1; transform: none; }

/* ── Typed.js cursor ─── */
.typed-cursor { color: var(--gold, #B09028); animation: typed-blink .7s step-end infinite; }
@keyframes typed-blink { 0%,100%{opacity:1} 50%{opacity:0} }

/* ── Swiper luxury overrides ─── */
.swiper-pagination-bullet { background: var(--gold, #B09028) !important; }
.swiper-button-next,.swiper-button-prev { color: var(--gold, #B09028) !important; }
.swiper-button-next::after,.swiper-button-prev::after { font-size: 1.2rem !important; }

/* ── D3 chart defaults ─── */
.ailex-chart text { fill: var(--muted2, #969AA8); font-family: 'Montserrat', sans-serif; font-size: 11px; }
.ailex-chart .domain, .ailex-chart .tick line { stroke: rgba(176,144,40,.2); }
.ailex-chart .bar { fill: var(--gold, #B09028); transition: opacity .2s; }
.ailex-chart .bar:hover { opacity: .75; }
.ailex-chart .line { fill: none; stroke: var(--gold, #B09028); stroke-width: 2; }

/* ── Chart.js canvas container ─── */
.chart-container { position: relative; width: 100%; max-width: 600px; }

/* ── CountUp number ─── */
.countup-number {
  font-family: 'Cormorant Garamond', serif;
  font-size: clamp(2rem, 4vw, 4rem);
  font-weight: 600; color: var(--gold-l, #C8A840);
  text-shadow: 0 0 16px rgba(176,144,40,.4);
}

/* ── Vivus SVG animation ─── */
.vivus-svg path, .vivus-svg polyline, .vivus-svg polygon {
  stroke: var(--gold, #B09028);
  stroke-width: 1.5;
  fill: none;
}

/* ── tsParticles container ─── */
#tsparticles {
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  width: 100vw; height: 100vh;
}

/* ── ScrollReveal defaults ─── */
.sr-hidden { opacity: 0; transform: translateY(20px); }

/* ── VANTA background container ─── */
.vanta-bg {
  position: absolute; inset: 0; z-index: 0;
  pointer-events: none; overflow: hidden;
}

/* ── anime.js morph shape ─── */
.morph-shape { fill: rgba(176,144,40,.06); stroke: rgba(176,144,40,.15); stroke-width: 1; }

/* ── Confetti canvas ─── */
#confetti-canvas { position: fixed; inset: 0; pointer-events: none; z-index: 9990; }
"""


# ── JS — all effects activated ─────────────────────────────────────────────────

MAX_JS_TEMPLATE = """
/* ══════════════════════════════════════════════════════════════
   AILEX MaxEffects v1.0 — All libraries active
   D3 · anime.js · tsParticles · Typed.js · Chart.js
   Splitting.js · Swiper · VANTA · ScrollReveal · Vivus · CountUp
   ══════════════════════════════════════════════════════════════ */

(function MaxEffects() {

  /* ── 1. SPLITTING.JS — char/word text split ─── */
  if (typeof Splitting !== 'undefined') {
    Splitting();
    // Activate split-reveal on scroll
    const splitEls = document.querySelectorAll('.split-reveal');
    if (splitEls.length && typeof IntersectionObserver !== 'undefined') {
      const io = new IntersectionObserver(entries => {
        entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
      }, { threshold: 0.1 });
      splitEls.forEach(el => io.observe(el));
    }
  }

  /* ── 2. TYPED.JS — typewriter effect ─── */
  if (typeof Typed !== 'undefined') {
    document.querySelectorAll('[data-typed]').forEach(el => {
      const strings = (el.dataset.typed || el.dataset.strings || '').split('|').filter(Boolean);
      if (!strings.length) return;
      new Typed(el, {
        strings,
        typeSpeed: 60,
        backSpeed: 30,
        backDelay: 2000,
        loop: true,
        showCursor: true,
        cursorChar: '|',
      });
    });
  }

  /* ── 3. TSPARTICLES — GPU particle system ─── */
  if (typeof tsParticles !== 'undefined' && document.getElementById('tsparticles')) {
    tsParticles.load('tsparticles', {
      fpsLimit: 60,
      interactivity: {
        events: {
          onHover: { enable: true, mode: 'repulse' },
          onClick: { enable: true, mode: 'push' },
        },
        modes: {
          repulse: { distance: 80, duration: 0.4 },
          push:    { quantity: 3 },
        },
      },
      particles: {
        color: { value: ['#B09028','#C8A840','#BE4A62','#E8A8B8','#F2EAD8'] },
        links: {
          color: '#B09028', distance: 130, enable: true,
          opacity: 0.15, width: 1,
        },
        move: { enable: true, speed: 0.8, random: true, outModes: 'bounce' },
        number: { value: 55, density: { enable: true, area: 900 } },
        opacity: { value: { min: 0.15, max: 0.55 }, animation: { enable: true, speed: 0.5 } },
        shape: { type: ['circle','triangle'] },
        size:  { value: { min: 1, max: 3 } },
      },
      background: { opacity: 0 },
      detectRetina: true,
    }).catch(() => {});
  }

  /* ── 4. COUNTUP.JS — animated counters ─── */
  if (typeof CountUp !== 'undefined') {
    const cObs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        const el    = e.target;
        const end   = parseFloat(el.dataset.count || '0');
        const dec   = el.dataset.decimal ? 1 : 0;
        const sfx   = el.dataset.suffix || '';
        const opts  = { duration: 2.2, decimalPlaces: dec, suffix: sfx,
                        useEasing: true, useGrouping: true };
        try {
          const cu = new CountUp(el, end, opts);
          if (!cu.error) cu.start();
        } catch(_) { el.textContent = end.toLocaleString() + sfx; }
        cObs.unobserve(el);
      });
    }, { threshold: 0.3 });
    document.querySelectorAll('[data-count]').forEach(el => cObs.observe(el));
  }

  /* ── 5. ANIME.JS — micro-animations ─── */
  if (typeof anime !== 'undefined') {
    // Animate elements with data-anime attribute
    document.querySelectorAll('[data-anime]').forEach((el, i) => {
      const cfg = el.dataset.anime;
      anime({
        targets: el,
        opacity: [0, 1],
        translateY: [30, 0],
        duration: 800,
        delay: i * 80,
        easing: 'easeOutExpo',
        autoplay: false,
        begin: (anim) => {
          const io = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting) { anim.play(); io.disconnect(); }
          }, { threshold: 0.1 });
          io.observe(el);
        }
      });
    });

    // Floating shapes (SVG morphs)
    document.querySelectorAll('.morph-shape').forEach(el => {
      anime({
        targets: el,
        d: [
          { value: el.getAttribute('d') || 'M0,0 L100,0 L100,100 L0,100 Z' },
        ],
        duration: 4000,
        loop: true,
        direction: 'alternate',
        easing: 'easeInOutSine',
      });
    });
  }

  /* ── 6. SWIPER — touch carousels ─── */
  if (typeof Swiper !== 'undefined') {
    document.querySelectorAll('.swiper:not([data-no-swiper])').forEach(el => {
      new Swiper(el, {
        slidesPerView: 'auto',
        spaceBetween: 16,
        loop: el.querySelectorAll('.swiper-slide').length > 3,
        grabCursor: true,
        pagination: { el: '.swiper-pagination', clickable: true },
        navigation: { nextEl: '.swiper-button-next', prevEl: '.swiper-button-prev' },
        breakpoints: {
          480:  { slidesPerView: 2 },
          768:  { slidesPerView: 3 },
          1024: { slidesPerView: 4 },
        },
        autoplay: el.dataset.autoplay ? { delay: 4000, pauseOnMouseEnter: true } : false,
      });
    });
  }

  /* ── 7. SCROLLREVEAL — entrance effects ─── */
  if (typeof ScrollReveal !== 'undefined') {
    const sr = ScrollReveal({
      distance: '24px', duration: 800,
      easing: 'cubic-bezier(0.4, 0, 0.2, 1)',
      origin: 'bottom', interval: 80,
      reset: false, useDelay: 'onload',
      viewOffset: { bottom: 60 },
    });
    sr.reveal('.sr-reveal',      { origin: 'bottom' });
    sr.reveal('.sr-reveal-left', { origin: 'left' });
    sr.reveal('.sr-reveal-right',{ origin: 'right' });
    sr.reveal('.sr-reveal-top',  { origin: 'top' });
    sr.reveal('.sr-scale',       { origin: 'bottom', scale: 0.9 });
    sr.reveal('.sr-stagger > *', { interval: 100 });
  }

  /* ── 8. VIVUS — SVG drawing animation ─── */
  if (typeof Vivus !== 'undefined') {
    document.querySelectorAll('[data-vivus],.vivus-animate').forEach(el => {
      new Vivus(el, {
        type: 'oneByOne',
        duration: 200,
        animTimingFunction: Vivus.EASE,
      });
    });
  }

  /* ── 9. CHART.JS — default chart setup ─── */
  if (typeof Chart !== 'undefined') {
    Chart.defaults.color         = 'rgba(150, 154, 168, 0.8)';
    Chart.defaults.borderColor   = 'rgba(176, 144, 40, 0.15)';
    Chart.defaults.font.family   = "'Montserrat', sans-serif";
    Chart.defaults.font.size     = 12;
    Chart.defaults.plugins.legend.labels.color = '#969AA8';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(6,6,8,.95)';
    Chart.defaults.plugins.tooltip.borderColor     = 'rgba(176,144,40,.3)';
    Chart.defaults.plugins.tooltip.borderWidth     = 1;
    Chart.defaults.plugins.tooltip.padding         = 12;
    Chart.defaults.plugins.tooltip.titleColor      = '#EAD880';
    Chart.defaults.plugins.tooltip.bodyColor       = '#969AA8';
    // Auto-init charts from data-chart-type attributes
    document.querySelectorAll('canvas[data-chart]').forEach(canvas => {
      try {
        const cfg = JSON.parse(canvas.dataset.chart);
        new Chart(canvas, cfg);
      } catch(_) {}
    });
  }

  /* ── 10. D3.js — data visualizations ─── */
  if (typeof d3 !== 'undefined') {
    // Auto-render bar charts from data-d3-bar attribute
    document.querySelectorAll('[data-d3-bar]').forEach(el => {
      try {
        const data   = JSON.parse(el.dataset.d3Bar);
        const width  = el.clientWidth || 400;
        const height = parseInt(el.dataset.height || '200');
        const margin = { top: 10, right: 20, bottom: 30, left: 40 };

        const svg = d3.select(el).append('svg')
          .attr('width', width).attr('height', height)
          .attr('class', 'ailex-chart');

        const x = d3.scaleBand().range([margin.left, width - margin.right])
                    .domain(data.map(d => d.label)).padding(0.3);
        const y = d3.scaleLinear().range([height - margin.bottom, margin.top])
                    .domain([0, d3.max(data, d => d.value)]);

        svg.append('g').attr('transform', `translate(0,${height-margin.bottom})`)
           .call(d3.axisBottom(x)).attr('class', 'domain');
        svg.append('g').attr('transform', `translate(${margin.left},0)`)
           .call(d3.axisLeft(y).ticks(4)).attr('class', 'domain');

        svg.selectAll('.bar').data(data).join('rect')
           .attr('class', 'bar')
           .attr('x', d => x(d.label)).attr('y', d => y(d.value))
           .attr('width', x.bandwidth())
           .attr('height', d => height - margin.bottom - y(d.value))
           .attr('rx', 2);
      } catch(_) {}
    });
  }

  /* ── 11. VANTA.js — animated 3D backgrounds ─── */
  if (typeof VANTA !== 'undefined') {
    document.querySelectorAll('[data-vanta]').forEach(el => {
      const effect = el.dataset.vanta || 'NET';
      const VantaFn = VANTA[effect] || VANTA.NET;
      if (typeof VantaFn === 'function') {
        VantaFn({
          el,
          THREE: typeof THREE !== 'undefined' ? THREE : undefined,
          mouseControls: true,
          touchControls: true,
          color:       0xB09028,
          backgroundColor: 0x050507,
          points: 8.0,
          maxDistance: 22.0,
          spacing: 18.0,
          opacity: 0.4,
        });
      }
    });
  }

  /* ── 12. GSAP + anime.js combined timeline ─── */
  if (typeof gsap !== 'undefined' && typeof anime !== 'undefined') {
    // Hero mega entrance — GSAP orchestrates, anime.js does micro effects
    const heroTl = gsap.timeline({ delay: 0.3 });
    heroTl.fromTo('.hero-badge, [data-hero-badge]',
      { opacity: 0, x: -20, filter: 'blur(8px)' },
      { opacity: 1, x: 0, filter: 'blur(0)', duration: 0.7, ease: 'power3.out' });

    // anime.js stagger on any [data-stagger] containers
    document.querySelectorAll('[data-anime-stagger]').forEach(parent => {
      const children = [...parent.children];
      anime({
        targets: children,
        opacity: [0, 1],
        translateY: [20, 0],
        delay: anime.stagger(80),
        duration: 600,
        easing: 'easeOutExpo',
        autoplay: false,
        begin: (anim) => {
          const io = new IntersectionObserver(es => {
            if (es[0].isIntersecting) { anim.play(); io.disconnect(); }
          }, { threshold: 0.05 });
          io.observe(parent);
        }
      });
    });
  }

})();
"""


# ── package.json for Node.js projects ─────────────────────────────────────────

def generate_package_json(project_name: str, description: str = "") -> str:
    slug = re.sub(r"[^a-z0-9-]", "-", project_name.lower())
    return json.dumps({
        "name": slug,
        "version": "1.0.0",
        "description": description or f"{project_name} — AILEX MaxEffects",
        "private": True,
        "scripts": {
            "dev":       "vite",
            "build":     "vite build",
            "preview":   "vite preview",
            "lint":      "eslint src --ext .js,.ts",
        },
        "dependencies": {
            "three":         "^0.169.0",
            "gsap":          "^3.12.5",
            "lenis":         "^1.1.14",
            "d3":            "^7.9.0",
            "animejs":       "^3.2.2",
            "tsparticles":   "^3.5.0",
            "typed.js":      "^2.1.0",
            "chart.js":      "^4.4.4",
            "splitting":     "^1.0.6",
            "swiper":        "^11.1.4",
            "vanta":         "^0.5.24",
            "scrollreveal":  "^4.0.9",
            "vivus":         "^0.5.2",
            "countup.js":    "^2.8.0",
            "canvas-confetti":"^1.9.3",
        },
        "devDependencies": {
            "vite":           "^5.4.0",
            "tailwindcss":    "^3.4.0",
            "autoprefixer":   "^10.4.0",
            "typescript":     "^5.5.0",
            "@types/d3":      "^7.4.3",
        },
    }, indent=2)


# ── Main class ─────────────────────────────────────────────────────────────────

class MaxEffects:
    """
    Injects ALL visual libraries into any HTML page.
    Permanent standard for every AILEX-generated site.

    Effects activated:
      Tailwind CSS · D3.js · anime.js · tsParticles · Typed.js
      Chart.js · Splitting.js · Swiper · VANTA.js · ScrollReveal
      Vivus · CountUp.js · confetti
    """

    # Which CDNs to inject in <head> (CSS before JS)
    HEAD_CSS_CDNS  = ["splitting_css", "swiper_css"]
    HEAD_SCRIPT_CDNS = [
        "tailwind",      # must be first for config
        "splitting",
        "vivus",
        "countup",
        "scrollreveal",
    ]
    # Defer scripts (after DOM)
    DEFER_CDNS = [
        "d3",
        "anime",
        "tsparticles",
        "typed",
        "chartjs",
        "swiper",
        "vanta",
        "confetti",
    ]

    def inject(self, html: str, theme: str = "dark_luxury") -> str:
        """
        Inject all MaxEffects libraries into an HTML page.
        Safe to call multiple times — checks for existing injection.
        """
        if "MaxEffects v1.0" in html:
            return html   # already injected

        # 1. CSS links in <head>
        css_links = "\n".join(
            f'<link rel="stylesheet" href="{CDNS[k]}">'
            for k in self.HEAD_CSS_CDNS if k in CDNS
        )

        # 2. Inline scripts in <head> (sync, needed before body)
        head_scripts = "\n".join(
            f'<script src="{CDNS[k]}"></script>'
            for k in self.HEAD_SCRIPT_CDNS if k in CDNS
        )

        # 3. Tailwind config (after tailwind.js)
        tailwind_cfg = TAILWIND_CONFIG_JS

        # 4. MaxEffects CSS
        css_block = f"<style>{MAX_CSS}</style>"

        # 5. Add tsparticles canvas after <body>
        particles_div = '<div id="tsparticles" aria-hidden="true"></div>'

        # 6. Deferred scripts before </body>
        defer_scripts = "\n".join(
            f'<script src="{CDNS[k]}" defer></script>'
            for k in self.DEFER_CDNS if k in CDNS
        )

        # 7. MaxEffects activation JS before </body>
        activation = f"\n<script>\n{MAX_JS_TEMPLATE}\n</script>\n"

        # ── Inject ──────────────────────────────────────────────────────────────
        # Into <head>
        head_inject = f"\n{css_links}\n{head_scripts}\n{tailwind_cfg}\n{css_block}\n"
        html = re.sub(r"(</head>)", f"{head_inject}\\1", html, count=1)

        # After <body> tag
        html = re.sub(r"(<body[^>]*>)", r"\1\n" + particles_div + "\n", html, count=1)

        # Before </body>
        body_inject = f"\n{defer_scripts}\n{activation}\n"
        html = re.sub(r"(</body>)", f"{body_inject}\\1", html, count=1)

        return html

    def get_node_package(self, project_name: str, description: str = "") -> str:
        """Return package.json string for a Node.js project."""
        return generate_package_json(project_name, description)

    def describe(self) -> str:
        lines = ["MaxEffects System — All Visual Libraries", "─" * 55]
        libs = [
            ("Tailwind CSS 3",   "Utility classes + luxury custom config"),
            ("D3.js 7",          "Data visualizations, SVG, force graphs"),
            ("anime.js 3.2",     "Micro-animations, timeline sequences"),
            ("tsParticles 3",    "GPU particle system (WebGL-accelerated)"),
            ("Typed.js 2.1",     "Typewriter effect with cursor"),
            ("Chart.js 4",       "Line, bar, doughnut, radar charts"),
            ("Splitting.js 1.0", "Char/word/line text splitting"),
            ("Swiper 11",        "Touch-enabled slider/carousel"),
            ("VANTA.js 0.5",     "Animated 3D WebGL backgrounds"),
            ("ScrollReveal 4",   "Scroll-triggered entrance effects"),
            ("Vivus.js 0.5",     "SVG path drawing animation"),
            ("CountUp.js 2",     "Animated number counters"),
            ("canvas-confetti",  "Celebration particle burst"),
        ]
        for name, desc in libs:
            lines.append(f"  ✦ {name:<20} {desc}")
        return "\n".join(lines)


# ── Singleton ─────────────────────────────────────────────────────────────────

_me: Optional[MaxEffects] = None

def get_max_effects() -> MaxEffects:
    global _me
    if _me is None:
        _me = MaxEffects()
    return _me


def max_inject(html: str, theme: str = "dark_luxury") -> str:
    """One-call MaxEffects injection."""
    return get_max_effects().inject(html, theme)


if __name__ == "__main__":
    me = MaxEffects()
    print(me.describe())
    print()
    # Quick test
    test_html = "<!DOCTYPE html><html><head><title>T</title></head><body><h1>Hi</h1></body></html>"
    result = me.inject(test_html)
    checks = [
        ("Tailwind", "tailwindcss" in result),
        ("D3.js",    "d3@7" in result),
        ("anime.js", "animejs@3" in result),
        ("tsParticles", "tsparticles" in result),
        ("Typed.js", "typed.js" in result),
        ("Chart.js", "chart.js" in result),
        ("Splitting","splitting" in result),
        ("Swiper",   "swiper" in result),
        ("VANTA",    "vanta" in result),
        ("ScrollReveal", "scrollreveal" in result),
        ("Vivus",    "vivus" in result),
        ("CountUp",  "countup" in result),
        ("MaxEffects JS", "MaxEffects v1.0" in result),
        ("Tailwind Config", "tailwind.config" in result),
        ("tsParticles div", "id=\"tsparticles\"" in result),
    ]
    all_ok = all(v for _,v in checks)
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'}  {name}")
    print(f"\n{'✅ ALL PASS' if all_ok else '❌ FAIL'}")
    print()
    print("Node.js package.json:")
    print(me.get_node_package("my-site", "AI-generated site")[:200], "...")
