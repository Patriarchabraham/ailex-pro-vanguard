"""
AILEX Vision — design_system.py
Extract complete design tokens from any website as JSON + CSS variables.
Generate React component library from existing site.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DesignTokens:
    source_url:   str
    colors:       Dict[str, str]    # name → hex
    typography:   Dict[str, Any]    # fonts, sizes, weights
    spacing:      List[str]         # spacing scale
    shadows:      List[str]
    radii:        List[str]         # border-radius values
    gradients:    List[str]
    animations:   List[str]
    css_vars:     str               # complete :root { } block
    json:         str               # complete token JSON
    tech_stack:   List[str]


class DesignSystemExtractor:
    """
    Extracts design tokens from any website snapshot.
    Outputs: JSON tokens + CSS custom properties.
    """

    def extract(self, snapshot: Any) -> DesignTokens:
        css = snapshot.html if hasattr(snapshot, "html") else ""
        colors    = self._extract_colors(snapshot.colors, css)
        typo      = self._extract_typography(snapshot.fonts, css)
        spacing   = self._extract_spacing(css)
        shadows   = self._extract_shadows(css)
        radii     = self._extract_radii(css)
        gradients = self._extract_gradients(css)
        anims     = self._extract_animations(css)

        tokens = {
            "source": snapshot.url,
            "colors": colors,
            "typography": typo,
            "spacing": spacing,
            "shadows": shadows,
            "radii": radii,
            "gradients": gradients,
        }
        css_vars = self._to_css_vars(colors, typo, spacing, shadows, radii)

        return DesignTokens(
            source_url=snapshot.url,
            colors=colors, typography=typo,
            spacing=spacing, shadows=shadows, radii=radii,
            gradients=gradients, animations=anims,
            css_vars=css_vars,
            json=json.dumps(tokens, indent=2),
            tech_stack=snapshot.tech_stack,
        )

    def _extract_colors(self, raw_colors: List[str], css: str) -> Dict[str, str]:
        colors: Dict[str, str] = {}
        named = {"primary": None, "secondary": None, "accent": None,
                 "bg": None, "text": None, "muted": None}

        # Use captured colors from snapshot
        for i, color in enumerate(raw_colors[:12]):
            if not color.startswith("#"):
                continue
            r, g, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
            lightness = (max(r,g,b) + min(r,g,b)) / 2 / 255
            if lightness < 0.2 and named["text"] is None:
                named["text"] = color
            elif lightness > 0.9 and named["bg"] is None:
                named["bg"] = color
            elif named["primary"] is None:
                named["primary"] = color
            elif named["secondary"] is None:
                named["secondary"] = color
            elif named["accent"] is None:
                named["accent"] = color
            colors[f"color-{i+1}"] = color

        for k, v in named.items():
            if v:
                colors[k] = v

        return colors

    def _extract_typography(self, fonts: List[str], css: str) -> Dict[str, Any]:
        sizes = list(dict.fromkeys(re.findall(r"font-size:\s*([\d.]+(?:px|rem|em))", css)))[:8]
        weights = list(dict.fromkeys(re.findall(r"font-weight:\s*(\d+|bold|normal)", css)))[:6]
        return {
            "fonts":      fonts[:4] if fonts else ["system-ui", "sans-serif"],
            "heading":    fonts[0] if fonts else "Georgia, serif",
            "body":       fonts[1] if len(fonts) > 1 else "system-ui, sans-serif",
            "sizes":      sizes or ["12px", "14px", "16px", "18px", "24px", "32px", "48px"],
            "weights":    weights or ["400", "500", "600", "700"],
            "lineHeight": "1.5",
        }

    def _extract_spacing(self, css: str) -> List[str]:
        vals = re.findall(r"(?:padding|margin|gap):\s*([\d.]+px)", css)
        unique = sorted(set(vals), key=lambda x: float(x.replace("px", "")))
        if not unique:
            return ["4px", "8px", "12px", "16px", "24px", "32px", "48px", "64px"]
        return unique[:10]

    def _extract_shadows(self, css: str) -> List[str]:
        shadows = re.findall(r"box-shadow:\s*([^;}{]+)", css)
        return list(dict.fromkeys(s.strip() for s in shadows if len(s) < 100))[:5]

    def _extract_radii(self, css: str) -> List[str]:
        radii = re.findall(r"border-radius:\s*([\d.]+(?:px|rem|%))", css)
        return list(dict.fromkeys(radii))[:6] or ["4px", "8px", "12px", "16px", "24px", "9999px"]

    def _extract_gradients(self, css: str) -> List[str]:
        grads = re.findall(r"(?:linear|radial)-gradient\([^)]+\)", css)
        return list(dict.fromkeys(grads))[:5]

    def _extract_animations(self, css: str) -> List[str]:
        anims = re.findall(r"@keyframes\s+(\w+)", css)
        return list(dict.fromkeys(anims))

    def _to_css_vars(self, colors: Dict, typo: Dict, spacing: List,
                     shadows: List, radii: List) -> str:
        lines = [":root {"]
        for k, v in colors.items():
            lines.append(f"  --{k}: {v};")
        for i, s in enumerate(spacing):
            lines.append(f"  --space-{i+1}: {s};")
        for i, r in enumerate(radii):
            lines.append(f"  --radius-{i+1}: {r};")
        for i, sh in enumerate(shadows):
            lines.append(f"  --shadow-{i+1}: {sh};")
        if typo.get("fonts"):
            lines.append(f"  --font-heading: {typo['fonts'][0]};")
            lines.append(f"  --font-body: {typo.get('body', 'system-ui')};")
        lines.append("}")
        return "\n".join(lines)


class ComponentLibraryGenerator:
    """
    Generate a React component library from an existing site's design tokens.
    Outputs: Button, Card, Input, Badge, Avatar, Section components.
    """

    def generate(self, tokens: DesignTokens, client: Any) -> str:
        """Use Claude to generate React components from extracted tokens."""
        if not client:
            return self._demo_components(tokens)

        prompt = (
            f"Generate a React + Tailwind CSS component library based on these design tokens "
            f"from {tokens.source_url}:\n\n"
            f"CSS Variables:\n{tokens.css_vars}\n\n"
            f"Tech stack: {', '.join(tokens.tech_stack)}\n\n"
            "Generate these components with exact colors/styles:\n"
            "1. Button (primary, secondary, outline variants)\n"
            "2. Card (with image, title, text, hover effect)\n"
            "3. Badge (status indicator)\n"
            "4. Avatar (circular image with fallback)\n"
            "5. Section (full-width section wrapper with heading)\n\n"
            "Use TypeScript. Return one file with all components exported."
        )
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    def _demo_components(self, tokens: DesignTokens) -> str:
        primary = tokens.colors.get("primary", "#0066ff")
        return f"""// Component library generated from {tokens.source_url}
// Primary: {primary}

export const Button = ({{ children, variant = "primary", ...props }}) => {{
  const styles = {{
    primary: "bg-[{primary}] text-white px-6 py-3 rounded-xl hover:opacity-90 transition",
    outline: "border-2 border-[{primary}] text-[{primary}] px-6 py-3 rounded-xl hover:bg-[{primary}]/10",
  }};
  return <button className={{styles[variant]}} {{...props}}>{{children}}</button>;
}};

export const Card = ({{ title, text, image, children }}) => (
  <div className="bg-white/80 backdrop-blur-md rounded-2xl shadow-lg hover:scale-[1.02] transition p-6">
    {{image && <img src={{image}} className="w-full h-48 object-cover rounded-xl mb-4" />}}
    {{title && <h3 className="font-bold text-xl mb-2">{{title}}</h3>}}
    {{text && <p className="text-gray-600">{{text}}</p>}}
    {{children}}
  </div>
);
"""
