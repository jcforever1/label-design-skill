#!/usr/bin/env python3
"""
render_micrographics.py — Premium micro-detail layer for product labels.

Adds small-scale visual information: micro-text strips, grid marks, alignment
ticks, border ornaments, coordinate labels, batch-style markers, data strips,
and precision details that make simple label designs feel more premium,
technical, and intentional.

Used as a supporting design layer only — must never reduce readability,
regulatory clarity, nutrition accuracy, barcode scannability, or print quality.
"""

from __future__ import annotations

import re
from typing import Literal

# ---------------------------------------------------------------------------
# Safety Allowlist
# ---------------------------------------------------------------------------
# Micrographics text must match one of these patterns. Nothing else is allowed.
# This prevents fake regulatory data, fake certifications, fake barcodes, etc.

PLACEHOLDER_PATTERNS: list[re.Pattern] = [
    # Batch / lot markers
    re.compile(r"^BATCH NO\.?\s*_+$", re.IGNORECASE),
    re.compile(r"^LOT:?\s*_+$", re.IGNORECASE),
    re.compile(r"^REF:?\s*_+$", re.IGNORECASE),
    re.compile(r"^MFD:?\s*_+$", re.IGNORECASE),
    re.compile(r"^DATE:?\s*_+$", re.IGNORECASE),
    re.compile(r"^SERIAL:?\s*_+$", re.IGNORECASE),
    re.compile(r"^CERT:?\s*_+$", re.IGNORECASE),
    re.compile(r"^PROD-ID:?\s*_+$", re.IGNORECASE),
    # Decorative / functional microcopy
    re.compile(r"^SCAN FOR DETAILS$", re.IGNORECASE),
    re.compile(r"^NET WT AREA$", re.IGNORECASE),
    re.compile(r"^QUALITY CHECKPOINT$", re.IGNORECASE),
    re.compile(r"^PRINT SAFE ZONE$", re.IGNORECASE),
    re.compile(r"^FORMULA INDEX$", re.IGNORECASE),
    re.compile(r"^ORIGIN: USER PROVIDED$", re.IGNORECASE),
    re.compile(r"^FLAVOR CODE: USER PROVIDED$", re.IGNORECASE),
    re.compile(r"^INGREDIENT INDEX$", re.IGNORECASE),
    re.compile(r"^ALLERGEN KEY$", re.IGNORECASE),
    re.compile(r"^STORAGE GUIDE$", re.IGNORECASE),
    re.compile(r"^RECYCLE SYMBOL$", re.IGNORECASE),
    re.compile(r"^PRINT TEST$", re.IGNORECASE),
    re.compile(r"^EDITION\s+\d+$", re.IGNORECASE),
    re.compile(r"^COORD: [_X\d.,\-]+$", re.IGNORECASE),
    # Registration / alignment marks
    re.compile(r"^\+\s*$"),  # registration cross
    re.compile(r"^[\.\-□▣]+$"),  # tick sequences / grid dots
    re.compile(r"^[─━│┃]+$"),  # fine-line dividers
]

# Blocked patterns — anything matching these is rejected regardless of allowlist.
BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(FDA|USDA|EPA|TTB|ASIC|CLINICAL|TRIAL|PROVEN|MEDICAL|APPROVED|CERTIFIED|REGISTERED)\b", re.IGNORECASE),
    re.compile(r"\b(BARCODE|ITEM\s*NO\.?|ARTICLE\s*NO\.?|GTIN|UPC|EAN)\s*:\s*\d", re.IGNORECASE),
    re.compile(r"\b(NDC|DRUG\s*NO\.?|RX|DEA\s*NO\.?)\b", re.IGNORECASE),
    re.compile(r"\b(LAB|RESULTS?|STUDY|PROVEN|EFFICACY)\b", re.IGNORECASE),
    re.compile(r"\b(ORGANIC|KOSHER|HALAL|FAIR\s*TRADE)\s*(CERTIFIED|APPROVED|REGISTERED)", re.IGNORECASE),
]


def _safe_text(text: str) -> bool:
    """Return True if text is safe for micrographics use (allowlist + blocklist check)."""
    if not text or len(text.strip()) == 0:
        return False
    # Blocklist first — reject obviously dangerous content
    for pat in BLOCKED_PATTERNS:
        if pat.search(text.strip()):
            return False
    # Allowlist — must match at least one pattern
    for pat in PLACEHOLDER_PATTERNS:
        if pat.match(text.strip()):
            return True
    return False


# ---------------------------------------------------------------------------
# Density presets
# ---------------------------------------------------------------------------

