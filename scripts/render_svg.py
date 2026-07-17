#!/usr/bin/env python3
"""
render_svg.py — Generate canonical production SVG from an approved label spec.

Produces SVG with named layer groups:
  - background
  - artwork
  - text
  - barcode
  - bleed-marks

Output: renders/{spec_id}/label.svg
"""

import sys
import yaml
from pathlib import Path

from render_micrographics import render_micrographics_layer

SKILL_DIR = Path.home() / ".claude" / "skills" / "label-design"
SPECS_DIR = SKILL_DIR / "specs"
RENDERS_DIR = SKILL_DIR / "renders"


def spec_to_dimensions(spec: dict) -> tuple[float, float, float, float]:
    """Return (trim_w, trim_h, bleed, artboard_w, artboard_h) in points (72pt/inch)."""
    label = spec.get("label", {})
    dims = label.get("dimensions", {})
    width = float(dims.get("width", 3))
    height = float(dims.get("height", 4))
    unit = dims.get("unit", "inches")
    bleed = float(label.get("bleed", 0.125))
    # Clamp bleed to 0.5 INCHES (the sane print range). The bleed field
    # is always specified in inches regardless of the dimensions.unit —
    # bleed is a print-production constant, not a dimensional measurement.
    # bleeds > 0.5" are almost always spec errors; bleeds <= 0.5" pass
    # through unchanged.
    bleed = min(bleed, 0.5)

    # Convert all dimensions to points (72pt / inch)
    if unit == "inches":
        w_pt = width * 72
        h_pt = height * 72
        b_pt = bleed * 72
    elif unit == "mm":
        w_pt = width * 72 / 25.4
        h_pt = height * 72 / 25.4
        b_pt = bleed * 72
    else:
        w_pt = width * 72
        h_pt = height * 72
        b_pt = bleed * 72

    # Artboard includes bleed
    aw = w_pt + 2 * b_pt
    ah = h_pt + 2 * b_pt
    return w_pt, h_pt, b_pt, aw, ah


def hex_to_svg_rgb(hex_color: str) -> str:
    """Convert #RRGGBB to rgb(r,g,b) for SVG."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgb({r},{g},{b})"
    return hex_color


def hex_to_cmyk(hex_color: str) -> dict:
    """Convert #RRGGBB to CMYK percentage dict for print production."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return {"c": 0, "m": 0, "y": 0, "k": 100}
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    k = 1 - max(r, g, b)
    if k == 1:
        return {"c": 0, "m": 0, "y": 0, "k": 100}
    c = (1 - r - k) / (1 - k)
    m = (1 - g - k) / (1 - k)
    y = (1 - b - k) / (1 - k)
    return {
        "c": round(c * 100),
        "m": round(m * 100),
        "y": round(y * 100),
        "k": round(k * 100),
    }


def wrap_text(text: str, max_chars_per_line: int = 25) -> list[str]:
    """Wrap long text into lines at word boundaries."""
    if not text:
        return []
    lines = []
    words = text.split()
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        if len(test_line) <= max_chars_per_line or not current_line:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def build_tspan_lines(lines: list[str], x: float, y: float,
                       font_size: int, line_height: float = 1.2) -> str:
    """Build SVG tspan elements for multi-line text."""
    if not lines:
        return ""
    first_line = lines[0]
    rest_lines = lines[1:]

    tspan = f'<tspan x="{x:.2f}" dy="0">{first_line}</tspan>'
    for line in rest_lines:
        tspan += f'\n    <tspan x="{x:.2f}" dy="{font_size * line_height:.2f}">{line}</tspan>'
    return tspan


def build_google_fonts_style(font_families: list[str]) -> str:
    """
    Generate an SVG <style> block that loads Google Fonts via CSS @import.

    Usage: inject the returned string inside the <svg> element, before any <g> layers.
    Font names with spaces should be quoted in the SVG font-family attribute
    (e.g., 'Playfair Display').
    """
    if not font_families:
        return ""
    # Build the family list for the URL (pipe-separated, spaces encoded as +)
    families_param = "+".join(f.replace(" ", "+") for f in font_families)
    google_url = (
        f"https://fonts.googleapis.com/css2?"
        f"family={families_param}&display=swap"
    )
    return (
        f"  <defs>\n"
        f"    <style type=\"text/css\">\n"
        f"      @import url('{google_url}');\n"
        f"    </style>\n"
        f"  </defs>\n"
    )


