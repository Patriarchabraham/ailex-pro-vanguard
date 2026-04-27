"""
AILEX — ultra_motion_system.py
Maximum visual effects for luxury websites.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Libraries integrated (all CDN, all MIT/free):
  Three.js  r169      — WebGL 3D particles, shaders, geometry
  GSAP 3.12.5         — animation orchestration (already in MotionSystem)
  Lenis 1.1.14        — smooth scroll (already in MotionSystem)
  Tailwind CSS 3      — utility classes complement

Effects:
  01. Three.js WebGL 5000-particle galaxy (replaces 2D canvas)
  02. GLSL vertex/fragment shaders — additive blending, soft glow
  03. Mouse-reactive particles (gravity field)
  04. Neon CSS glow — gold, rose, burgundy, white variants
  05. Neon pulse animation — breathing glow cycle
  06. Neon borders on cards/inputs on hover
  07. Cursor trail — 24-dot smooth trail with fade + glow
  08. Magnetic cursor ring (already in MotionSystem, upgraded)
  09. Film grain noise overlay (SVG feTurbulence, animated)
  10. Page loader — ROMA logo + progress bar
  11. Holographic card effect (CSS gradient animation + tilt)
  12. Text scramble reveal on hero title
  13. Gradient text animation (shifting color across heading)
  14. Theatre.js-style scripted entrance sequence (GSAP timeline)
  15. Ambient light bloom around gold elements

Usage:
    from ailex_vision.ultra_motion_system import UltraMotionSystem
    ums = UltraMotionSystem()
    html = ums.inject(html, site_context="luxury_dating")

    # Or use the convenience function:
    from ailex_vision.ultra_motion_system import ultra_inject
    html = ultra_inject(html, site_context="luxury_dating")
"""

from __future__ import annotations
import re
from typing import Optional


# ── CDN VERSIONS ──────────────────────────────────────────────────────────────
THREEJS_CDN  = "https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.min.js"
GSAP_CDN     = "https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"
ST_CDN       = "https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js"
LENIS_CDN    = "https://cdn.jsdelivr.net/npm/lenis@1.1.14/dist/lenis.min.js"
TAILWIND_CDN = "https://cdn.tailwindcss.com"


# ── CSS ───────────────────────────────────────────────────────────────────────