def _build_border_ornament(w: float, h: float, density: str) -> str:
    """Generate SVG border ornament group. density: 'minimal' | 'standard' | 'premium'."""
    segments: list[str] = []
    stroke = "currentColor"
    sw_minor = 0.25  # fine ticks
    sw_major = 0.5   # heavier border marks

    if density == "minimal":
        # Corner ticks only
        tick = 8
        for cx, cy in [(0, 0), (w, 0), (0, h), (w, h)]:
            dx = 1 if cx == 0 else -1
            dy = 1 if cy == 0 else -1
            segments.append(
                f'<path d="M{cx:.2f},{cy + dy*tick:.2f} L{cx:.2f},{cy:.2f} L{cx + dx*tick:.2f},{cy:.2f}" '
                f'stroke="{stroke}" stroke-width="{sw_minor}" fill="none"/>'
            )
    elif density in ("standard", "premium"):
        # Border ticks + registration marks
        tick = 10
        # Top/bottom edge ticks
        for x in range(int(w * 0.1), int(w), max(1, int(w * 0.05))):
            segments.append(
                f'<line x1="{x:.2f}" y1="0" x2="{x:.2f}" y2="{tick:.2f}" '
                f'stroke="{stroke}" stroke-width="{sw_minor}"/>'
            )
            segments.append(
                f'<line x1="{x:.2f}" y1="{h:.2f}" x2="{x:.2f}" y2="{h - tick:.2f}" '
                f'stroke="{stroke}" stroke-width="{sw_minor}"/>'
            )
        # Left/right edge ticks
        for y in range(int(h * 0.1), int(h), max(1, int(h * 0.05))):
            segments.append(
                f'<line x1="0" y1="{y:.2f}" x2="{tick:.2f}" y1="{y:.2f}" x2="{tick:.2f}" '
                f'stroke="{stroke}" stroke-width="{sw_minor}"/>'
            )
            segments.append(
                f'<line x1="{w:.2f}" y1="{y:.2f}" x2="{w - tick:.2f}" y2="{y:.2f}" '
                f'stroke="{stroke}" stroke-width="{sw_minor}"/>'
            )
        # Registration crosses at corners and midpoints
        cross_locs = [
            (w * 0.25, h * 0.25), (w * 0.75, h * 0.25),
            (w * 0.25, h * 0.75), (w * 0.75, h * 0.75),
            (w * 0.5, h * 0.5),
        ]
        cs = 6  # cross size
        for cx, cy in cross_locs:
            segments.append(
                f'<path d="M{cx - cs:.2f},{cy:.2f} L{cx + cs:.2f},{cy:.2f} '
                f'M{cx:.2f},{cy - cs:.2f} L{cx:.2f},{cy + cs:.2f}" '
                f'stroke="{stroke}" stroke-width="{sw_minor}" fill="none"/>'
            )

    return "\n    ".join(segments)


def _build_microtext_strip(texts: list[str], w: float, y: float,
                           font_size: float, color: str) -> str:
    """Build a horizontal microtext strip at given y-position."""
    if not texts:
        return ""
    combined = "  ·  ".join(t.upper() for t in texts if _safe_text(t))
    if not combined:
        return ""
    return (
        f'<text x="{w/2:.2f}" y="{y:.2f}" '
        f'text-anchor="middle" font-size="{font_size}" '
        f'fill="{color}" letter-spacing="2" '
        f'font-family="Helvetica, Arial, sans-serif">'
        f"{combined}</text>"
    )


def _build_grid_overlay(w: float, h: float, density: str) -> str:
    """Generate faint grid marks for premium density only."""
    if density != "premium":
        return ""
    lines: list[str] = []
    spacing = 36.0  # every 0.5 inch
    stroke = "currentColor"
    sw = 0.15
    for x in range(int(0), int(w), int(spacing)):
        lines.append(f'<line x1="{x:.2f}" y1="0" x2="{x:.2f}" y2="{h:.2f}" stroke="{stroke}" stroke-width="{sw}" opacity="0.15"/>')
    for yi in range(int(0), int(h), int(spacing)):
        lines.append(f'<line x1="0" y1="{yi:.2f}" x2="{w:.2f}" y2="{yi:.2f}" stroke="{stroke}" stroke-width="{sw}" opacity="0.15"/>')
    return "\n    ".join(lines)


def _build_data_strip(content: str, x: float, y: float,
                      w: float, font_size: float, color: str) -> str:
    """Build a small data-strip rectangle with microcopy."""
    if not _safe_text(content):
        return ""
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{font_size * 1.8:.2f}" '
        f'fill="none" stroke="{color}" stroke-width="0.3" opacity="0.4"/>'
        f'<text x="{x + w/2:.2f}" y="{y + font_size * 1.3:.2f}" '
        f'text-anchor="middle" font-size="{font_size}" fill="{color}" '
        f'font-family="Helvetica, Arial, sans-serif" opacity="0.6">'
        f"{content.upper()}</text>"
    )


# ---------------------------------------------------------------------------
# Main layer builder
# ---------------------------------------------------------------------------

