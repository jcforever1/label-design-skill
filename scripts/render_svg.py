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
    # Clamp bleed to a sane print range — spec values > 0.5" are likely errors
    bleed = min(bleed, 0.5)

    # Convert to points (72pt / inch)
    if unit == "inches":
        w_pt = width * 72
        h_pt = height * 72
        b_pt = bleed * 72
    elif unit == "mm":
        w_pt = width * 72 / 25.4
        h_pt = height * 72 / 25.4
        b_pt = bleed * 72 / 25.4
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


def build_svg(spec: dict, spec_id: str) -> str:
    """Build SVG string from spec."""
    label = spec.get("label", {})
    dims = label.get("dimensions", {})
    width = float(dims.get("width", 3))
    height = float(dims.get("height", 4))
    unit = dims.get("unit", "inches")
    bleed = float(label.get("bleed", 0.125))
    # Clamp bleed to a sane print range — spec values > 0.5" are likely errors
    bleed = min(bleed, 0.5)

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
          letter-spacing="2">{brand.upper()}</text>

    <!-- Product name: center -->
    <text x="{aw/2:.2f}" y="{aw/2:.2f}"
          text-anchor="middle" font-size="22" font-weight="bold"
          fill="{hex_to_svg_rgb(text_dark)}">{product}</text>

    <!-- Variant -->
    {("<text x=\"{{aw/2:.2f}}\" y=\"{{aw/2 + 24:.2f}}\" "
       "text-anchor=\"middle\" font-size=\"12\" fill=\"{{hex_to_svg_rgb(secondary)}}\">{{variant}}</text>"
       if variant else "")}

    <!-- Net volume: bottom-left (inside safe zone) -->
    <text x="{b_pt + 12:.2f}" y="{ah - b_pt - 12:.2f}"
          font-size="9" fill="{hex_to_svg_rgb(secondary)}">{net_volume}</text>
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


def render_svg(spec_id: str, dry_run: bool = False) -> Path | None:
    """Render spec to SVG file. Returns path or None on failure."""
    path = SPECS_DIR / f"{spec_id}.yaml"
    if not path.exists():
        print(f"Spec not found: {spec_id}", file=sys.stderr)
        return None

    with open(path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

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