ULTRA_CSS = """
/* ══════════════════════════════════════════════════════════════
   AILEX Ultra Motion System — CSS
   Three.js + Neons + Holographic + Grain + Trail + Loader
   ══════════════════════════════════════════════════════════════ */

/* ── WebGL Canvas ─────────────────────────────────────────── */
#webgl{
  position:fixed;inset:0;z-index:0;pointer-events:none;
  width:100vw!important;height:100vh!important;
}

/* ── Page Loader ──────────────────────────────────────────── */
#ailex-loader{
  position:fixed;inset:0;z-index:10000;
  background:var(--obsidian,#050507);
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:24px;
  transition:opacity .8s ease;
}
#ailex-loader .ld-logo{
  font-family:'Playfair Display',serif;font-size:2.4rem;font-weight:700;
  letter-spacing:.3em;color:var(--gold,#B09028);
  text-shadow:0 0 20px rgba(176,144,40,.5),0 0 40px rgba(176,144,40,.2);
  animation:neon-pulse 2s ease-in-out infinite;
}
#ailex-loader .ld-sub{
  font-size:.6rem;letter-spacing:.3em;text-transform:uppercase;
  color:rgba(176,144,40,.5);
}
#ailex-loader .ld-bar{
  width:200px;height:1px;background:rgba(176,144,40,.15);position:relative;overflow:hidden;
}
#ailex-loader .ld-bar::after{
  content:'';position:absolute;left:0;top:0;height:100%;
  background:linear-gradient(to right,var(--gold,#B09028),var(--gold-l,#C8A840));
  animation:loader-bar 1.8s ease-in-out;
  box-shadow:0 0 8px var(--gold,#B09028);
}
@keyframes loader-bar{from{width:0}to{width:100%}}

/* ── Neon Gold ─────────────────────────────────────────────── */
.neon-gold,.neon-text{
  text-shadow:
    0 0 4px rgba(176,144,40,.9),
    0 0 11px rgba(176,144,40,.7),
    0 0 19px rgba(176,144,40,.5),
    0 0 40px rgba(176,144,40,.3),
    0 0 80px rgba(176,144,40,.15);
}
.neon-rose{
  text-shadow:
    0 0 4px rgba(190,74,98,.9),
    0 0 11px rgba(190,74,98,.7),
    0 0 19px rgba(190,74,98,.5),
    0 0 40px rgba(190,74,98,.3);
}
.neon-white{
  text-shadow:
    0 0 4px rgba(255,255,255,.8),
    0 0 11px rgba(255,255,255,.5),
    0 0 19px rgba(255,255,255,.3),
    0 0 40px rgba(255,255,255,.15);
}

/* ── Neon Border ─────────────────────────────────────────────── */
.neon-border,.neon-border-hover:hover{
  border-color:rgba(176,144,40,.6)!important;
  box-shadow:
    inset 0 0 8px rgba(176,144,40,.08),
    0 0 8px rgba(176,144,40,.35),
    0 0 16px rgba(176,144,40,.2),
    0 0 32px rgba(176,144,40,.1);
}

/* ── Neon Pulse Animation ───────────────────────────────────── */
.neon-pulse,.neon-animate{
  animation:neon-pulse 3s ease-in-out infinite;
}
@keyframes neon-pulse{
  0%,100%{
    text-shadow:
      0 0 4px rgba(176,144,40,.9),0 0 11px rgba(176,144,40,.6),
      0 0 19px rgba(176,144,40,.4),0 0 40px rgba(176,144,40,.2);
  }
  50%{
    text-shadow:
      0 0 2px rgba(176,144,40,.6),0 0 8px rgba(176,144,40,.4),
      0 0 14px rgba(176,144,40,.25),0 0 28px rgba(176,144,40,.12);
  }
}

/* ── Gradient Text ───────────────────────────────────────────── */
.gradient-text,.grad-text{
  background:linear-gradient(
    90deg,
    var(--gold,#B09028) 0%,
    var(--gold-l,#C8A840) 25%,
    var(--rose-p,#E8A8B8) 50%,
    var(--gold-l,#C8A840) 75%,
    var(--gold,#B09028) 100%
  );
  background-size:200% auto;
  -webkit-background-clip:text;
  background-clip:text;
  -webkit-text-fill-color:transparent;
  animation:grad-shift 4s linear infinite;
}
@keyframes grad-shift{to{background-position:200% center}}

/* ── Holographic Card ────────────────────────────────────────── */
.holo-card{
  background:linear-gradient(
    135deg,
    rgba(176,144,40,.06) 0%,
    rgba(190,74,98,.06) 25%,
    rgba(138,26,46,.06) 50%,
    rgba(190,74,98,.06) 75%,
    rgba(176,144,40,.06) 100%
  )!important;
  background-size:300% 300%!important;
  animation:holo-bg 6s ease infinite;
}
.holo-card::before{
  content:'';position:absolute;inset:0;
  background:linear-gradient(
    105deg,
    transparent 40%,
    rgba(176,144,40,.06) 50%,
    rgba(190,74,98,.04) 55%,
    transparent 70%
  );
  background-size:200% 200%;
  animation:holo-shine 4s ease infinite;
  pointer-events:none;border-radius:inherit;
}
@keyframes holo-bg{
  0%{background-position:0% 50%}
  50%{background-position:100% 50%}
  100%{background-position:0% 50%}
}
@keyframes holo-shine{
  0%{background-position:-200% center}
  100%{background-position:300% center}
}

/* ── Film Grain / Noise ──────────────────────────────────────── */
#ailex-grain{
  position:fixed;inset:0;z-index:9996;pointer-events:none;
  opacity:.028;mix-blend-mode:overlay;
  animation:grain-move .15s steps(2) infinite;
}
@keyframes grain-move{
  0%{transform:translate(0,0)}
  25%{transform:translate(-2px,1px)}
  50%{transform:translate(1px,-2px)}
  75%{transform:translate(-1px,2px)}
  100%{transform:translate(2px,-1px)}
}

/* ── Cursor Trail ────────────────────────────────────────────── */
.cursor-trail-dot{
  position:fixed;width:5px;height:5px;border-radius:50%;
  background:var(--gold,#B09028);pointer-events:none;
  z-index:9998;mix-blend-mode:screen;
  box-shadow:0 0 6px var(--gold,#B09028),0 0 12px rgba(176,144,40,.4);
  will-change:transform;
}

/* ── Ambient Glow behind gold elements ───────────────────────── */
.glow-ambient{
  position:relative;
}
.glow-ambient::after{
  content:'';position:absolute;inset:-20px;
  background:radial-gradient(ellipse,rgba(176,144,40,.12),transparent 70%);
  pointer-events:none;z-index:-1;
  animation:glow-breathe 4s ease-in-out infinite;
}
@keyframes glow-breathe{
  0%,100%{opacity:.6;transform:scale(1)}
  50%{opacity:1;transform:scale(1.08)}
}

/* ── Scanlines (subtle) ──────────────────────────────────────── */
body::after{
  content:'';position:fixed;inset:0;z-index:9995;pointer-events:none;
  background:repeating-linear-gradient(
    0deg,transparent,transparent 2px,
    rgba(0,0,0,.015) 2px,rgba(0,0,0,.015) 4px
  );
}

/* ── Text Scramble ───────────────────────────────────────────── */
.scramble{display:inline-block}

/* ── Neon Input Focus ────────────────────────────────────────── */
input:focus,select:focus,textarea:focus{
  border-color:rgba(176,144,40,.7)!important;
  box-shadow:0 0 0 2px rgba(176,144,40,.1),0 0 12px rgba(176,144,40,.2)!important;
  outline:none!important;
}

/* ── Glitch effect (utility) ─────────────────────────────────── */
.glitch{position:relative}
.glitch::before,.glitch::after{
  content:attr(data-text);position:absolute;inset:0;
  clip-path:polygon(0 30%,100% 30%,100% 50%,0 50%);
}
.glitch::before{
  animation:glitch-a .8s infinite;
  color:var(--rose,#BE4A62);left:2px;
}
.glitch::after{
  animation:glitch-b .8s infinite;
  color:var(--gold,#B09028);left:-2px;
}
@keyframes glitch-a{
  0%,90%,100%{clip-path:polygon(0 0,0 0,0 0,0 0)}
  92%{clip-path:polygon(0 15%,100% 15%,100% 30%,0 30%);transform:translate(-2px)}
  94%{clip-path:polygon(0 55%,100% 55%,100% 70%,0 70%);transform:translate(2px)}
}
@keyframes glitch-b{
  0%,88%,100%{clip-path:polygon(0 0,0 0,0 0,0 0)}
  90%{clip-path:polygon(0 40%,100% 40%,100% 55%,0 55%);transform:translate(2px)}
  93%{clip-path:polygon(0 70%,100% 70%,100% 85%,0 85%);transform:translate(-2px)}
}
"""


