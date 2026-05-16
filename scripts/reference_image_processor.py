#!/usr/bin/env python3
"""
reference_image_processor.py — Full reference image processing pipeline.

7-step workflow:
  1_ingest    — Accept file path, URL, or Base64.
  2_validate  — Confirm file type, size, dimensions, readability.
  3_store_copy — Save a local copy under labels/references/{spec_id}/.
  4_analyze   — Extract layout, palette, typography mood, style matches,
                micrographics, material cues, aesthetic DNA.
  5_originality_filter — Identify must-not-copy elements:
                logo, exact composition, proprietary artwork, trade dress, slogans.
  6_generate_custom_template — Create legally distinct reusable template.
  7_attach_to_spec — Store reference_analysis.yaml and link to spec.

Requires: pip install Pillow requests numpy
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKILL_DIR = Path.home() / ".claude" / "skills" / "label-design"
LABELS_DIR = SKILL_DIR / "labels"
REFERENCES_DIR = SKILL_DIR / "references"
RENDERS_DIR = SKILL_DIR / "renders"
AESTHETICS_YAML = SKILL_DIR / "lib" / "aesthetics.yaml"
STYLES_YAML = SKILL_DIR / "lib" / "styles.yaml"
ORIGINALITY_YAML = SKILL_DIR / "lib" / "originality_filters.yaml"

MAX_FILE_SIZE_MB = 10
MAX_DIMENSION_PX = 4096
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

# ---------------------------------------------------------------------------
# Step 1 — Ingest
# ---------------------------------------------------------------------------

def ingest(
    source: Literal["path", "url", "base64"],
    value: str,
) -> tuple[Path, str]:
    """
    Download / decode input to a temporary file.
    Returns (temp_path, mime_hint).
    """
    if source == "path":
        p = Path(value)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        if not p.is_file():
            raise ValueError(f"Not a file: {p}")
        # Copy to temp to normalize
        suffix = p.suffix.lower()
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(p.read_bytes())
        tmp.close()
        return Path(tmp.name), _mime_from_ext(suffix)

    elif source == "url":
        import urllib.request
        try:
            with urllib.request.urlopen(value, timeout=30) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch URL: {e}") from e

        suffix = _ext_from_mime(content_type)
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(data)
        tmp.close()
        return Path(tmp.name), content_type

    elif source == "base64":
        # Handle optional data URL prefix
        if "," in value:
            meta, data_b64 = value.split(",", 1)
        else:
            data_b64 = value
            meta = ""

        try:
            data = base64.b64decode(data_b64)
        except Exception as e:
            raise ValueError(f"Invalid Base64: {e}") from e

        # Detect mime from data URL meta or default
        mime = "image/png"
        if meta:
            m = re.search(r"data:([^;]+)", meta)
            if m:
                mime = m.group(1)

        suffix = _ext_from_mime(mime)
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(data)
        tmp.close()
        return Path(tmp.name), mime

    else:
        raise ValueError(f"Unknown source type: {source}")


def _mime_from_ext(ext: str) -> str:
    map_ = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
    }
    return map_.get(ext.lower(), "application/octet-stream")


def _ext_from_mime(mime: str) -> str:
    map_ = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/gif": ".gif",
    }
    return map_.get(mime.lower(), ".png")


# ---------------------------------------------------------------------------
# Step 2 — Validate
# ---------------------------------------------------------------------------

def validate(image_path: Path, mime_hint: str) -> dict:
    """
    Check file type, size, dimensions, readability.
    Returns a dict with fields: valid, errors (list), warnings (list), metadata.
    """
    errors: list[str] = []
    warnings: list[str] = []
    metadata: dict = {}

    # File size
    size_bytes = image_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    metadata["size_bytes"] = size_bytes
    metadata["size_mb"] = round(size_mb, 3)

    if size_mb > MAX_FILE_SIZE_MB:
        errors.append(f"File too large: {size_mb:.1f}MB (max {MAX_FILE_SIZE_MB}MB)")
    if size_mb > 5:
        warnings.append(f"Large file ({size_mb:.1f}MB). Processing may be slow.")

    # Suffix check
    if image_path.suffix.lower() not in SUPPORTED_FORMATS:
        errors.append(f"Unsupported format: {image_path.suffix}. Supported: {', '.join(SUPPORTED_FORMATS)}")

    # Image validity
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            img.verify()
        # Re-open for metadata (verify consumes the file pointer)
        with Image.open(image_path) as img:
            width, height = img.size
            metadata["width_px"] = width
            metadata["height_px"] = height
            metadata["mode"] = img.mode
            if hasattr(img, "info"):
                metadata["dpi"] = img.info.get("dpi", None)
    except Exception as e:
        errors.append(f"Cannot read image: {e}")
        return {"valid": False, "errors": errors, "warnings": warnings, "metadata": metadata}

    if metadata.get("width_px", 0) > MAX_DIMENSION_PX or metadata.get("height_px", 0) > MAX_DIMENSION_PX:
        errors.append(f"Image too large: {metadata['width_px']}x{metadata['height_px']}px (max {MAX_DIMENSION_PX}px per side)")

    if metadata.get("width_px", 0) < 50 or metadata.get("height_px", 0) < 50:
        warnings.append(f"Image very small: {metadata['width_px']}x{metadata['height_px']}px. Analysis may be unreliable.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "metadata": metadata,
    }


# ---------------------------------------------------------------------------
# Step 3 — Store copy
# ---------------------------------------------------------------------------

def store_copy(temp_path: Path, spec_id: str, source_hash: str) -> Path:
    """
    Copy image to labels/references/{spec_id}/original.{ext}.
    Creates directories as needed.
    """
    ref_dir = LABELS_DIR / "references" / spec_id
    ref_dir.mkdir(parents=True, exist_ok=True)

    suffix = temp_path.suffix.lower()
    dest = ref_dir / f"original{suffix}"

    import shutil
    shutil.copy2(temp_path, dest)
    return dest


# ---------------------------------------------------------------------------
# Step 4 — Analyze
# ---------------------------------------------------------------------------

def analyze(image_path: Path) -> dict:
    """
    Full aesthetic analysis of the reference image.
    Extracts: colors, layout, typography mood, micrographics, material cues,
    style matches, complexity level.
    """
    from collections import Counter

    try:
        from PIL import Image
    except ImportError:
        return {"error": "Pillow not installed. Run: pip install Pillow"}

    img = Image.open(image_path)
    img_rgb = img.convert("RGB")
    width, height = img.size

    # --- Colors ---
    colors = _extract_colors(img_rgb)

    # --- Layout ---
    layout = _analyze_layout(img_rgb, width, height)

    # --- Typography cues ---
    typography = _analyze_typography(img_rgb, width, height)

    # --- Micrographics ---
    micrographics = _detect_micrographics(img_rgb)

    # --- Material cues ---
    material = _infer_material(img_rgb, colors)

    # --- Style matching ---
    style_match = _match_styles(colors, layout, typography, micrographics, material)

    # --- Complexity ---
    complexity = _estimate_complexity(img_rgb)

    return {
        "dominant_colors": colors,
        "layout": layout,
        "typography_mood": typography,
        "micrographics": micrographics,
        "material_cues": material,
        "style_match": style_match,
        "complexity_level": complexity,
    }


def _extract_colors(img: "Image.Image", num_colors: int = 6) -> list[dict]:
    """Extract dominant colors using coarse quantization."""
    img_small = img.resize((120, 120))
    pixels = list(img_small.getdata())

    buckets = Counter()
    for r, g, b in pixels:
        qr = (r // 24) * 24
        qg = (g // 24) * 24
        qb = (b // 24) * 24
        buckets[(qr, qg, qb)] += 1

    total = len(pixels)
    top = sorted(buckets.items(), key=lambda x: -x[1])[:num_colors]

    result = []
    for (r, g, b), count in top:
        pct = round(count / total * 100, 1)
        hex_val = f"#{r:02x}{g:02x}{b:02x}"
        result.append({"hex": hex_val, "rgb": [r, g, b], "percentage": pct})

    return result


def _analyze_layout(img: "Image.Image", width: int, height: int) -> dict:
    """
    Infer layout structure: center-weighted, grid, asymmetric, editorial, etc.
    """
    # Downscale for edge analysis
    small = img.resize((60, 60))
    arr = list(small.getdata())

    # Check horizontal vs vertical text density
    # Row-based variance
    rows = [arr[i * 60:(i + 1) * 60] for i in range(60)]
    row_variances = []
    for row in rows:
        brightness = [sum(p) // 3 for p in row]
        row_variances.append(sum(1 for i in range(1, len(brightness))) if brightness else 0)

    aspect = width / max(height, 1)
    is_portrait = aspect < 0.8
    is_landscape = aspect > 1.25
    is_square = not is_portrait and not is_landscape

    # Center mass detection — find where content concentrates
    center_x, center_y = 30, 30
    center_rows = rows[max(0, center_y - 5):center_y + 5]
    center_variance = sum(sum(1 for p in row[max(0, center_x - 5):center_x + 5]) for row in center_rows)
    edge_rows = rows[:5] + rows[-5:]
    edge_density = sum(sum(1 for p in row) for row in edge_rows)

    if center_variance > edge_density * 1.5:
        balance = "center-weighted"
    elif edge_density > center_variance * 1.5:
        balance = "edge-weighted"
    else:
        balance = "distributed"

    # Grid detection via horizontal line frequency
    horizontal_lines = _count_horizontal_lines(arr, 60, 60)
    vertical_lines = _count_vertical_lines(arr, 60, 60)
    is_grid = horizontal_lines >= 3 or vertical_lines >= 3

    orientation = "portrait" if is_portrait else ("landscape" if is_landscape else "square")

    return {
        "orientation": orientation,
        "balance": balance,
        "grid_detected": is_grid,
        "horizontal_structures": horizontal_lines,
        "vertical_structures": vertical_lines,
    }


def _count_horizontal_lines(arr: list, w: int, h: int) -> int:
    count = 0
    threshold = 0.85
    for y in range(1, h):
        prev_row = arr[(y - 1) * w:y * w]
        curr_row = arr[y * w:(y + 1) * w]
        similar = sum(1 for i in range(w) if abs(sum(prev_row[i]) - sum(curr_row[i])) < 30)
        if similar / w > threshold:
            count += 1
    return count // 10


def _count_vertical_lines(arr: list, w: int, h: int) -> int:
    count = 0
    threshold = 0.85
    for x in range(1, w):
        col_prev = [arr[y * w + x - 1] for y in range(h)]
        col_curr = [arr[y * w + x] for y in range(h)]
        similar = sum(1 for i in range(h) if abs(sum(col_prev[i]) - sum(col_curr[i])) < 30)
        if similar / h > threshold:
            count += 1
    return count // 10


def _analyze_typography(img: "Image.Image", width: int, height: int) -> dict:
    """
    Infer typography mood from the image.
    """
    # Simple heuristics based on overall image brightness distribution
    arr = list(img.resize((80, 80)).getdata())
    brightness = [sum(p) / 3 for p in arr]

    # Contrast (high contrast = bold, low contrast = light/delicate)
    max_b, min_b = max(brightness), min(brightness)
    contrast = max_b - min_b

    # Check for heavy/dark areas (bold text)
    dark_px = sum(1 for b in brightness if b < 80)
    light_px = sum(1 for b in brightness if b > 200)
    total_px = len(brightness)

    dark_ratio = dark_px / total_px
    light_ratio = light_px / total_px

    if contrast > 150 and dark_ratio > 0.2:
        weight = "bold"
    elif contrast < 80 and light_ratio > 0.5:
        weight = "light"
    else:
        weight = "regular"

    # Serif detection via stroke width variation (simplified)
    # High edge density suggests serif or display
    edges = _edge_density(img, 40)
    if edges > 0.15:
        classification = "display"
    elif edges > 0.08:
        classification = "serif"
    else:
        classification = "sans-serif"

    # All-caps detection via uniform height of dark regions
    caps_indicator = _detect_caps(img, 40)

    return {
        "weight": weight,
        "classification": classification,
        "caps_indicator": caps_indicator,
        "contrast_score": round(contrast, 1),
        "edge_density": round(edges, 3),
    }


def _edge_density(img: "Image.Image", size: int) -> float:
    """Fraction of pixels that are edges (high local variance)."""
    small = img.resize((size, size)).convert("L")
    arr = list(small.getdata())
    w = size

    edges = 0
    for y in range(1, size - 1):
        for x in range(1, size - 1):
            i = y * w + x
            val = arr[i]
            neighbors = [
                arr[(y - 1) * w + x],
                arr[(y + 1) * w + x],
                arr[y * w + x - 1],
                arr[y * w + x + 1],
            ]
            variance = sum(abs(val - n) for n in neighbors)
            if variance > 60:
                edges += 1

    return edges / (size * size)


def _detect_caps(img: "Image.Image", size: int) -> float:
    """
    Estimate likelihood of all-caps text.
    Returns 0-1 score based on height distribution of dark regions.
    """
    small = img.resize((size, size)).convert("RGB")
    arr = list(small.getdata())
    w = size

    dark_rows = []
    for y in range(size):
        row = arr[y * w:(y + 1) * w]
        dark_count = sum(1 for px in row if sum(px) < 150)
        dark_rows.append(dark_count)

    if not dark_rows:
        return 0.0

    # Find peaks in dark row histogram
    peaks = 0
    for i in range(1, len(dark_rows) - 1):
        if dark_rows[i] > dark_rows[i - 1] and dark_rows[i] > dark_rows[i + 1]:
            if dark_rows[i] > 5:
                peaks += 1

    # More evenly spaced peaks = more likely uniform line heights (caps)
    score = min(peaks / 8.0, 1.0)
    return round(score, 2)


def _detect_micrographics(img: "Image.Image") -> dict:
    """
    Detect presence of micrographics: borders, ornamental patterns,
    registration marks, data strips, etc.
    """
    arr = list(img.resize((80, 80)).convert("L").getdata())
    w, h = 80, 80

    # Border detection: count dark pixels near edges
    border_dark = 0
    total_edge = 2 * w + 2 * h - 4
    for x in range(w):
        if arr[x] < 100:  # top row
            border_dark += 1
        if arr[(h - 1) * w + x] < 100:  # bottom row
            border_dark += 1
    for y in range(1, h - 1):
        if arr[y * w] < 100:  # left col
            border_dark += 1
        if arr[y * w + w - 1] < 100:  # right col
            border_dark += 1

    border_ratio = border_dark / max(total_edge, 1)

    # Line/rule detection via horizontal structure count
    h_lines = _count_horizontal_lines(arr, w, h)
    v_lines = _count_vertical_lines(arr, w, h)

    # Pattern detection via repetition
    pattern_score = _detect_repetition(arr, w, h)

    return {
        "has_border": border_ratio > 0.15,
        "border_strength": round(border_ratio, 3),
        "horizontal_rules": h_lines,
        "vertical_rules": v_lines,
        "pattern_score": round(pattern_score, 3),
        "has_ornaments": h_lines + v_lines > 5,
    }


def _detect_repetition(arr: list, w: int, h: int) -> float:
    """
    Score 0-1 for repetitive/patterned content.
    """
    # Row hash similarity
    row_hashes = []
    for y in range(h):
        row = arr[y * w:(y + 1) * w]
        row_hash = hashlib.md5(bytes(row)).hexdigest()[:6]
        row_hashes.append(row_hash)

    unique_rows = len(set(row_hashes))
    repetition = 1.0 - (unique_rows / max(h, 1))
    return round(repetition, 2)


def _infer_material(img: "Image.Image", colors: list[dict]) -> dict:
    """
    Infer material/substrate cues: paper, plastic, metal, glass, fabric.
    """
    arr = list(img.convert("RGB").getdata())

    # Overall brightness and saturation
    brightness = [sum(px) / 3 for px in arr]
    saturation = [max(px) - min(px) for px in arr]

    avg_brightness = sum(brightness) / len(brightness)
    avg_saturation = sum(saturation) / len(saturation)

    # Specific color checks
    first_color = colors[0]["hex"].upper() if colors else "#000000"
    r, g, b = int(first_color[1:3], 16), int(first_color[3:5], 16), int(first_color[5:7], 16)

    cues: dict[str, float] = {}

    # Matte paper: low saturation, mid brightness
    cues["matte_paper"] = round(max(0, 1 - (avg_saturation / 50) - abs(avg_brightness - 180) / 100), 2)

    # Glossy plastic: high contrast, low-mid brightness
    cues["glossy_plastic"] = round(max(0, 0.5 - avg_saturation / 80 + (200 - avg_brightness) / 200), 2)

    # Kraft/ kraft paper: warm tan/brown, low saturation
    cues["kraft_natural"] = round(max(0, 1 - abs(r - 180) / 60 - abs(g - 140) / 40 - abs(b - 90) / 60 - avg_saturation / 40), 2)

    # Metallic foil: very low saturation, high brightness OR very dark
    cues["metallic_foil"] = round(max(0, (1 - avg_saturation / 30) * (1 - abs(avg_brightness - 180) / 80)), 2)

    # Glass: very high brightness, low saturation, high contrast
    cues["glass"] = round(max(0, (avg_brightness / 255) * (1 - avg_saturation / 30) * 0.8), 2)

    # Fabric: moderate saturation, textured (high variance)
    brightness_vals = [abs(b - avg_brightness) for b in brightness]
    texture = sum(brightness_vals) / len(brightness_vals)
    cues["fabric"] = round(max(0, min(1, (1 - abs(avg_saturation - 40) / 30) * min(texture / 40, 1))), 2)

    best = max(cues.items(), key=lambda x: x[1])

    return {
        "primary_material": best[0],
        "confidence": best[1],
        "all_cues": {k: round(v, 2) for k, v in sorted(cues.items(), key=lambda x: -x[1])},
    }


def _match_styles(
    colors: list[dict],
    layout: dict,
    typography: dict,
    micrographics: dict,
    material: dict,
) -> list[dict]:
    """
    Score all styles from styles.yaml against extracted features.
    Return top 3 matches.
    """
    import yaml

    if not STYLES_YAML.exists():
        return []

    with open(STYLES_YAML, encoding="utf-8") as f:
        styles_data = yaml.safe_load(f)

    styles: list[dict] = styles_data.get("styles", [])

    def score_style(s: dict) -> float:
        score = 0.0

        # Color score
        if colors:
            primary_hex = colors[0]["hex"].upper()
            palette = s.get("color_palette_hint", "").lower()
            if primary_hex in palette or any(c["hex"].upper() in palette for c in colors[:3]):
                score += 0.3

        # Layout score
        if layout.get("grid_detected") and "grid" in s.get("description", "").lower():
            score += 0.2
        if layout.get("balance") == "center-weighted" and "minimal" in s.get("description", "").lower():
            score += 0.15

        # Typography score
        ty_weight = typography.get("weight", "")
        ty_class = typography.get("classification", "")
        if ty_weight == "bold" and "bold" in s.get("description", "").lower():
            score += 0.15
        if ty_class == "serif" and "serif" in s.get("description", "").lower():
            score += 0.2
        if ty_class == "sans-serif" and "sans" in s.get("description", "").lower():
            score += 0.15

        # Micrographics score
        if micrographics.get("has_border") and "border" in s.get("description", "").lower():
            score += 0.15
        if micrographics.get("has_ornaments") and ("ornament" in s.get("description", "").lower() or "artisan" in s.get("description", "").lower()):
            score += 0.2

        # Material score
        mat = material.get("primary_material", "")
        mat_related = {
            "kraft_natural": ["kraft", "natural", "organic", "eco"],
            "matte_paper": ["matte", "natural", "minimal"],
            "glossy_plastic": ["glossy", "plastic", "modern"],
            "metallic_foil": ["metallic", "luxury", "premium"],
            "glass": ["glass", "transparent", "premium"],
        }
        for cue_mat, keywords in mat_related.items():
            if cue_mat == mat and any(k in s.get("description", "").lower() for k in keywords):
                score += 0.2
                break

        return round(score, 2)

    scored = [(s, score_style(s)) for s in styles]
    scored.sort(key=lambda x: -x[1])

    return [
        {
            "style_id": s.get("id"),
            "name": s.get("name"),
            "score": sc,
            "description": s.get("description", "")[:80],
        }
        for s, sc in scored[:3] if sc > 0
    ]


def _estimate_complexity(img: "Image.Image") -> str:
    """
    Estimate visual complexity: minimal, standard, premium.
    """
    arr = list(img.resize((60, 60)).convert("L").getdata())

    # Count distinct gray levels
    unique = len(set(arr))
    # Count edge density
    edges = _edge_density(img, 60)
    # Count color variety via downscaled color count
    color_count = len(_extract_colors(img, 8))

    score = (unique / 255) * 0.3 + edges * 2 + (color_count / 8) * 0.3

    if score < 0.8:
        return "minimal"
    elif score < 1.5:
        return "standard"
    else:
        return "premium"


# ---------------------------------------------------------------------------
# Step 5 — Originality Filter
# ---------------------------------------------------------------------------

def load_originality_rules() -> dict:
    """Load must-not-copy pattern rules."""
    if not ORIGINALITY_YAML.exists():
        return {"rules": []}
    import yaml
    with open(ORIGINALITY_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def apply_originality_filter(analysis: dict, image_path: Path) -> dict:
    """
    Flag elements that should not be copied: logos, specific compositions,
    trade dress, slogans, etc.
    """
    flags: list[dict] = []
    rules_data = load_originality_rules()
    rules: list[dict] = rules_data.get("rules", [])

    for rule in rules:
        if _check_rule(rule, analysis):
            flags.append({
                "rule_id": rule.get("id"),
                "category": rule.get("category"),
                "message": rule.get("message"),
                "severity": rule.get("severity", "warn"),
            })

    # Heuristic flags (always applied)
    colors = analysis.get("dominant_colors", [])
    if len(colors) >= 3:
        # Check for very saturated bright colors (common in logo-heavy designs)
        saturated = [c for c in colors if (max(c["rgb"]) - min(c["rgb"])) > 150]
        if len(saturated) >= 2:
            flags.append({
                "rule_id": "heuristic_high_saturation_logo_colors",
                "category": "proprietary_colors",
                "message": "High-saturation color pair detected — likely brand colors. Do not replicate exact palette.",
                "severity": "warn",
            })

    # All-caps with high contrast often = brand name / logo text
    ty = analysis.get("typography_mood", {})
    if ty.get("caps_indicator", 0) > 0.7 and ty.get("weight") == "bold":
        flags.append({
            "rule_id": "heuristic_bold_caps_logo_text",
            "category": "logo_text",
            "message": "Bold all-caps detected — may be a brand name or logo. Do not replicate typography.",
            "severity": "warn",
        })

    # Center-weighted with a single dominant element often = logo composition
    layout = analysis.get("layout", {})
    if layout.get("balance") == "center-weighted" and layout.get("orientation") != "portrait":
        flags.append({
            "rule_id": "heuristic_center_logo_composition",
            "category": "composition",
            "message": "Center-weighted composition detected — may include logo or focal artwork. Extract layout principles only, not exact placement.",
            "severity": "info",
        })

    return {
        "flags": flags,
        "passed": all(f.get("severity") != "block" for f in flags),
        "copy_restrictions": [
            {"category": f["category"], "guidance": f["message"]}
            for f in flags
        ],
    }


def _check_rule(rule: dict, analysis: dict) -> bool:
    """Check if a specific rule applies to this analysis."""
    rule_type = rule.get("type")
    condition = rule.get("condition", {})

    if rule_type == "color_match":
        colors = analysis.get("dominant_colors", [])
        target_hex = condition.get("hex", "").upper()
        threshold = condition.get("threshold", 20)
        for c in colors:
            r1, g1, b1 = c["rgb"]
            r2 = int(target_hex[1:3], 16)
            g2 = int(target_hex[3:5], 16)
            b2 = int(target_hex[5:7], 16)
            dist = ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b2 - b2) ** 2) ** 0.5
            if dist < threshold:
                return True
    return False


# ---------------------------------------------------------------------------
# Step 6 — Generate Custom Template
# ---------------------------------------------------------------------------

def generate_template(
    analysis: dict,
    spec_id: str,
    template_name: str,
) -> dict:
    """
    Generate a new reusable template YAML inspired by the reference,
    but legally distinct. Strips proprietary elements, keeps aesthetic DNA.
    """
    colors = analysis.get("dominant_colors", [])
    layout = analysis.get("layout", {})
    typography = analysis.get("typography_mood", {})
    material = analysis.get("material_cues", {})
    style_matches = analysis.get("style_match", [])
    complexity = analysis.get("complexity_level", "standard")
    micrographics = analysis.get("micrographics", {})

    # Use top style match as baseline
    primary_style = style_matches[0] if style_matches else {"style_id": "custom", "name": "Custom"}

    # Build safe color palette (shift hues, don't copy exactly)
    safe_colors = _derive_safe_palette(colors)

    # Determine micrographics level from analysis
    if micrographics.get("has_ornaments") or micrographics.get("horizontal_rules", 0) + micrographics.get("vertical_rules", 0) > 5:
        mg_level = "standard"
        mg_placement = "border"
    elif micrographics.get("has_border") or micrographics.get("border_strength", 0) > 0.15:
        mg_level = "subtle"
        mg_placement = "border"
    else:
        mg_level = "none"
        mg_placement = "border"

    template = {
        "template_id": template_name.lower().replace(" ", "-"),
        "spec_id": spec_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_reference": f"references/{spec_id}/original.png",
        "inspired_by": primary_style.get("name", "custom"),
        "style_id": primary_style.get("style_id", "custom"),

        "label": {
            "dimensions": {
                "width": 3.0,
                "height": 4.0,
                "unit": "inches",
            },
            "bleed": 0.125,
        },

        "color_palette": {
            "background": safe_colors[0].get("hex", "#F7F5F0") if safe_colors else "#F7F5F0",
            "primary": safe_colors[1].get("hex", "#1A1A1A") if len(safe_colors) > 1 else "#1A1A1A",
            "secondary": safe_colors[2].get("hex", "#6B7280") if len(safe_colors) > 2 else "#6B7280",
            "text_dark": "#1A1A1A",
            "accent": safe_colors[3].get("hex", "#0EA5E9") if len(safe_colors) > 3 else "#0EA5E9",
        },

        "aesthetic_style": primary_style.get("style_id", "custom"),

        "micrographics": {
            "level": mg_level,
            "placement": mg_placement,
            "color": "#888888",
        },

        "typography_mood": typography.get("classification", "sans-serif"),
        "material_cues": [material.get("primary_material", "matte_paper")],
        "complexity": complexity,

        "layout_principles": {
            "orientation": layout.get("orientation", "portrait"),
            "balance": layout.get("balance", "distributed"),
            "grid": layout.get("grid_detected", False),
        },

        "_originality_note": (
            "This template is inspired by a reference image but uses a "
            "legally distinct color palette (hues shifted), generic typography "
            "classifications, and abstracted layout principles. "
            "Do not replicate proprietary brand elements, logos, or exact color values."
        ),
    }

    return template


def _derive_safe_palette(colors: list[dict]) -> list[dict]:
    """
    Shift hue of each color slightly to create a 'legally distinct' palette.
    """
    import colorsys

    result = []
    for i, c in enumerate(colors[:5]):
        r, g, b = c["rgb"]
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

        # Rotate hue by 15-45 degrees depending on position
        hue_shift = 0.08 + (i * 0.05)
        h = (h + hue_shift) % 1.0

        # Slightly reduce saturation of highly saturated colors (likely brand colors)
        if s > 0.7:
            s = s * 0.85

        new_r, new_g, new_b = colorsys.hsv_to_rgb(h, s, v)
        new_hex = f"#{int(new_r * 255):02x}{int(new_g * 255):02x}{int(new_b * 255):02x}"
        result.append({**c, "hex": new_hex, "shifted": True})

    return result


# ---------------------------------------------------------------------------
# Step 7 — Attach to Spec
# ---------------------------------------------------------------------------

def attach_to_spec(
    spec_id: str,
    analysis: dict,
    originality: dict,
    template: dict,
    reference_copy_path: Path,
) -> Path:
    """
    Write reference_analysis.yaml and link it to the label spec.
    """
    import yaml

    ref_dir = LABELS_DIR / "references" / spec_id
    ref_dir.mkdir(parents=True, exist_ok=True)

    # Write analysis
    analysis_path = ref_dir / "reference_analysis.yaml"
    report = {
        "spec_id": spec_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_image": str(reference_copy_path),
        "analysis": analysis,
        "originality": originality,
        "generated_template": template,
    }
    with open(analysis_path, "w", encoding="utf-8") as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False)

    # Update renders dir with symlink to reference analysis
    render_dir = RENDERS_DIR / spec_id
    render_dir.mkdir(parents=True, exist_ok=True)
    analysis_link = render_dir / "reference_analysis.yaml"
    if not analysis_link.exists():
        analysis_link.symlink_to(analysis_path)

    return analysis_path


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def process_reference(
    source: Literal["path", "url", "base64"],
    value: str,
    spec_id: Optional[str] = None,
    template_name: Optional[str] = None,
    skip_template: bool = False,
) -> dict:
    """
    Full 7-step reference image processing pipeline.
    Returns a dict with all step results.
    """
    results: dict = {"steps": {}}

    # 1 — Ingest
    try:
        temp_path, mime_hint = ingest(source, value)
        results["steps"]["1_ingest"] = {"status": "ok", "temp_path": str(temp_path), "mime": mime_hint}
    except Exception as e:
        results["steps"]["1_ingest"] = {"status": "error", "message": str(e)}
        results["success"] = False
        return results

    # 2 — Validate
    validation = validate(temp_path, mime_hint)
    results["steps"]["2_validate"] = validation
    if not validation["valid"]:
        results["success"] = False
        results["summary"] = "Validation failed"
        return results

    # 3 — Store copy
    source_hash = hashlib.sha256(temp_path.read_bytes()).hexdigest()[:12]
    if spec_id is None:
        spec_id = f"ref-{source_hash}"

    ref_copy_path = store_copy(temp_path, spec_id, source_hash)
    results["steps"]["3_store_copy"] = {"status": "ok", "path": str(ref_copy_path)}
    results["spec_id"] = spec_id

    # 4 — Analyze
    analysis = analyze(temp_path)
    results["steps"]["4_analyze"] = {"status": "ok", "colors_count": len(analysis.get("dominant_colors", []))}
    results["analysis"] = analysis

    # 5 — Originality filter
    originality = apply_originality_filter(analysis, temp_path)
    results["steps"]["5_originality_filter"] = {
        "status": "ok",
        "flags_count": len(originality.get("flags", [])),
        "passed": originality.get("passed", True),
    }
    results["originality"] = originality

    # 6 — Generate template
    if skip_template:
        results["steps"]["6_generate_template"] = {"status": "skipped"}
        template = None
    else:
        if template_name is None:
            template_name = f"custom-{source_hash}"
        template = generate_template(analysis, spec_id, template_name)
        results["steps"]["6_generate_template"] = {"status": "ok", "template_id": template["template_id"]}
        results["template"] = template

    # 7 — Attach to spec
    try:
        analysis_path = attach_to_spec(spec_id, analysis, originality, template, ref_copy_path)
        results["steps"]["7_attach_to_spec"] = {"status": "ok", "path": str(analysis_path)}
    except Exception as e:
        results["steps"]["7_attach_to_spec"] = {"status": "error", "message": str(e)}

    results["success"] = True
    results["summary"] = f"Reference '{spec_id}' processed: {len(analysis.get('dominant_colors', []))} colors, complexity={analysis.get('complexity_level')}, {len(originality.get('flags', []))} originality flags"

    # Cleanup temp
    try:
        temp_path.unlink(missing_ok=True)
    except Exception:
        pass

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reference image processing pipeline (7-step workflow)")
    parser.add_argument("source", choices=["path", "url", "base64"], help="Input source type")
    parser.add_argument("value", help="File path, URL, or base64 string")
    parser.add_argument("--spec-id", help="Spec ID for storage (auto-generated if not provided)")
    parser.add_argument("--template-name", help="Name for generated template")
    parser.add_argument("--skip-template", action="store_true", help="Skip template generation")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    result = process_reference(
        source=args.source,
        value=args.value,
        spec_id=args.spec_id,
        template_name=args.template_name,
        skip_template=args.skip_template,
    )

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print("\n=== Reference Image Processing Report ===")
        print(f"Spec ID: {result.get('spec_id', 'n/a')}")
        print(f"Success: {result.get('success', False)}")
        print(f"\nSteps:")
        for step, data in result.get("steps", {}).items():
            status = data.get("status", "unknown")
            print(f"  {step}: {status}")
            if status == "error":
                print(f"    -> {data.get('message', data)}")

        analysis = result.get("analysis", {})
        if analysis:
            print(f"\nAnalysis:")
            colors = analysis.get("dominant_colors", [])
            print(f"  Colors ({len(colors)}): {[c['hex'] for c in colors[:5]]}")
            print(f"  Complexity: {analysis.get('complexity_level')}")
            print(f"  Typography: {analysis.get('typography_mood', {}).get('classification')} / {analysis.get('typography_mood', {}).get('weight')}")
            print(f"  Material: {analysis.get('material_cues', {}).get('primary_material')}")
            print(f"  Layout: {analysis.get('layout', {}).get('balance')} / {analysis.get('layout', {}).get('orientation')}")

            style = analysis.get("style_match", [])
            if style:
                print(f"  Top style match: {style[0].get('name')} ({style[0].get('score')})")

        orig = result.get("originality", {})
        flags = orig.get("flags", [])
        if flags:
            print(f"\nOriginality flags ({len(flags)}):")
            for f in flags:
                print(f"  [{f['severity']}] {f['category']}: {f['message'][:80]}")

        tmpl = result.get("template")
        if tmpl:
            print(f"\nTemplate generated: {tmpl.get('template_id')}")

        print(f"\n{result.get('summary', '')}")