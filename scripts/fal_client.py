#!/usr/bin/env python3
"""
fal_client.py — Fal AI service layer for label generation.

Model selection based on label attributes (industry, style, complexity).
Authentication via FAL_API_KEY environment variable.

Requires: pip install fal-client
"""

import os
import sys
from pathlib import Path
from typing import Optional

SKILL_DIR = Path.home() / ".claude" / "skills" / "label-design"

# Model registry — maps (industry_complexity, style_family) to Fal AI model
# High detail / photorealistic: flux-pro, flux-ultra
# Fast / illustrative: flux-schnell, illustra
# Style-specific: flux-realism, flux-3d
MODEL_REGISTRY = {
    # Food & Beverage
    ("food_beverage", "modern_minimalist"): "fal-ai/flux-pro",
    ("food_beverage", "eco_friendly_natural"): "fal-ai/flux-pro",
    ("food_beverage", "bold_commercial"): "fal-ai/flux-ultra",
    ("food_beverage", "mediterranean"): "fal-ai/flux-realism",
    ("food_beverage", "vintage_artisan"): "fal-ai/flux-realism",
    ("food_beverage", "rustic_farmhouse"): "fal-ai/flux-realism",

    # Cosmetics & Beauty
    ("cosmetics", "luxury_premium"): "fal-ai/flux-ultra",
    ("cosmetics", "japanese_minimalism"): "fal-ai/flux-pro",
    ("cosmetics", "boutique_elegance"): "fal-ai/flux-ultra",
    ("cosmetics", "clean_medical"): "fal-ai/flux-pro",

    # Health & Supplements
    ("health_supplements", "modern_minimalist"): "fal-ai/flux-pro",
    ("health_supplements", "bold_commercial"): "fal-ai/flux-ultra",
    ("health_supplements", "tech_futuristic"): "fal-ai/flux-pro",
    ("health_supplements", "scientific_botanical"): "fal-ai/flux-realism",

    # Artisan / Crafts
    ("artisan_crafts", "vintage_artisan"): "fal-ai/flux-realism",
    ("artisan_crafts", "boho_handcrafted"): "fal-ai/flux-realism",
    ("artisan_crafts", "handcrafted"): "fal-ai/flux-realism",
    ("artisan_crafts", "cottage_core"): "fal-ai/flux-realism",

    # Electronics / Tech
    ("electronics", "tech_futuristic"): "fal-ai/flux-pro",
    ("electronics", "high_tech_industrial"): "fal-ai/flux-ultra",
    ("electronics", "soft_futurism"): "fal-ai/flux-pro",

    # Default fallback
    ("default", "default"): "fal-ai/flux-pro",
}

# Style aliases — map 25-style names to style_family keys
STYLE_ALIASES = {
    "modern_minimalist": "modern_minimalist",
    "luxury_premium": "luxury_premium",
    "eco_friendly_natural": "eco_friendly_natural",
    "bold_commercial": "bold_commercial",
    "vintage_artisan": "vintage_artisan",
    "tech_futuristic": "tech_futuristic",
    "japanese_minimalism": "japanese_minimalism",
    "scandinavian": "scandinavian",
    "mediterranean": "mediterranean",
    "art_deco": "art_deco",
    "retro_diner": "retro_diner",
    "boho_handcrafted": "boho_handcrafted",
    "high_tech_industrial": "high_tech_industrial",
    "farm_to_table": "farm_to_table",
    "boutique_elegance": "boutique_elegance",
    "street_urban": "street_urban",
    "nautical_maritime": "nautical_maritime",
    "candy_pop": "candy_pop",
    "dark_moody": "dark_moody",
    "fresh_scandinavian": "fresh_scandinavian",
    "rustic_farmhouse": "rustic_farmhouse",
    "chic_urban": "chic_urban",
    "tropical_paradise": "tropical_paradise",
    "clean_medical": "clean_medical",
    "cottage_core": "cottage_core",
    "custom": "modern_minimalist",
}

INDUSTRY_KEYS = {
    "food_beverage": "food_beverage",
    "cosmetics": "cosmetics",
    "health_supplements": "health_supplements",
    "electronics": "electronics",
    "artisan_crafts": "artisan_crafts",
    "apparel": "apparel",
    "cleaning": "cleaning",
    "default": "default",
}


def get_api_key() -> Optional[str]:
    """Read FAL_API_KEY from environment variable."""
    return os.environ.get("FAL_API_KEY") or os.environ.get("FAL_KEY")


def is_configured() -> bool:
    """True if API key is present (fal-client will validate on call)."""
    return bool(get_api_key())