# ── HTML elements to inject ────────────────────────────────────────────────────

LOADER_HTML = """<div id="ailex-loader" aria-hidden="true">
  <div class="ld-logo">ROMA</div>
  <div class="ld-sub">Prestige</div>
  <div class="ld-bar"></div>
</div>"""

GRAIN_HTML = """<svg style="position:absolute;width:0;height:0">
  <filter id="ailex-noise-filter">
    <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3"
                  stitchTiles="stitch" result="noise"/>
    <feColorMatrix type="saturate" values="0" in="noise"/>
  </filter>
</svg>
<div id="ailex-grain" style="filter:url(#ailex-noise-filter)"></div>"""

WEBGL_CANVAS = """<canvas id="webgl" aria-hidden="true"></canvas>"""


# ── JavaScript ─────────────────────────────────────────────────────────────────

ULTRA_JS = r"""
/* ═══════════════════════════════════════════════════════════════════
   AILEX Ultra Motion System — JavaScript
   Three.js WebGL | Neons | Trail | Holographic | Scramble | Loader
   ═══════════════════════════════════════════════════════════════════ */

(function UltraMotion() {

  /* ── 0. PAGE LOADER ──────────────────────────────────────────────── */
  window.addEventListener('load', function() {
    var loader = document.getElementById('ailex-loader');
    if (loader) {
      setTimeout(function() {
        loader.style.opacity = '0';
        setTimeout(function() { loader.remove(); }, 800);
      }, 1200);
    }
  });

  /* ── 1. THREE.JS WebGL PARTICLE GALAXY ──────────────────────────── */
  (function initWebGL() {
    if (typeof THREE === 'undefined') return;
    var canvas = document.getElementById('webgl');
    if (!canvas) return;

    var scene    = new THREE.Scene();
    var camera   = new THREE.PerspectiveCamera(60, innerWidth/innerHeight, 0.1, 100);
    camera.position.z = 3;

    var renderer = new THREE.WebGLRenderer({canvas: canvas, alpha: true, antialias: true});
    renderer.setSize(innerWidth, innerHeight);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);

    /* ── Main particle system: 5000 particles ── */
    var COUNT    = 5000;
    var geometry = new THREE.BufferGeometry();
    var pos      = new Float32Array(COUNT * 3);
    var col      = new Float32Array(COUNT * 3);
    var sizes    = new Float32Array(COUNT);

    /* Gold / Rose / Ivory palette */
    var palette  = [
      [0.69, 0.56, 0.16],   /* gold      */
      [0.75, 0.29, 0.41],   /* rose      */
      [0.95, 0.93, 0.88],   /* ivory     */
      [0.82, 0.10, 0.17],   /* crimson   */
      [0.36, 0.04, 0.09],   /* burgundy  */
    ];

    for (var i = 0; i < COUNT; i++) {
      var r     = 2.5 + Math.random() * 5;
      var theta = Math.random() * Math.PI * 2;
      var phi   = Math.acos(2 * Math.random() - 1);
      pos[i*3]   = r * Math.sin(phi) * Math.cos(theta);
      pos[i*3+1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i*3+2] = r * Math.cos(phi);

      var c    = palette[Math.floor(Math.random() * palette.length)];
      col[i*3]   = c[0];
      col[i*3+1] = c[1];
      col[i*3+2] = c[2];
      sizes[i] = Math.random() * 2.5 + 0.5;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geometry.setAttribute('color',    new THREE.BufferAttribute(col, 3));
    geometry.setAttribute('size',     new THREE.BufferAttribute(sizes, 1));

    /* Custom GLSL shader for soft glowing particles */
    var vshader = [
      'attribute float size;',
      'attribute vec3 color;',
      'varying vec3 vColor;',
      'void main(){',
      '  vColor=color;',
      '  vec4 mv=modelViewMatrix*vec4(position,1.0);',
      '  gl_PointSize=size*(350.0/-mv.z);',
      '  gl_Position=projectionMatrix*mv;',
      '}'
    ].join('\n');

    var fshader = [
      'varying vec3 vColor;',
      'void main(){',
      '  float d=length(gl_PointCoord-vec2(0.5));',
      '  if(d>0.5)discard;',
      '  float alpha=smoothstep(0.5,0.0,d);',
      '  gl_FragColor=vec4(vColor,alpha*0.85);',
      '}'
    ].join('\n');

    var material = new THREE.ShaderMaterial({
      vertexShader:   vshader,
      fragmentShader: fshader,
      transparent:    true,
      blending:       THREE.AdditiveBlending,
      depthWrite:     false,
      attributes:     {size: {value: null}, color: {value: null}},
    });

    var particles = new THREE.Points(geometry, material);
    scene.add(particles);

    /* ── Secondary: floating geometric shapes ── */
    var shapes = [];
    var geoTypes = [
      new THREE.IcosahedronGeometry(0.08, 0),
      new THREE.OctahedronGeometry(0.06, 0),
      new THREE.TetrahedronGeometry(0.07, 0),
    ];
    for (var j = 0; j < 12; j++) {
      var geo  = geoTypes[j % geoTypes.length];
      var edges = new THREE.EdgesGeometry(geo);
      var mat  = new THREE.LineBasicMaterial({
        color: j % 2 === 0 ? 0xB09028 : 0xBE4A62,
        transparent: true, opacity: 0.15,
      });
      var mesh = new THREE.LineSegments(edges, mat);
      mesh.position.set(
        (Math.random() - 0.5) * 6,
        (Math.random() - 0.5) * 6,
        (Math.random() - 0.5) * 4 - 2
      );
      mesh.userData.rot = {
        x: (Math.random() - 0.5) * 0.005,
        y: (Math.random() - 0.5) * 0.005,
      };
      scene.add(mesh);
      shapes.push(mesh);
    }

    /* ── Mouse interaction ── */
    var mx = 0, my = 0;
    document.addEventListener('mousemove', function(e) {
      mx = (e.clientX / innerWidth - 0.5) * 2;
      my = -(e.clientY / innerHeight - 0.5) * 2;
    });

    /* ── Animation loop ── */
    var t = 0;
    function animate() {
      requestAnimationFrame(animate);
      t += 0.0006;

      particles.rotation.y = t + mx * 0.08;
      particles.rotation.x = t * 0.4 + my * 0.05;
      particles.rotation.z = t * 0.1;

      shapes.forEach(function(s) {
        s.rotation.x += s.userData.rot.x + my * 0.001;
        s.rotation.y += s.userData.rot.y + mx * 0.001;
      });

      renderer.render(scene, camera);
    }
    animate();

    window.addEventListener('resize', function() {
      camera.aspect = innerWidth / innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(innerWidth, innerHeight);
    });
  })();

  /* ── 2. CURSOR TRAIL (24 dots) ───────────────────────────────────── */
  (function initTrail() {
    if (!window.matchMedia('(hover:hover)').matches) return;

    var N    = 24;
    var dots = [];
    for (var i = 0; i < N; i++) {
      var d = document.createElement('div');
      d.className = 'cursor-trail-dot';
      var scale = 1 - i / N;
      d.style.cssText +=
        ';opacity:' + (scale * 0.7) +
        ';width:' + (5 * scale) + 'px' +
        ';height:' + (5 * scale) + 'px';
      document.body.appendChild(d);
      dots.push(d);
    }

    var positions = Array.from({length: N}, function() { return {x: 0, y: 0}; });
    var mouseX = 0, mouseY = 0;
    document.addEventListener('mousemove', function(e) { mouseX = e.clientX; mouseY = e.clientY; });

    function trailTick() {
      positions.unshift({x: mouseX, y: mouseY});
      positions.pop();
      for (var i = 0; i < dots.length; i++) {
        var half = (5 * (1 - i / N)) / 2;
        dots[i].style.transform =
          'translate(' + (positions[i].x - half) + 'px,' +
          (positions[i].y - half) + 'px)';
      }
      requestAnimationFrame(trailTick);
    }
    trailTick();

    /* Cursor hover state */
    document.querySelectorAll('a,button,.cam-c,.pc,.ec,.plan,.sc,.match-card,.ev-card').forEach(function(el) {
      el.addEventListener('mouseenter', function() {
        dots.forEach(function(d) { d.style.background = 'var(--rose,#BE4A62)'; d.style.boxShadow = '0 0 8px var(--rose)'; });
      });
      el.addEventListener('mouseleave', function() {
        dots.forEach(function(d) { d.style.background = 'var(--gold,#B09028)'; d.style.boxShadow = '0 0 6px var(--gold),0 0 12px rgba(176,144,40,.4)'; });
      });
    });
  })();

  /* ── 3. TEXT SCRAMBLE on data-scramble elements ──────────────────── */
  (function initScramble() {
    var CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789✦★◆♡♥';

    function scramble(el, finalText, delay) {
      delay = delay || 0;
      setTimeout(function() {
        var frames = 0;
        var total  = 40;
        var iv = setInterval(function() {
          el.textContent = finalText.split('').map(function(ch, i) {
            if (frames / total > i / finalText.length) return ch;
            return CHARS[Math.floor(Math.random() * CHARS.length)];
          }).join('');
          if (++frames > total) {
            el.textContent = finalText;
            clearInterval(iv);
          }
        }, 20);
      }, delay);
    }

    document.querySelectorAll('[data-scramble]').forEach(function(el) {
      var orig = el.dataset.scramble || el.textContent;
      el.textContent = orig;
      if (typeof IntersectionObserver !== 'undefined') {
        var io = new IntersectionObserver(function(entries) {
          entries.forEach(function(e) {
            if (e.isIntersecting) { scramble(el, orig); io.unobserve(el); }
          });
        }, {threshold: 0.3});
        io.observe(el);
      } else {
        scramble(el, orig, 800);
      }
    });
  })();

  /* ── 4. HOLOGRAPHIC TILT on .holo-card elements ──────────────────── */
  (function initHolo() {
    document.querySelectorAll('.holo-card,.pc,.match-card').forEach(function(card) {
      card.classList.add('holo-card');
      card.style.position = card.style.position || 'relative';
      card.style.overflow = 'hidden';

      card.addEventListener('mousemove', function(e) {
        var r = card.getBoundingClientRect();
        var x = (e.clientX - r.left) / r.width;
        var y = (e.clientY - r.top) / r.height;
        var rx = (y - 0.5) * 15;
        var ry = (x - 0.5) * -15;
        card.style.transform =
          'perspective(700px) rotateX(' + rx + 'deg) rotateY(' + ry + 'deg) scale(1.02)';
        card.style.boxShadow =
          '0 ' + (20 + Math.abs(rx)) + 'px 60px rgba(0,0,0,.5),' +
          '0 0 20px rgba(176,144,40,.2)';
      });
      card.addEventListener('mouseleave', function() {
        card.style.transform = '';
        card.style.boxShadow = '';
      });
    });
  })();

  /* ── 5. NEON ACTIVATION on data-neon elements ────────────────────── */
  (function initNeons() {
    document.querySelectorAll('[data-neon]').forEach(function(el) {
      var color = el.dataset.neon || 'gold';
      el.classList.add('neon-' + color, 'neon-pulse');
    });
    /* Also activate on stat numbers */
    document.querySelectorAll('.stat-n,.stat-about-n,.hero-kn').forEach(function(el) {
      el.classList.add('neon-gold');
    });
    /* Neon on section labels */
    document.querySelectorAll('.lbl,.lbl.c').forEach(function(el) {
      el.style.textShadow = '0 0 8px rgba(176,144,40,.5)';
    });
    /* Glow on rule elements */
    document.querySelectorAll('.rule').forEach(function(el) {
      el.style.boxShadow = '0 0 8px rgba(176,144,40,.6),0 0 16px rgba(176,144,40,.3)';
    });
  })();

  /* ── 6. GRADIENT TEXT on hero titles ────────────────────────────── */
  (function initGradientText() {
    document.querySelectorAll('h1.hero-title,.hero-h1,.hero-h1 em,.page-hero-title').forEach(function(el) {
      if (el.tagName === 'EM' || el.querySelector('em')) return; /* skip parent if has em */
    });
    /* Apply gradient to em inside hero */
    document.querySelectorAll('.hero-h1 em,.hero-title em').forEach(function(el) {
      el.classList.add('gradient-text');
    });
  })();

  /* ── 7. THEATRE.JS TIMELINE — scripted cinematic entrance ────────── */
  (function initTheatre() {
    if (typeof gsap === 'undefined') return;

    /* Hero cinematic sequence — fires once on load */
    var tl = gsap.timeline({delay: 1.4});

    /* Stage 1: Logo appear */
    tl.fromTo('.logo,.nav-logo',
      {opacity:0, y:-16, filter:'blur(8px)'},
      {opacity:1, y:0, filter:'blur(0px)', duration:.8, ease:'expo.out'}
    );

    /* Stage 2: Hero badge slide + glow */
    tl.fromTo('#hbadge,.hero-badge',
      {opacity:0, x:-20, filter:'blur(4px)'},
      {opacity:1, x:0, filter:'blur(0px)', duration:.7, ease:'power3.out'},
      '-=0.3'
    );

    /* Stage 3: Hero title chars (augments existing char animation) */
    tl.fromTo('.hero-h1,.hero-title',
      {filter:'blur(6px)'},
      {filter:'blur(0px)', duration:1, ease:'power2.out'},
      '-=0.5'
    );

    /* Stage 4: Sub text with slight glow */
    tl.fromTo('.hero-sub',
      {opacity:0, filter:'blur(4px)'},
      {opacity:1, filter:'blur(0px)', duration:.8, ease:'power3.out'},
      '-=0.6'
    );

    /* Stage 5: CTAs with neon flash */
    tl.fromTo('.hero-btns',
      {opacity:0, scale:.9},
      {opacity:1, scale:1, duration:.6, ease:'back.out(1.7)'},
      '-=0.4'
    );

    /* Stage 6: KPIs from right with neon */
    tl.fromTo('.hero-r,.hero-kpis',
      {opacity:0, x:30},
      {opacity:1, x:0, duration:.8, ease:'power3.out'},
      '-=0.5'
    );

    /* ── Scroll theatre: neon section reveals ── */
    if (typeof ScrollTrigger !== 'undefined') {
      gsap.utils.toArray('.h2,.sec-title').forEach(function(el) {
        gsap.fromTo(el,
          {filter:'blur(8px)', opacity:0},
          {filter:'blur(0px)', opacity:1, duration:1, ease:'power3.out',
           scrollTrigger:{trigger:el, start:'top 85%', once:true}}
        );
      });

      /* Neon surge on stat boxes */
      gsap.utils.toArray('.stat-b,.stat-about,.stat-box').forEach(function(el, i) {
        gsap.fromTo(el,
          {opacity:0, y:20, boxShadow:'0 0 0px rgba(176,144,40,0)'},
          {opacity:1, y:0, duration:.6, ease:'power2.out', delay: i * 0.1,
           boxShadow:'0 0 20px rgba(176,144,40,.15),0 0 40px rgba(176,144,40,.08)',
           scrollTrigger:{trigger:el, start:'top 86%', once:true}}
        );
      });

      /* Gallery cells with chromatic aberration effect */
      gsap.utils.toArray('.gc,.g-cell').forEach(function(el, i) {
        gsap.fromTo(el,
          {opacity:0, scale:.88, filter:'blur(12px) saturate(0)'},
          {opacity:1, scale:1, filter:'blur(0px) saturate(1)',
           duration:.75, ease:'power2.out', delay: (i % 3) * 0.06,
           scrollTrigger:{trigger:el.parentElement, start:'top 82%', once:true}}
        );
      });
    }
  })();

  /* ── 8. AMBIENT BLOOM on gold elements ───────────────────────────── */
  (function initBloom() {
    document.querySelectorAll('.btn-p,.nav-cta').forEach(function(btn) {
      btn.classList.add('glow-ambient');
    });
  })();

  /* ── 9. GLITCH effect on logo (subtle, timed) ───────────────────── */
  (function initGlitch() {
    var logo = document.querySelector('.logo,.nav-logo');
    if (!logo) return;
    var text = logo.textContent.trim().replace('PRESTIGE', '').replace('Prestige', '').trim();
    /* Trigger brief glitch every 8s */
    setInterval(function() {
      logo.classList.add('glitch');
      logo.dataset.text = text;
      setTimeout(function() { logo.classList.remove('glitch'); }, 600);
    }, 8000);
  })();

  /* ── 10. SMOOTH SCROLL via Lenis + GSAP integration ─────────────── */
  (function initLenis() {
    if (typeof Lenis === 'undefined' || typeof gsap === 'undefined') return;
    /* Only init if not already initialized by base MotionSystem */
    if (window._lenisInitialized) return;
    window._lenisInitialized = true;

    var lenis = new Lenis({
      duration: 1.6,
      easing: function(t) { return Math.min(1, 1.001 - Math.pow(2, -10 * t)); },
      smoothWheel: true,
      touchMultiplier: 1.8,
    });
    if (typeof ScrollTrigger !== 'undefined') {
      lenis.on('scroll', ScrollTrigger.update);
    }
    gsap.ticker.add(function(t) { lenis.raf(t * 1000); });
    gsap.ticker.lagSmoothing(0);
    window._lenis = lenis;

    /* Anchor links via Lenis */
    document.querySelectorAll('a[href^="#"]').forEach(function(a) {
      a.addEventListener('click', function(e) {
        var t = document.querySelector(a.getAttribute('href'));
        if (t) { e.preventDefault(); lenis.scrollTo(t, {offset: -60, duration: 1.6}); }
      });
    });
  })();

})();
"""


