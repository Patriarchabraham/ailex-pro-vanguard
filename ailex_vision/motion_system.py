"""
AILEX MotionSystem v1.0 — Cinematic Motion Design for Generated Websites
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sources implemented:
  ↳ GSAP 3.12.5 + ScrollTrigger  github.com/greensock/GSAP (MIT, 100% free 2024)
  ↳ Lenis 1.1.14                 github.com/darkroomengineering/lenis (MIT)
  ↳ Theatre.js patterns           github.com/theatre-js/theatre (MIT)
  ↳ Anime.js patterns             github.com/juliangarnier/anime (MIT)
  ↳ Magnetic UI pattern           motion.dev/docs/gestures

USAGE:
    from ailex_vision.motion_system import MotionSystem
    ms = MotionSystem()
    html = ms.inject(html, preset="luxury_dating")

PRESETS:
    luxury_dating        — ROMA, dating, lifestyle sites
    institutional        — diplomatic, NGO, formal portals
    luxury_restaurant    — hospitality, dining
    minimal              — portfolios, agencies
    cinematic            — hero-heavy, storytelling sites
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Optional


# ── CDN VERSIONS (pinned for stability) ───────────────────────────────────────
GSAP_CDN     = "https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"
ST_CDN       = "https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js"
LENIS_CDN    = "https://cdn.jsdelivr.net/npm/lenis@1.1.14/dist/lenis.min.js"
SPLITTEXT_CDN= "https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/SplitText.min.js"


# ── PRESET CONFIGURATION ──────────────────────────────────────────────────────
@dataclass
class MotionPreset:
    name:             str
    lenis_duration:   float = 1.4      # scroll smoothness
    cursor:           bool  = True      # custom cursor dot
    text_split:       bool  = True      # hero char-by-char entrance
    magnetic:         bool  = True      # magnetic CTA buttons
    tilt_3d:          bool  = True      # card 3D hover tilt
    parallax:         bool  = True      # scroll parallax on BG
    stagger_gallery:  bool  = True      # gallery image stagger
    stagger_cards:    bool  = True      # profile/feature card stagger
    floating:         bool  = False     # floating animation on elements
    scroll_progress:  bool  = False     # top progress bar
    page_transition:  bool  = False     # Barba.js-style transitions
    cursor_color:     str   = "rgba(184,144,48,.8)"   # gold
    cursor_hover_scale: float = 3.0


PRESETS: Dict[str, MotionPreset] = {
    "luxury_dating": MotionPreset(
        name="luxury_dating",
        lenis_duration=1.5,
        cursor=True, text_split=True, magnetic=True,
        tilt_3d=True, parallax=True, stagger_gallery=True,
        stagger_cards=True, floating=True, scroll_progress=True,
        cursor_color="rgba(184,144,48,.9)",
    ),
    "institutional": MotionPreset(
        name="institutional",
        lenis_duration=1.2,
        cursor=False, text_split=True, magnetic=False,
        tilt_3d=False, parallax=True, stagger_gallery=True,
        stagger_cards=True, floating=False, scroll_progress=True,
    ),
    "luxury_restaurant": MotionPreset(
        name="luxury_restaurant",
        lenis_duration=1.4,
        cursor=True, text_split=True, magnetic=True,
        tilt_3d=True, parallax=True, stagger_gallery=True,
        stagger_cards=True, floating=False, scroll_progress=False,
        cursor_color="rgba(212,175,55,.9)",
    ),
    "minimal": MotionPreset(
        name="minimal",
        lenis_duration=1.0,
        cursor=True, text_split=False, magnetic=False,
        tilt_3d=False, parallax=False, stagger_gallery=True,
        stagger_cards=False, floating=False, scroll_progress=False,
        cursor_color="rgba(0,0,0,.8)",
    ),
    "cinematic": MotionPreset(
        name="cinematic",
        lenis_duration=1.8,
        cursor=True, text_split=True, magnetic=True,
        tilt_3d=True, parallax=True, stagger_gallery=True,
        stagger_cards=True, floating=True, scroll_progress=True,
        page_transition=True,
        cursor_color="rgba(255,255,255,.8)",
    ),
}


class MotionSystem:
    """
    Generates and injects a complete motion design system into any HTML.
    Based on GSAP, Lenis, and patterns from Theatre.js / Anime.js / motion.dev.

    Core philosophy (from Theatre.js):
      "Separate motion orchestration from component logic."
    Every effect is optional and preset-driven.
    """

    def get_head_scripts(self, preset: str = "luxury_dating") -> str:
        """CDN script tags to inject into <head> (before </head>)."""
        p = PRESETS.get(preset, PRESETS["luxury_dating"])
        scripts = [
            f'<script src="{GSAP_CDN}" defer></script>',
            f'<script src="{ST_CDN}" defer></script>',
            f'<script src="{LENIS_CDN}" defer></script>',
        ]
        return "\n".join(scripts)

    def get_cursor_html(self, preset: str = "luxury_dating") -> str:
        """Custom cursor HTML elements to inject after <body>."""
        p = PRESETS.get(preset, PRESETS["luxury_dating"])
        if not p.cursor:
            return ""
        return (
            '<div id="ailex-cursor" aria-hidden="true"></div>'
            '<div id="ailex-dot" aria-hidden="true"></div>'
        )

    def get_progress_html(self, preset: str = "luxury_dating") -> str:
        """Scroll progress bar HTML."""
        p = PRESETS.get(preset, PRESETS["luxury_dating"])
        if not p.scroll_progress:
            return ""
        return '<div id="ailex-progress" aria-hidden="true"></div>'

    def get_motion_css(self, preset: str = "luxury_dating") -> str:
        """Motion CSS to inject into the page's <style> block."""
        p = PRESETS.get(preset, PRESETS["luxury_dating"])
        css_parts = []

        # Smooth scroll baseline (Lenis requires html scroll)
        css_parts.append("""
/* ── AILEX MOTION SYSTEM ──────────────────────────────────────── */
html.lenis,html.lenis body{height:auto}
.lenis.lenis-smooth{scroll-behavior:auto !important}
.lenis.lenis-smooth [data-lenis-prevent]{overscroll-behavior:contain}
.lenis.lenis-stopped{overflow:hidden}
""")

        if p.cursor:
            css_parts.append(f"""
/* ── Custom Cursor ──────────────────────────────────────────── */
@media(hover:hover) and (pointer:fine){{
  *{{cursor:none !important}}
  #ailex-cursor{{
    position:fixed;top:0;left:0;z-index:9998;pointer-events:none;
    width:32px;height:32px;border-radius:50%;
    border:1px solid {p.cursor_color};
    transition:transform .08s ease,width .25s ease,height .25s ease,
               border-color .25s ease,background .25s ease;
    mix-blend-mode:difference;
  }}
  #ailex-dot{{
    position:fixed;top:0;left:0;z-index:9999;pointer-events:none;
    width:5px;height:5px;border-radius:50%;
    background:{p.cursor_color};
    transition:transform .04s linear;
  }}
  #ailex-cursor.hover{{
    width:{int(32 * p.cursor_hover_scale)}px;
    height:{int(32 * p.cursor_hover_scale)}px;
    background:rgba(255,255,255,.06);
    border-color:rgba(255,255,255,.5);
  }}
  #ailex-cursor.press{{transform:scale(.85)}}
}}
""")

        if p.scroll_progress:
            css_parts.append("""
/* ── Scroll Progress Bar ────────────────────────────────────── */
#ailex-progress{
  position:fixed;top:0;left:0;z-index:1001;
  height:2px;width:0%;
  background:linear-gradient(to right,var(--gold,#B89030),var(--rose,#C05068));
  transition:width .05s linear;
  pointer-events:none;
}
""")

        if p.text_split:
            css_parts.append("""
/* ── Text Split Animation ───────────────────────────────────── */
.ms-char{display:inline-block;will-change:transform,opacity}
.ms-word{display:inline-block;overflow:hidden}
""")

        if p.tilt_3d:
            css_parts.append("""
/* ── 3D Tilt Cards ──────────────────────────────────────────── */
.tilt-card{transform-style:preserve-3d;will-change:transform;
           transition:transform .12s ease !important}
.tilt-card:hover{box-shadow:0 24px 64px rgba(0,0,0,.55)}
""")

        if p.floating:
            css_parts.append("""
/* ── Floating Animation ─────────────────────────────────────── */
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
.ms-float{animation:float 4s ease-in-out infinite}
""")

        # HyperFrame transitions — Cinema-grade section transitions
        css_parts.append("""
/* ── HyperFrame Transitions (section entrance sequences) ────── */
.hf-frame{position:relative;overflow:hidden}
.hf-frame::before{
  content:'';position:absolute;inset:0;
  background:var(--obsidian,#060608);
  transform:scaleX(1);transform-origin:right;
  transition:transform .9s cubic-bezier(.77,0,.18,1);
  z-index:10;pointer-events:none;
}
.hf-frame.hf-revealed::before{transform:scaleX(0)}
""")

        return "\n".join(css_parts)

    def get_motion_js(self, preset: str = "luxury_dating") -> str:
        """Complete motion system JS to inject before </body>."""
        p = PRESETS.get(preset, PRESETS["luxury_dating"])
        parts = []

        # Header
        parts.append(f"""
/* ═══════════════════════════════════════════════════════════════════
   AILEX MotionSystem v1.0 — preset: {preset}
   Sources: GSAP (MIT), Lenis (MIT), Theatre.js patterns (MIT)
   Runs after DOM + CDN scripts are loaded
   ═══════════════════════════════════════════════════════════════════ */
(function initMotion(){{
  // Wait for GSAP + Lenis to be available
  if(typeof gsap === 'undefined' || typeof Lenis === 'undefined'){{
    window.addEventListener('load', initMotion); return;
  }}
  gsap.registerPlugin(ScrollTrigger);
""")

        # Lenis smooth scroll
        parts.append(f"""
  /* ── 1. LENIS SMOOTH SCROLL (darkroomengineering/lenis) ────────── */
  const lenis = new Lenis({{
    duration: {p.lenis_duration},
    easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    orientation: 'vertical',
    smoothWheel: true,
    touchMultiplier: 1.5,
  }});
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add(time => lenis.raf(time * 1000));
  gsap.ticker.lagSmoothing(0);
  // Anchor clicks use Lenis
  document.querySelectorAll('a[href^="#"]').forEach(a => {{
    a.addEventListener('click', e => {{
      const t = document.querySelector(a.getAttribute('href'));
      if(t) {{ e.preventDefault(); lenis.scrollTo(t, {{offset:-60, duration:{p.lenis_duration}}}); }}
    }});
  }});
""")

        # Custom cursor
        if p.cursor:
            parts.append("""
  /* ── 2. CUSTOM CURSOR ──────────────────────────────────────────── */
  const cur  = document.getElementById('ailex-cursor');
  const dot  = document.getElementById('ailex-dot');
  if(cur && dot && window.matchMedia('(hover:hover)').matches){
    let mx=0,my=0,cx=0,cy=0;
    document.addEventListener('mousemove', e=>{mx=e.clientX;my=e.clientY;});
    document.addEventListener('mousedown', ()=>cur.classList.add('press'));
    document.addEventListener('mouseup',   ()=>cur.classList.remove('press'));
    (function tick(){
      cx += (mx-cx)*.1; cy += (my-cy)*.1;
      cur.style.transform = `translate(${cx-16}px,${cy-16}px)`;
      dot.style.transform = `translate(${mx-2.5}px,${my-2.5}px)`;
      requestAnimationFrame(tick);
    })();
    const hovers = 'a,button,.cam-card,.prof-card,.ev-card,.plan,.stor-card,.scr-btn';
    document.querySelectorAll(hovers).forEach(el=>{
      el.addEventListener('mouseenter',()=>cur.classList.add('hover'));
      el.addEventListener('mouseleave',()=>cur.classList.remove('hover'));
    });
  }
""")

        # Scroll progress bar
        if p.scroll_progress:
            parts.append("""
  /* ── 3. SCROLL PROGRESS BAR ─────────────────────────────────────── */
  const prog = document.getElementById('ailex-progress');
  if(prog){
    lenis.on('scroll',({progress})=>{prog.style.width=`${progress*100}%`;});
  }
""")

        # Hero text split entrance
        if p.text_split:
            parts.append("""
  /* ── 4. HERO TITLE — CHAR ENTRANCE (Theatre.js pattern) ────────── */
  (function splitHero(){
    const h1 = document.querySelector('.hero-title,.page-title,h1');
    if(!h1) return;
    const nodes = [...h1.childNodes];
    h1.innerHTML = '';
    nodes.forEach(node=>{
      if(node.nodeType===3){  // text node
        [...node.textContent].forEach(ch=>{
          const s=document.createElement('span');
          s.className='ms-char';s.textContent=ch===' '?' ':ch;
          if(ch===' ')s.style.display='inline';
          h1.appendChild(s);
        });
      } else {  // element node (em, strong, etc.)
        const wrap=node.cloneNode(false);
        [...node.textContent].forEach(ch=>{
          const s=document.createElement('span');
          s.className='ms-char';s.textContent=ch===' '?' ':ch;
          if(ch===' ')s.style.display='inline';
          wrap.appendChild(s);
        });
        h1.appendChild(wrap);
      }
    });
    gsap.fromTo(h1.querySelectorAll('.ms-char'),
      { opacity:0, y:50, rotateX:-40 },
      {
        opacity:1, y:0, rotateX:0,
        duration:.8, ease:'expo.out',
        stagger:.022, delay:.25,
        transformOrigin:'center bottom',
      }
    );
  })();
  // Hero supporting elements fade in
  gsap.fromTo(
    ['.hero-badge','.hero-sub','.hero-tag','.hero-btns','.hero-kpis'],
    {opacity:0,y:24},
    {opacity:1,y:0,duration:.9,ease:'power3.out',stagger:.12,delay:.7}
  );
""")

        # Magnetic buttons
        if p.magnetic:
            parts.append("""
  /* ── 5. MAGNETIC BUTTONS (motion.dev gesture pattern) ───────────── */
  document.querySelectorAll('.btn-prim,.btn-ghost,.nav-cta').forEach(btn=>{
    btn.addEventListener('mousemove',e=>{
      const r=btn.getBoundingClientRect();
      const x=(e.clientX-r.left-r.width/2)*.18;
      const y=(e.clientY-r.top-r.height/2)*.18;
      gsap.to(btn,{x,y,duration:.3,ease:'power2.out'});
    });
    btn.addEventListener('mouseleave',()=>{
      gsap.to(btn,{x:0,y:0,duration:.5,ease:'elastic.out(1,.5)'});
    });
  });
""")

        # 3D tilt cards
        if p.tilt_3d:
            parts.append("""
  /* ── 6. 3D TILT CARDS ───────────────────────────────────────────── */
  document.querySelectorAll('.cam-card,.stor-card,.ev-card,.plan').forEach(card=>{
    card.classList.add('tilt-card');
    card.addEventListener('mousemove',e=>{
      const r=card.getBoundingClientRect();
      const x=(e.clientX-r.left)/r.width-.5;
      const y=(e.clientY-r.top)/r.height-.5;
      gsap.to(card,{
        rotateX:-y*7, rotateY:x*7,
        transformPerspective:900,
        duration:.2,ease:'power1.out',
      });
    });
    card.addEventListener('mouseleave',()=>{
      gsap.to(card,{rotateX:0,rotateY:0,duration:.6,ease:'elastic.out(1,.5)'});
    });
  });
""")

        # Parallax
        if p.parallax:
            parts.append("""
  /* ── 7. PARALLAX SCROLL (GSAP ScrollTrigger) ───────────────────── */
  // Hero background
  const heroBg = document.querySelector('.hero-bg,.hero-image');
  if(heroBg){
    gsap.to(heroBg,{
      y:'20%',ease:'none',
      scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:1},
    });
  }
  // Section backgrounds with data-parallax attr
  document.querySelectorAll('[data-parallax]').forEach(el=>{
    const spd=parseFloat(el.dataset.parallax)||.3;
    gsap.to(el,{
      y:`${spd*100}%`,ease:'none',
      scrollTrigger:{
        trigger:el.parentElement||el,
        start:'top bottom',end:'bottom top',scrub:1,
      },
    });
  });
""")

        # Gallery stagger
        if p.stagger_gallery:
            parts.append("""
  /* ── 8. GALLERY STAGGER (Anime.js pattern via GSAP) ────────────── */
  const galleryItems=document.querySelectorAll('.g-cell,.gallery-item,.grid-cell');
  if(galleryItems.length){
    gsap.fromTo(galleryItems,
      {opacity:0,scale:.9,y:30},
      {
        opacity:1,scale:1,y:0,
        duration:.7,ease:'power2.out',
        stagger:{amount:.6,from:'start'},
        scrollTrigger:{trigger:galleryItems[0].parentElement,start:'top 82%',once:true},
      }
    );
  }
""")

        # Profile card stagger
        if p.stagger_cards:
            parts.append("""
  /* ── 9. PROFILE / FEATURE CARD STAGGER ─────────────────────────── */
  // Profile scroll cards
  const profCards=document.querySelectorAll('.prof-card');
  if(profCards.length){
    gsap.fromTo(profCards,
      {opacity:0,x:50},
      {
        opacity:1,x:0,duration:.65,ease:'power2.out',
        stagger:.1,
        scrollTrigger:{trigger:'.scr-inner,.scr-wrap',start:'top 87%',once:true},
      }
    );
  }
  // Stat boxes
  gsap.fromTo('.stat-box',
    {opacity:0,y:30},
    {opacity:1,y:0,duration:.6,ease:'power2.out',stagger:.1,
     scrollTrigger:{trigger:'.stats-inner,.stats',start:'top 85%',once:true}}
  );
  // Plans
  gsap.fromTo('.plan',
    {opacity:0,y:40},
    {opacity:1,y:0,duration:.7,ease:'power2.out',stagger:.12,
     scrollTrigger:{trigger:'.plans',start:'top 85%',once:true}}
  );
""")

        # Floating elements
        if p.floating:
            parts.append("""
  /* ── 10. FLOATING ELEMENTS ─────────────────────────────────────── */
  document.querySelectorAll('.hero-kpis>div,.hero-badge').forEach((el,i)=>{
    gsap.to(el,{
      y:-8,duration:3+i*.4,ease:'sine.inOut',
      yoyo:true,repeat:-1,delay:i*.3,
    });
  });
""")

        # HyperFrame section reveals (cinematic wipe)
        parts.append("""
  /* ── 11. HYPERFRAME SECTION REVEALS (cinematic wipe) ───────────── */
  // Inspired by Theatre.js timeline orchestration:
  // each section frame wipes in from right, revealing content below
  document.querySelectorAll('.hf-frame').forEach(frame=>{
    ScrollTrigger.create({
      trigger:frame,start:'top 80%',once:true,
      onEnter:()=>frame.classList.add('hf-revealed'),
    });
  });

  /* ── 12. GSAP SCROLL REVEALS (augments existing IntersectionObserver) */
  // Stagger child elements inside containers with data-stagger
  document.querySelectorAll('[data-stagger]').forEach(container=>{
    const delay=parseFloat(container.dataset.stagger)||.1;
    const children=[...container.children];
    gsap.fromTo(children,
      {opacity:0,y:24},
      {
        opacity:1,y:0,duration:.7,ease:'power2.out',stagger:delay,
        scrollTrigger:{trigger:container,start:'top 85%',once:true},
      }
    );
  });

  /* ── 13. GSAP COUNTER (replaces native animC for visible stats) ── */
  document.querySelectorAll('.stat-n:not(.stat-decimal),[data-count]:not(.stat-decimal)').forEach(el=>{
    const end=parseInt(el.dataset.count)||0;
    const sfx=el.dataset.suffix||'';
    const obj={val:0};
    gsap.to(obj,{
      val:end,duration:2,ease:'power2.out',
      scrollTrigger:{trigger:el,start:'top 88%',once:true},
      onUpdate(){ el.textContent=Math.round(obj.val).toLocaleString('it-IT')+sfx; },
      onComplete(){ el.textContent=end.toLocaleString('it-IT')+sfx; },
    });
  });

""")

        # Close IIFE
        parts.append("""
  /* ── DONE ─────────────────────────────────────────────────────── */
})();
""")

        return "\n".join(parts)

    def inject(self, html: str, preset: str = "luxury_dating") -> str:
        """
        Inject the complete AILEX MotionSystem into an HTML string.
        Safe to call multiple times — checks for existing injection.

        Args:
            html:    Complete HTML string to enhance
            preset:  One of luxury_dating / institutional / luxury_restaurant
                     / minimal / cinematic

        Returns:
            HTML string with motion system fully integrated
        """
        if "ailex-cursor" in html or "AILEX MotionSystem" in html:
            return html  # Already injected

        # 1. Inject CDN scripts into <head>
        scripts = self.get_head_scripts(preset)
        html = re.sub(r'(</head>)', f'\n{scripts}\n\\1', html, count=1)

        # 2. Inject motion CSS into existing <style> or create new one
        motion_css = self.get_motion_css(preset)
        if '</style>' in html:
            html = html.replace('</style>', f'{motion_css}\n</style>', 1)
        else:
            html = re.sub(r'(</head>)', f'<style>{motion_css}</style>\n\\1', html, count=1)

        # 3. Inject cursor + progress HTML after <body>
        cursor_html  = self.get_cursor_html(preset)
        progress_html = self.get_progress_html(preset)
        insert_after_body = f"\n{cursor_html}\n{progress_html}\n"
        html = re.sub(r'(<body[^>]*>)', r'\1' + insert_after_body, html, count=1)

        # 4. Inject motion JS before </body>
        motion_js = f"\n<script>\n{self.get_motion_js(preset)}\n</script>\n"
        html = re.sub(r'(</body>)', f'{motion_js}\\1', html, count=1)

        return html

    @staticmethod
    def describe() -> str:
        lines = ["AILEX MotionSystem v1.0", "─" * 55]
        lines.append("Libraries: GSAP 3.12.5, ScrollTrigger, Lenis 1.1.14")
        lines.append("")
        lines.append("Presets:")
        for name, p in PRESETS.items():
            effects = []
            if p.cursor:          effects.append("cursor")
            if p.text_split:      effects.append("text-split")
            if p.magnetic:        effects.append("magnetic")
            if p.tilt_3d:         effects.append("3D-tilt")
            if p.parallax:        effects.append("parallax")
            if p.stagger_gallery: effects.append("gallery-stagger")
            if p.stagger_cards:   effects.append("card-stagger")
            if p.floating:        effects.append("floating")
            if p.scroll_progress: effects.append("scroll-progress")
            lines.append(f"  {name:<22} [{', '.join(effects)}]")
        lines.append("")
        lines.append("Usage: ms = MotionSystem(); html = ms.inject(html, 'luxury_dating')")
        return "\n".join(lines)


if __name__ == "__main__":
    print(MotionSystem.describe())
    # Quick test
    ms = MotionSystem()
    test_html = "<!DOCTYPE html><html><head><title>Test</title></head><body><h1 class='hero-title'>Hello <em>World</em></h1></body></html>"
    result = ms.inject(test_html, "luxury_dating")
    print(f"\nInjection test: {'✅ OK' if 'ailex-cursor' in result and 'GSAP' in result else '❌ FAIL'}")
    print(f"GSAP CDN added: {'✅' if 'gsap@3.12.5' in result else '❌'}")
    print(f"Lenis CDN added: {'✅' if 'lenis@1.1.14' in result else '❌'}")
    print(f"Motion CSS added: {'✅' if 'AILEX MOTION SYSTEM' in result else '❌'}")
    print(f"Motion JS added: {'✅' if 'initMotion' in result else '❌'}")
    print(f"HyperFrame CSS added: {'✅' if 'hf-frame' in result else '❌'}")