def _normalize_style(style: str) -> str:
    """Normalize style name to style_family key."""
    slug = style.lower().replace("-", "_").replace(" ", "_")
    return STYLE_ALIASES.get(slug, slug if slug in STYLE_ALIASES.values() else "modern_minimalist")


def _normalize_industry(industry: str) -> str:
    """Normalize industry to industry key."""
    slug = industry.lower().replace("-", "_").replace(" ", "_")
    return INDUSTRY_KEYS.get(slug, "default")


def select_model(spec: dict) -> str:
    """
    Select optimal Fal AI model based on label spec attributes.

    Selection criteria:
      - Industry (food_beverage, cosmetics, health_supplements, etc.)
      - Style family (modern_minimalist, bold_commercial, etc.)
      - Complexity (high detail = ultra/pro, fast = schnell/illustra)

    Returns a Fal AI model identifier string.
    """
    style = spec.get("style", spec.get("approach", {}).get("aesthetic_style", "custom"))
    industry = spec.get("industry", spec.get("product_category", "default"))

    style_family = _normalize_style(style)
    industry_key = _normalize_industry(industry)

    # Try exact match first
    model = MODEL_REGISTRY.get((industry_key, style_family))
    if model:
        return model

    # Try industry-only match
    model = MODEL_REGISTRY.get((industry_key, "default"))
    if model:
        return model

    # Try style-only match
    model = MODEL_REGISTRY.get(("default", style_family))
    if model:
        return model

    return MODEL_REGISTRY[("default", "default")]


def _build_label_prompt(spec: dict, spec_id: str) -> str:
    """
    Build a detailed AI prompt from label spec.
    Used for both artwork generation and full label synthesis.
    """
    label = spec.get("label", {})
    dims = label.get("dimensions", {})
    content = spec.get("content", {})
    color = spec.get("color_palette", {})
    style = spec.get("style", "custom")
    industry = spec.get("industry", spec.get("product_category", "general"))

    width = dims.get("width", 3)
    height = dims.get("height", 4)
    brand = content.get("brand", "Brand")
    product = content.get("product", "Product")
    background = color.get("background", "#FFFFFF")
    primary = color.get("primary", "#1A1A1A")
    accent = color.get("accent", "#0EA5E9")

    prompt = (
        f"Professional product label design for '{brand} {product}'. "
        f"Label format: {width}x{height} inches. "
        f"Background: {background}. Primary color: {primary}. Accent: {accent}. "
        f"Industry: {industry}. Style: {style}. "
        f"Clean print-ready design, no text, no barcode, no noise. "
        f"High resolution, photorealistic, commercial printing quality."
    )
    return prompt