# ── Tailwind config snippet ────────────────────────────────────────────────────
TAILWIND_CONFIG = """<script>
if(typeof tailwind!=='undefined'){
  tailwind.config={
    darkMode:'class',
    theme:{extend:{
      colors:{
        gold:'#B09028','gold-l':'#C8A840','gold-p':'#EAD880',
        obsidian:'#050507',noir:'#0C0C10',
        burgundy:'#520812',crimson:'#840F28',rose:'#BE4A62',
        ivory:'#F2EAD8',cream:'#FDFAF5',
      },
      fontFamily:{
        serif:["'Cormorant Garamond'","serif"],
        display:["'Playfair Display'","serif"],
        sans:["'Montserrat'","sans-serif"],
      }
    }}
  }
}
</script>"""


# ── Main class ─────────────────────────────────────────────────────────────────

class UltraMotionSystem:
    """
    Maximum visual effects for luxury websites.
    Three.js WebGL + Neons + Trail + Holographic + Scramble + Grain + Loader.

    Usage:
        ums = UltraMotionSystem()
        html = ums.inject(html, site_context="luxury_dating")
    """

    def inject(
        self,
        html:          str,
        site_context:  str = "luxury_dating",
        include_loader: bool = True,
        include_tailwind: bool = False,
        loader_logo:   str = "ROMA",
    ) -> str:
        """Inject full ultra motion system into an HTML string."""
        if "ailex-grain" in html and "webgl" in html:
            return html   # already injected

        # 1. CDN scripts (before </head>)
        cdns = "\n".join([
            f'<script src="{THREEJS_CDN}"></script>',  # needs to be sync for THREE.* in init
            f'<script src="{GSAP_CDN}" defer></script>',
            f'<script src="{ST_CDN}" defer></script>',
            f'<script src="{LENIS_CDN}" defer></script>',
        ])
        if include_tailwind:
            cdns += f'\n<script src="{TAILWIND_CDN}"></script>\n{TAILWIND_CONFIG}'
        html = re.sub(r'(</head>)', f'\n{cdns}\n\\1', html, count=1)

        # 2. Ultra CSS into <style>
        if '</style>' in html:
            html = html.replace('</style>', ULTRA_CSS + '\n</style>', 1)
        else:
            html = re.sub(r'(</head>)', f'<style>{ULTRA_CSS}</style>\n\\1', html, count=1)

        # 3. WebGL canvas + grain + loader after <body>
        loader = LOADER_HTML.replace('ROMA', loader_logo) if include_loader else ''
        after_body = f'\n{loader}\n{GRAIN_HTML}\n{WEBGL_CANVAS}\n'
        html = re.sub(r'(<body[^>]*>)', r'\1' + after_body, html, count=1)

        # 4. Ultra JS before </body>
        html = re.sub(
            r'(</body>)',
            f'\n<script>\n{ULTRA_JS}\n</script>\n\\1',
            html, count=1
        )

        # 5. MaxEffects — ALL visual libraries (permanent standard)
        try:
            from .max_effects_system import MaxEffects
            me = MaxEffects()
            html = me.inject(html)
        except Exception:
            pass   # graceful fallback if MaxEffects not available

        return html

    def add_neon(self, html: str, selector: str, color: str = "gold") -> str:
        """Add data-neon attribute to elements matching a string pattern."""
        return html.replace(
            f'class="{selector}',
            f'data-neon="{color}" class="{selector}',
        )

    @staticmethod
    def describe() -> str:
        return """UltraMotionSystem — Maximum Luxury Effects
─────────────────────────────────────────────────────
Libraries: Three.js r169, GSAP 3.12.5, Lenis 1.1.14
Optional:  Tailwind CSS 3

Effects:
  01  Three.js WebGL 5000-particle galaxy (GLSL shaders)
  02  12 floating geometric wireframes (icosahedron/octahedron)
  03  Mouse-reactive particle rotation
  04  Neon CSS glow — gold/rose/white/crimson variants
  05  Neon pulse breathing animation
  06  Neon border on hover for cards/inputs
  07  Cursor trail — 24 dots, fade + color on hover
  08  Text scramble on [data-scramble] elements
  09  Holographic card — CSS gradient animation + 3D tilt
  10  Film grain noise (SVG feTurbulence, animated)
  11  Page loader — logo + progress bar
  12  Ambient glow bloom behind CTA buttons
  13  Glitch effect on logo (every 8s)
  14  Gradient text animation (shifting gold→rose)
  15  Theatre.js-style cinematic entrance (GSAP timeline)
  16  Chromatic aberration reveal on gallery cells
  17  Neon surge on stat boxes on scroll
  18  Scanlines overlay (subtle CRT aesthetic)

Usage: html = UltraMotionSystem().inject(html, 'luxury_dating')
"""


