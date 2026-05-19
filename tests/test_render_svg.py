#!/usr/bin/env python3
"""
tests/test_render_svg.py — Pytest suite for render_svg.py

Covers:
  - SVG structure: named layer groups (background, artwork, text, barcode, bleed-marks)
  - Color conversion: hex_to_svg_rgb, hex_to_cmyk
  - Text reflow: wrap_text, build_tspan_lines
  - Dimension math: spec_to_dimensions (inches, mm, bleed clamping)
  - Dry-run output (no file written)
"""

import sys
from pathlib import Path

# Ensure the scripts dir is on the path so imports work when running via pytest
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from render_svg import (
    spec_to_dimensions,
    hex_to_svg_rgb,
    hex_to_cmyk,
    wrap_text,
    build_tspan_lines,
    build_svg,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

_MINIMAL_SPEC = {
    "label": {
        "dimensions": {"width": 3.0, "height": 2.0, "unit": "inches"},
        "bleed": 0.125,
        "safe_zone": 0.25,
    },
    "content": {
        "brand": "Test Brand",
        "product": "Test Product",
        "variant": "Original",
        "net_volume": "Net Wt. 8 oz (227g)",
    },
    "color_palette": {
        "background": "#FFFFFF",
        "primary": "#1A1A1A",
        "secondary": "#666666",
        "text_dark": "#1A1A1A",
    },
}


# ── Color Conversion ────────────────────────────────────────────────────────

class TestHexToSvgRgb:
    def test_white(self):
        assert hex_to_svg_rgb("#FFFFFF") == "rgb(255,255,255)"

    def test_black(self):
        assert hex_to_svg_rgb("#000000") == "rgb(0,0,0)"

    def test_named_color(self):
        assert hex_to_svg_rgb("blue") == "blue"  # passthrough for named/CSS colors

    def test_no_hash(self):
        assert hex_to_svg_rgb("FF0000") == "rgb(255,0,0)"


class TestHexToCmyk:
    def test_white(self):
        result = hex_to_cmyk("#FFFFFF")
        assert result == {"c": 0, "m": 0, "y": 0, "k": 0}

    def test_black(self):
        result = hex_to_cmyk("#000000")
        assert result == {"c": 0, "m": 0, "y": 0, "k": 100}

    def test_red(self):
        result = hex_to_cmyk("#FF0000")
        assert result["c"] == 0
        assert result["m"] == 100
        assert result["y"] == 100
        assert result["k"] == 0

    def test_green(self):
        result = hex_to_cmyk("#00FF00")
        assert result["c"] == 100
        assert result["m"] == 0
        assert result["y"] == 100
        assert result["k"] == 0

    def test_blue(self):
        result = hex_to_cmyk("#0000FF")
        assert result["c"] == 100
        assert result["m"] == 100
        assert result["y"] == 0
        assert result["k"] == 0

    def test_invalid_returns_black(self):
        result = hex_to_cmyk("#GGG")
        assert result == {"c": 0, "m": 0, "y": 0, "k": 100}


# ── Dimensions ──────────────────────────────────────────────────────────────

class TestSpecToDimensions:
    def test_inches(self):
        spec = {"label": {"dimensions": {"width": 3.0, "height": 2.0, "unit": "inches"}, "bleed": 0.125}}
        w, h, b, aw, ah = spec_to_dimensions(spec)
        assert w == 3.0 * 72  # 216 pts
        assert h == 2.0 * 72  # 144 pts
        assert b == 0.125 * 72  # 9 pts
        assert aw == w + 2 * b
        assert ah == h + 2 * b

    def test_mm(self):
        spec = {"label": {"dimensions": {"width": 76.2, "height": 50.8, "unit": "mm"}, "bleed": 3.0}}
        w, h, b, aw, ah = spec_to_dimensions(spec)
        # 76.2mm = 3in; 50.8mm = 2in
        assert abs(w - 3.0 * 72) < 0.01
        assert abs(h - 2.0 * 72) < 0.01
        # bleed clamped to 0.5in
        assert b == 0.5 * 72

    def test_bleed_clamped_to_half_inch(self):
        spec = {"label": {"dimensions": {"width": 3.0, "height": 2.0}, "bleed": 2.0}}  # 2" bleed
        _, _, b, _, _ = spec_to_dimensions(spec)
        assert b == 0.5 * 72  # clamped to 0.5"


# ── Text Reflow ─────────────────────────────────────────────────────────────

class TestWrapText:
    def test_empty(self):
        assert wrap_text("") == []

    def test_short_text(self):
        assert wrap_text("Hello World", max_chars_per_line=20) == ["Hello World"]

    def test_wraps_at_boundary(self):
        lines = wrap_text("Hello World", max_chars_per_line=10)
        assert lines == ["Hello", "World"]

    def test_preserves_words(self):
        lines = wrap_text("The quick brown fox", max_chars_per_line=8)
        assert "The" in lines[0]
        assert "quick" in lines[1]


class TestBuildTspanLines:
    def test_single_line(self):
        tspan = build_tspan_lines(["Hello"], 100, 150, 12)
        assert 'x="100.00"' in tspan
        assert "Hello" in tspan

    def test_multi_line(self):
        tspan = build_tspan_lines(["Line one", "Line two"], 100, 150, 12)
        assert "Line one" in tspan
        assert "Line two" in tspan
        assert tspan.count("<tspan") == 2


# ── SVG Structure ───────────────────────────────────────────────────────────

class TestSvgStructure:
    def test_named_layer_groups_present(self):
        svg = build_svg(_MINIMAL_SPEC, "test-spec-001")
        for layer_id in ("background", "artwork", "text", "barcode", "bleed-marks", "micrographics"):
            assert f'id="{layer_id}"' in svg, f"Layer '{layer_id}' not found in SVG"

    def test_brand_in_svg(self):
        svg = build_svg(_MINIMAL_SPEC, "test-spec-001")
        assert "Test Brand" in svg

    def test_product_in_svg(self):
        svg = build_svg(_MINIMAL_SPEC, "test-spec-001")
        assert "Test Product" in svg

    def test_viewbox_set(self):
        svg = build_svg(_MINIMAL_SPEC, "test-spec-001")
        assert "viewBox=" in svg

    def test_bleed_marks_present(self):
        svg = build_svg(_MINIMAL_SPEC, "test-spec-001")
        # Trim box should be present (rect within bleed-marks group)
        assert "<rect" in svg

    def test_net_volume(self):
        svg = build_svg(_MINIMAL_SPEC, "test-spec-001")
        assert "Net Wt. 8 oz (227g)" in svg

    def test_variant_conditional(self):
        spec_with_variant = {
            **_MINIMAL_SPEC,
            "content": {**_MINIMAL_SPEC["content"], "variant": "Deluxe Edition"},
        }
        svg_with = build_svg(spec_with_variant, "test-variant")
        assert "Deluxe Edition" in svg_with

        spec_no_variant = {
            **_MINIMAL_SPEC,
            "content": {**_MINIMAL_SPEC["content"], "variant": ""},
        }
        svg_without = build_svg(spec_no_variant, "test-no-variant")
        assert "Deluxe Edition" not in svg_without