def generate_label_image(
    spec_id: str,
    prompt: Optional[str] = None,
    size: str = "square",
    num_images: int = 1,
    style_hint: Optional[str] = None,
) -> Optional[dict]:
    """
    Generate label artwork image via Fal AI.

    Args:
        spec_id: Label spec identifier (used to load spec and select model)
        prompt: Custom prompt override (if None, builds from spec)
        size: Image size — "square", "portrait", "landscape_16_9", "1:1"
        num_images: Number of images to generate (1-4)
        style_hint: Override style_family for model selection

    Returns:
        dict with keys: images (list of {url, width, height}), model_used, seed
        or None if API key not configured or call fails.
    """
    api_key = get_api_key()
    if not api_key:
        print("FAL_API_KEY not set — Fal AI generation disabled.", file=sys.stderr)
        return None

    # Load spec
    spec_path = SKILL_DIR / "specs" / f"{spec_id}.yaml"
    if not spec_path.exists():
        print(f"Spec not found: {spec_id}", file=sys.stderr)
        return None

    import yaml
    with open(spec_path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    # Select model
    model = select_model(spec)
    if style_hint:
        model = MODEL_REGISTRY.get(
            ("default", _normalize_style(style_hint)),
            model,
        )

    # Build prompt
    if not prompt:
        prompt = _build_label_prompt(spec, spec_id)

    # Call Fal AI
    try:
        import fal_client

        result = fal_client.subscribe(
            model,
            arguments={
                "prompt": prompt,
                "image_size": size,
                "num_images": num_images,
                "enable_safety_filters": True,
            },
            api_key=api_key,
        )
        return {
            "images": result.get("images", []),
            "model_used": model,
            "seed": result.get("seed"),
        }
    except Exception as e:
        print(f"Fal AI error: {e}", file=sys.stderr)
        return None


def enhance_svg_artwork(spec_id: str, svg_path: Path, ai_image_url: str) -> bool:
    """
    Inject AI-generated artwork into the SVG artwork layer.

    Replaces the content of the <g id="artwork"> layer with an embedded
    image (base64) or links via <image> href.

    Args:
        spec_id: Spec identifier
        svg_path: Path to existing label.svg
        ai_image_url: URL of AI-generated image to inject

    Returns:
        True on success, False on failure.
    """
    try:
        import base64
        import urllib.request

        # Download image
        with urllib.request.urlopen(ai_image_url, timeout=30) as resp:
            image_data = resp.read()

        # Encode as base64
        b64 = base64.b64encode(image_data).decode("utf-8")
        mime = "image/png" if ai_image_url.lower().endswith(".png") else "image/jpeg"
        data_url = f"data:{mime};base64,{b64}"

        # Read SVG
        svg_text = svg_path.read_text(encoding="utf-8")

        # Replace artwork layer content
        artwork_open = '<g id="artwork">'
        artwork_close = "</g>"
        img_tag = f'<image href="{data_url}" width="100%" height="100%" preserveAspectRatio="xMidYMid slice"/>'

        start = svg_text.find(artwork_open)
        end = svg_text.find(artwork_close, start)
        if start == -1 or end == -1:
            print("Could not find artwork layer in SVG", file=sys.stderr)
            return False

        new_svg = (
            svg_text[:start + len(artwork_open)]
            + "\n    " + img_tag + "\n  "
            + svg_text[end:]
        )

        svg_path.write_text(new_svg, encoding="utf-8")
        return True

    except Exception as e:
        print(f"SVG enhancement error: {e}", file=sys.stderr)
        return False


def fal_status() -> dict:
    """
    Check Fal AI API connectivity and key validity.
    Returns dict with keys: configured (bool), key_present (bool), status, message.
    """
    key = get_api_key()
    if not key:
        return {
            "configured": False,
            "key_present": False,
            "status": "missing",
            "message": "FAL_API_KEY not set. Set it with: export FAL_API_KEY=your-key",
        }

    try:
        import fal_client
        # Lightweight test — subscribe with minimal prompt
        result = fal_client.subscribe(
            "fal-ai/flux-pro",
            arguments={
                "prompt": "test",
                "image_size": "square",
                "num_images": 1,
            },
            api_key=key,
        )
        return {
            "configured": True,
            "key_present": True,
            "status": "ok",
            "model_tested": "fal-ai/flux-pro",
            "message": f"Fal AI connected. Model: {result.get('images', [{}])[0].get('url', 'no-url')}",
        }
    except Exception as e:
        return {
            "configured": False,
            "key_present": True,
            "status": "error",
            "message": str(e),
        }


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fal AI label image generation")
    sub = parser.add_subparsers(dest="cmd")

    # fal status
    sub.add_parser("status", help="Check Fal AI configuration and connectivity")

    # fal generate <spec_id> [--prompt TEXT] [--size square|portrait|landscape_16_9]
    gen = sub.add_parser("generate", help="Generate label artwork via Fal AI")
    gen.add_argument("spec_id", help="Label spec ID")
    gen.add_argument("--prompt", help="Custom prompt (default: built from spec)")
    gen.add_argument("--size", default="square",
                     choices=["square", "portrait", "landscape_16_9", "1:1"],
                     help="Image size (default: square)")
    gen.add_argument("--inject", action="store_true",
                     help="Inject generated image into renders/{spec_id}/label.svg")

    args = parser.parse_args()

    if args.cmd == "status":
        s = fal_status()
        print(f"Configured: {s['configured']}")
        print(f"Key present: {s['key_present']}")
        print(f"Status: {s['status']}")
        print(f"Message: {s['message']}")

    elif args.cmd == "generate":
        if not is_configured():
            print("Error: FAL_API_KEY not set", file=sys.stderr)
            print("Set it with: export FAL_API_KEY=your-key", file=sys.stderr)
            sys.exit(1)

        result = generate_label_image(args.spec_id, prompt=args.prompt, size=args.size)
        if not result:
            sys.exit(1)

        print(f"Model: {result['model_used']}")
        for img in result["images"]:
            print(f"  {img['url']}")

        # Auto-inject into SVG if requested
        if args.inject and result["images"]:
            spec_path = SKILL_DIR / "specs" / f"{args.spec_id}.yaml"
            if spec_path.exists():
                import yaml
                with open(spec_path, encoding="utf-8") as f:
                    spec = yaml.safe_load(f)
                dims = spec.get("label", {}).get("dimensions", {})
                w_in = float(dims.get("width", 3))
                h_in = float(dims.get("height", 4))
                ratio = "landscape" if w_in > h_in else "portrait" if h_in > w_in else "square"

                svg_path = SKILL_DIR / "renders" / args.spec_id / "label.svg"
                if svg_path.exists():
                    ok = enhance_svg_artwork(args.spec_id, svg_path, result["images"][0]["url"])
                    print(f"Injected into SVG: {'ok' if ok else 'failed'}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()