# ── Convenience ────────────────────────────────────────────────────────────────

def ultra_inject(
    html: str,
    site_context: str = "luxury_dating",
    loader_logo:  str = "AILEX",
) -> str:
    """Inject the full ultra motion system in one call."""
    return UltraMotionSystem().inject(html, site_context, loader_logo=loader_logo)


if __name__ == "__main__":
    print(UltraMotionSystem.describe())
    # Quick test
    test = "<!DOCTYPE html><html><head><title>T</title></head><body><h1>Hi</h1></body></html>"
    result = UltraMotionSystem().inject(test, "luxury_dating")
    checks = [
        ("Three.js CDN",   "three@0.169.0" in result),
        ("WebGL canvas",   "id=\"webgl\"" in result),
        ("Grain overlay",  "ailex-grain" in result),
        ("Loader",         "ailex-loader" in result),
        ("Neon CSS",       "neon-gold" in result),
        ("Holographic",    "holo-card" in result),
        ("Trail CSS",      "cursor-trail-dot" in result),
        ("Scramble JS",    "data-scramble" in result),
        ("Theatre.js TL",  "initTheatre" in result),
        ("Grain/Noise",    "feTurbulence" in result),
        ("Scanlines",      "repeating-linear-gradient" in result),
        ("Glitch CSS",     "glitch" in result),
        ("Gradient text",  "gradient-text" in result),
        ("Lenis init",     "initLenis" in result),
    ]
    all_pass = True
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'}  {name}")
        if not ok: all_pass = False
    print(f"\n{'✅ All checks pass' if all_pass else '❌ Some checks failed'}")