def render_micrographics_layer(
    spec: dict,
    trim_w: float,
    trim_h: float,
    bleed: float,
    artboard_w: float,
    artboard_h: float,
) -> str:
    """
    Generate SVG micrographics layer as a <g> group.

    Driven by ``spec.get("micrographics", {})``:
        level     — "none" | "minimal" | "standard" | "premium"
        placement — "corner" | "border" | "background" | "header" | "footer"
        texts     — list of safe placeholder strings to use in microtext strips

    Returns empty string if level is "none" or if spec is missing micrographics key.
    """
    mg = spec.get("micrographics", {})
    level = mg.get("level", "none")
    if level == "none":
        return ""

    placement = mg.get("placement", "border")
    micro_texts: list[str] = mg.get("texts", [])
    color = mg.get("color", "#888888")

    # Clamp trim area (inside bleed)
    tx = bleed
    ty = bleed
    tw = trim_w
    th = trim_h

    groups: list[str] = []
    group_id = f' micrographics-level="{level}"'

    # --- Border ornament (all levels) ---
    if placement in ("border", "corner", "background"):
        groups.append(
            f'<g id="micrographics-border" stroke="{color}" opacity="0.5"{group_id}>'
            f"    {_build_border_ornament(tw, th, level)}"
            f"</g>"
        )

    # --- Microtext strips ---
    if placement in ("header", "footer", "background") and micro_texts:
        fs = 4.5  # micro font size
        strip_h = fs * 2.5
        if placement == "header":
            y_strip = ty + strip_h / 2
            groups.append(
                f'<g id="micrographics-header-strip" fill="{color}" opacity="0.6"{group_id}>'
                f"    {_build_microtext_strip(micro_texts, tw, y_strip, fs, color)}"
                f"</g>"
            )
        elif placement == "footer":
            y_strip = ty + th - strip_h / 2
            groups.append(
                f'<g id="micrographics-footer-strip" fill="{color}" opacity="0.6"{group_id}>'
                f"    {_build_microtext_strip(micro_texts, tw, y_strip, fs, color)}"
                f"</g>"
            )
        else:  # background — place at top and bottom
            y_top = ty + strip_h / 2
            y_bot = ty + th - strip_h / 2
            groups.append(
                f'<g id="micrographics-bg-strips" fill="{color}" opacity="0.5"{group_id}>'
                f"    {_build_microtext_strip(micro_texts[:3], tw, y_top, fs, color)}"
                f"    {_build_microtext_strip(micro_texts[3:6], tw, y_bot, fs, color)}"
                f"</g>"
            )

    # --- Corner data strips (standard + premium) ---
    if placement in ("corner", "footer") and level in ("standard", "premium"):
        strip_w = 54.0
        strip_h = 9.0
        fs = 3.5
        # Bottom-left: BATCH NO. _____
        groups.append(
            f'<g id="micrographics-corner-bl" fill="{color}" opacity="0.5"{group_id}>'
            f"    {_build_data_strip('BATCH NO. _____', tx + 4, ty + th - strip_h - 4, strip_w, fs, color)}"
            f"</g>"
        )
        # Bottom-right: LOT: _____
        groups.append(
            f'<g id="micrographics-corner-br" fill="{color}" opacity="0.5"{group_id}>'
            f"    {_build_data_strip('LOT: _____', tx + tw - strip_w - 4, ty + th - strip_h - 4, strip_w, fs, color)}"
            f"</g>"
        )

    # --- Grid overlay (premium only) ---
    if level == "premium":
        groups.append(
            f'<g id="micrographics-grid" stroke="{color}"{group_id}>'
            f"    {_build_grid_overlay(tw, th, 'premium')}"
            f"</g>"
        )

    if not groups:
        return ""

    layer = (
        "\n  <!-- LAYER: micrographics -->\n"
        '  <g id="micrographics" level="' + level + '" placement="' + placement + '">\n'
        "    " + "\n    ".join(groups) + "\n"
        "  </g>"
    )
    return layer


# ---------------------------------------------------------------------------
# CLI (dry-run)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import yaml
    import sys

    parser = argparse.ArgumentParser(description="Render micrographics layer (dry-run)")
    parser.add_argument("spec_id", help="Spec ID to read micrographics config from")
    args = parser.parse_args()

    skill_dir = __import__("pathlib").Path.home() / ".claude" / "skills" / "label-design"
    spec_path = skill_dir / "specs" / f"{args.spec_id}.yaml"
    if not spec_path.exists():
        print(f"Spec not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    with open(spec_path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    from render_svg import spec_to_dimensions
    trim_w, trim_h, bleed, aw, ah = spec_to_dimensions(spec)

    layer = render_micrographics_layer(spec, trim_w, trim_h, bleed, aw, ah)
    print(layer if layer else "// no micrographics (level=none)")