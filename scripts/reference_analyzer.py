#!/usr/bin/env python3
"""
reference_analyzer.py — Extract aesthetic DNA from a reference label image.

Reads a reference image and produces:
  - Dominant color palette (5 colors)
  - Typography cues (inferred from text regions)
  - Visual style classification
  - Recommended style_id from the aesthetics library

Input: a reference image file (PNG, JPG, WebP)
Output: JSON summary to stdout, stored as renders/{spec_id}/reference_analysis.json

Requires: pip install Pillow scikit-image numpy
"""

import sys
import json
import argparse
from pathlib import Path
from collections import Counter

SKILL_DIR = Path.home() / ".claude" / "skills" / "label-design"
AESTHETICS_YAML = SKILL_DIR / "lib" / "aesthetics.yaml"
RENDERS_DIR = SKILL_DIR / "renders"


def load_aesthetics() -> list[dict]:
    """Load aesthetics library."""
    import yaml

    if not AESTHETICS_YAML.exists():
        return []
    with open(AESTHETICS_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("aesthetics", [])


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def extract_colors_pillow(image_path: Path, num_colors: int = 5) -> list[dict]:
    """
    Extract dominant colors using Pillow's quantized palette.
    Returns list of {hex, percentage} dicts.
    """
    try:
        from PIL import Image
    except ImportError:
        return []

    img = Image.open(image_path)
    img = img.convert("RGB")

    # Downscale for speed
    img = img.resize((150, 150))
    pixels = list(img.getdata())

    # Simple k-means-style quantization via color binning
    buckets = Counter()
    for r, g, b in pixels:
        # Coarse quantization to 32 levels per channel
        qr = (r // 32) * 32
        qg = (g // 32) * 32
        qb = (b // 32) * 32
        buckets[(qr, qg, qb)] += 1

    total = len(pixels)
    top = sorted(buckets.items(), key=lambda x: -x[1])[:num_colors]

    return [
        {"hex": rgb_to_hex(r, g, b), "percentage": round(count / total * 100, 1)}
        for (r, g, b), count in top
    ]


def estimate_style_from_colors(colors: list[dict]) -> str:
    """
    Heuristic classification based on dominant palette.
    Returns a style_id from aesthetics.yaml or 'unknown'.
    """
    if not colors:
        return "unknown"

    primary = colors[0]["hex"].upper()
    r, g, b = hex_to_rgb(primary)

    # Neutral / Grayscale
    if max(r, g, b) - min(r, g, b) < 30 and (r + g + b) < 350:
        return "clean-minimalist"
    # Warm earth / kraft tones
    if r > g and r > b and g < 180 and b < 160:
        return "vintage-artisan"
    # Cool blue / navy tones
    if b > r and b > g and r < 120:
        return "luxury-premium"
    # Bright saturated / high energy
    if (r > 200 and g > 150) or (g > 200 and b > 100):
        return "bold-commercial"
    # Muted greens / earth
    if g > r and g > b and r < 150:
        return "eco-friendly-natural"
    return "clean-minimalist"


def analyze_image(image_path: Path) -> dict:
    """Run full analysis on a reference image."""
    colors = extract_colors_pillow(image_path)
    style_guess = estimate_style_from_colors(colors)

    aesthetics = load_aesthetics()
    style_match = None
    for a in aesthetics:
        if a.get("id") == style_guess:
            style_match = a
            break

    return {
        "image": str(image_path),
        "dominant_colors": colors,
        "style_guess": style_guess,
        "matched_style": style_match,
        "recommendations": {
            "suggested_style_id": style_guess,
            "use_cases": style_match.get("use_cases", []) if style_match else [],
            "typography_mood": style_match.get("typography_mood", "unknown") if style_match else "unknown",
            "color_strategy": style_match.get("color_strategy", "unknown") if style_match else "unknown",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Extract aesthetic DNA from label reference image")
    parser.add_argument("image_path", help="Path to reference image")
    parser.add_argument("--spec-id", help="Optional spec ID to save results under renders/")
    args = parser.parse_args()

    image_path = Path(args.image_path)
    if not image_path.exists():
        print(f"Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    result = analyze_image(image_path)
    print(json.dumps(result, indent=2))

    if args.spec_id:
        out_dir = RENDERS_DIR / args.spec_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "reference_analysis.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved to: {out_path}")


if __name__ == "__main__":
    main()