def build_svg(spec: dict, spec_id: str) -> str:
    """Build SVG string from spec."""
    label = spec.get("label", {})
    dims = label.get("dimensions", {})
    width = float(dims.get("width", 3))
    height = float(dims.get("height", 4))
    unit = dims.get("unit", "inches")
    bleed = float(label.get("bleed", 0.125))
    content = spec.get("content", {})
    color = spec.get("color_palette", {})

    # Dimensions in points
    if unit == "inches":
        w_pt, h_pt = width * 72, height * 72
        b_pt = bleed * 72
    elif unit == "mm":
        w_pt, h_pt = width * 72 / 25.4, height * 72 / 25.4
        b_pt = bleed * 72 / 25.4
    else:
        w_pt, h_pt = width * 72, height * 72
        b_pt = bleed * 72

    aw = w_pt + 2 * b_pt
    ah = h_pt + 2 * b_pt

    bg = color.get("background", "#FFFFFF")
    brand = content.get("brand", "")
    product = content.get("product", "")
    variant = content.get("variant", "")
    net_volume = content.get("net_volume", "")

    # Color palette
    primary = color.get("primary", "#1A1A1A")
    secondary = color.get("secondary", "#666666")
    text_dark = color.get("text_dark", "#1A1A1A")

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{aw/72:.3f}in" height="{ah/72:.3f}in"
     viewBox="0 0 {aw:.2f} {ah:.2f}">
  <title>{brand} — {product} Label</title>
  <desc>Generated from spec {spec_id}</desc>
{build_google_fonts_style(spec.get("typography", {}).get("families", []))}
  <!-- LAYER: background -->
  <g id="background">
    <rect x="0" y="0" width="{aw:.2f}" height="{ah:.2f}" fill="{hex_to_svg_rgb(bg)}"/>
  </g>

  <!-- LAYER: artwork -->
  <g id="artwork">
    <!-- Substrate texture suggestion (commented — enable as needed) -->
    <!-- <rect x="0" y="0" width="{aw:.2f}" height="{ah:.2f}" fill="url(#grain)" opacity="0.04"/> -->
  </g>

  <!-- LAYER: text -->
  <g id="text" font-family="Helvetica, Arial, sans-serif">
    <!-- Brand zone: top-center -->
    <text x="{aw/2:.2f}" y="{b_pt + 36:.2f}"
          text-anchor="middle" font-size="11" fill="{hex_to_svg_rgb(secondary)}"
          letter-spacing="2">
      <tspan>{brand.upper()}</tspan>
    </text>

    <!-- Product name: center (multi-line reflow) -->
    <text x="{aw/2:.2f}" y="{aw/2:.2f}"
          text-anchor="middle" font-size="22" font-weight="bold"
          fill="{hex_to_svg_rgb(text_dark)}">
      {build_tspan_lines(wrap_text(product, 22), aw/2, aw/2, 22)}
    </text>

    <!-- Variant -->
    {(f'<text x="{aw/2:.2f}" y="{aw/2 + 24:.2f}" '
       f'text-anchor="middle" font-size="12" fill="{hex_to_svg_rgb(secondary)}">{variant}</text>'
       if variant else "")}

    <!-- Net volume: bottom-left (inside safe zone) -->
    <text x="{b_pt + 12:.2f}" y="{ah - b_pt - 12:.2f}"
          font-size="9" fill="{hex_to_svg_rgb(secondary)}">
      <tspan>{net_volume}</tspan>
    </text>
  </g>

  <!-- LAYER: barcode -->
  <g id="barcode">
    <!-- Placeholder barcode visualization -->
    <rect x="{aw - b_pt - 48:.2f}" y="{ah - b_pt - 36:.2f}"
          width="36" height="24" fill="{hex_to_svg_rgb(text_dark)}"/>
    <text x="{aw - b_pt - 30:.2f}" y="{ah - b_pt - 18:.2f}"
          font-size="6" fill="{hex_to_svg_rgb(bg)}" text-anchor="middle">BARCODE</text>
  </g>

  <!-- LAYER: bleed-marks -->
  <g id="bleed-marks" stroke="{hex_to_svg_rgb(secondary)}" stroke-width="0.5" fill="none" opacity="0.5">
    <!-- Corner crop marks -->
    <path d="M {b_pt - 6:.2f} {b_pt} L {b_pt} {b_pt} L {b_pt} {b_pt - 6:.2f}"/>
    <path d="M {aw - b_pt + 6:.2f} {b_pt} L {aw - b_pt} {b_pt} L {aw - b_pt} {b_pt - 6:.2f}"/>
    <path d="M {b_pt - 6:.2f} {ah - b_pt} L {b_pt} {ah - b_pt} L {b_pt} {ah - b_pt + 6:.2f}"/>
    <path d="M {aw - b_pt + 6:.2f} {ah - b_pt} L {aw - b_pt} {ah - b_pt} L {aw - b_pt} {ah - b_pt + 6:.2f}"/>
    <!-- Trim box -->
    <rect x="{b_pt:.2f}" y="{b_pt:.2f}" width="{w_pt:.2f}" height="{h_pt:.2f}"/>
  </g>

  <!-- LAYER: micrographics -->
  <g id="micrographics">
    <!-- micrographics layer injected here -->
  </g>
</svg>"""

    layer = render_micrographics_layer(spec, w_pt, h_pt, b_pt, aw, ah)
    if layer:
        svg = svg.replace("<!-- micrographics layer injected here -->", layer)

    return svg


def _coerce_spec(spec):
    """Coerce YAML-loaded spec values to their expected scalar types.

    ``yaml.safe_load`` faithfully returns whatever the file contains, so a
    spec with ``content.brand: {a: 1}`` produces a dict where the renderer
    later calls ``.upper()`` (AttributeError), and ``label.dimensions.width:
    abc`` produces a string where the renderer calls ``float()`` (ValueError).
    Coerce each known field in place so every downstream call site sees the
    type it expects; missing keys keep their defaults (set by ``.get`` in
    ``build_svg`` / ``spec_to_dimensions``).
    """
    if not isinstance(spec, dict):
        return spec

    # Container fields are always accessed via .get(...) in build_svg /
    # render_micrographics_layer; if any of them is not a dict (e.g. a YAML
    # scalar), coerce to an empty dict so downstream calls return their
    # documented defaults instead of crashing.
    for key in ("label", "content", "color_palette", "typography", "micrographics"):
        if key in spec and not isinstance(spec[key], dict):
            spec[key] = {}

    # micrographics.level / placement are compared to and concatenated with
    # strings in render_micrographics_layer; coerce non-strings to safe defaults.
    mg = spec.get("micrographics")
    if isinstance(mg, dict):
        if "level" in mg and not isinstance(mg["level"], str):
            mg["level"] = "none"
        if "placement" in mg and not isinstance(mg["placement"], str):
            mg["placement"] = "border"
        if "color" in mg and not isinstance(mg["color"], str):
            mg["color"] = "#888888"
        if "texts" in mg:
            texts = mg["texts"]
            if isinstance(texts, list):
                mg["texts"] = [t if isinstance(t, str) else "" for t in texts]
            elif not isinstance(texts, list):
                mg["texts"] = []

    # Numeric label fields: coerce to float, fall back to a default on
    # TypeError (None / dict / list) or ValueError (non-numeric string).
    label = spec.get("label")
    if isinstance(label, dict):
        # nested container — same coercion as top-level
        if "dimensions" in label and not isinstance(label["dimensions"], dict):
            label["dimensions"] = {}
        dims = label.get("dimensions")
        if isinstance(dims, dict):
            for key, default in (("width", 3), ("height", 4)):
                if key not in dims:
                    continue
                try:
                    dims[key] = float(dims[key])
                except (TypeError, ValueError):
                    dims[key] = float(default)
            if "unit" in dims and not isinstance(dims["unit"], str):
                dims["unit"] = "inches"
        if "bleed" in label:
            try:
                float(label["bleed"])
            except (TypeError, ValueError):
                label["bleed"] = 0.125

    # Content fields must be strings: ``brand`` is fed to ``.upper()``,
    # ``product`` to ``.split()``, and the rest are interpolated into SVG.
    content = spec.get("content")
    if isinstance(content, dict):
        for key in ("brand", "product", "variant", "net_volume"):
            if key not in content:
                continue
            value = content[key]
            if not isinstance(value, str):
                content[key] = "" if value is None else str(value)

    # Color palette values are passed straight into ``hex_to_svg_rgb`` which
    # calls ``.lstrip("#")`` on them — any non-string raises ``AttributeError``.
    # Replace non-strings with the documented default; missing keys are fine
    # because ``.get`` returns those same defaults at the call site.
    color = spec.get("color_palette")
    if isinstance(color, dict):
        for key, default in (
            ("background", "#FFFFFF"),
            ("primary", "#1A1A1A"),
            ("secondary", "#666666"),
            ("text_dark", "#1A1A1A"),
        ):
            if key in color and not isinstance(color[key], str):
                color[key] = default

    # ``typography.families`` is iterated by ``build_google_fonts_style`` and
    # each element is fed to ``str.replace``; coerce non-string entries (or a
    # whole-list non-list) to a safe list of strings.
    typography = spec.get("typography")
    if isinstance(typography, dict) and "families" in typography:
        families = typography["families"]
        if isinstance(families, list):
            typography["families"] = [
                f if isinstance(f, str) else "" for f in families
            ]
        elif not isinstance(families, list):
            typography["families"] = []

    return spec


def render_svg(spec_id: str, dry_run: bool = False) -> Path | None:
    """Render spec to SVG file. Returns path or None on failure."""
    path = SPECS_DIR / f"{spec_id}.yaml"
    if not path.exists():
        print(f"Spec not found: {spec_id}", file=sys.stderr)
        return None

    with open(path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    # yaml.safe_load may return None / scalar / list if the YAML body doesn't
    # parse to a mapping; the renderer requires a dict, so coerce non-mappings
    # to an empty dict (which triggers all the documented defaults).
    if not isinstance(spec, dict):
        spec = {}

    spec = _coerce_spec(spec)

    status = spec.get("status", "draft")
    if status not in ("approved", "locked"):
        print(f"Warning: spec status is '{status}', render_svg is for approved/locked specs.", file=sys.stderr)

    out_dir = RENDERS_DIR / spec_id
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    svg_content = build_svg(spec, spec_id)

    if dry_run:
        print(svg_content)
        return None

    out_path = out_dir / "label.svg"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    return out_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Render label spec to SVG")
    parser.add_argument("spec_id", help="Spec ID")
    parser.add_argument("--dry-run", action="store_true", help="Print SVG to stdout without writing")
    args = parser.parse_args()

    path = render_svg(args.spec_id, dry_run=args.dry_run)
    if path:
        print(f"Rendered: {path}")


if __name__ == "__main__":
    main()