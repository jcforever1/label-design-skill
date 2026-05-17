#!/usr/bin/env python3
"""
svg_to_png.py — Rasterize SVG to 300 DPI PNG for press-ready output.

Requires: CairoSVG (pip install cairosvg) or Inkscape in PATH.
Falls back to a pure-python placeholder if neither is available.

Output: renders/{spec_id}/label.png
"""

import sys
import subprocess
from pathlib import Path

SKILL_DIR = Path.home() / ".claude" / "skills" / "label-design"
RENDERS_DIR = SKILL_DIR / "renders"
SPECS_DIR = SKILL_DIR / "specs"

DPI = 300


def is_cairosvg_available() -> bool:
    try:
        import cairosvg
        return True
    except ImportError:
        return False


def is_inkscape_available() -> bool:
    try:
        subprocess.run(
            ["inkscape", "--version"], capture_output=True, check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def svg_to_png_cairo(svg_path: Path, png_path: Path, dpi: int = DPI) -> bool:
    try:
        import cairosvg

        # Get dimensions from the spec YAML — the SVG's own width/height
        # attributes may be wrong (e.g. 201x200 instead of 3x2). Pull the
        # spec_id from the renders directory structure:
        # renders/<spec_id>/label.svg  →  spec_id = parent dir name
        spec_id = svg_path.parent.name
        spec_path = SPECS_DIR / f"{spec_id}.yaml"
        if spec_path.exists():
            import yaml
            with open(spec_path, encoding="utf-8") as f:
                spec = yaml.safe_load(f)
            dims = spec.get("label", {}).get("dimensions", {})
            w_in = float(dims.get("width", 3.0))
            h_in = float(dims.get("height", 2.0))
        else:
            # Fallback: parse SVG attribute (may still be wrong, let Cairo fail)
            with open(svg_path, encoding="utf-8") as f:
                svg_text = f.read()
            import re
            w_match = re.search(r'width="([0-9.]+)in"', svg_text)
            h_match = re.search(r'height="([0-9.]+)in"', svg_text)
            if w_match and h_match:
                w_in = float(w_match.group(1))
                h_in = float(h_match.group(1))
            else:
                w_in = h_in = None

        if w_in is not None and h_in is not None:
            output_w = int(w_in * dpi)
            output_h = int(h_in * dpi)
        else:
            output_w = output_h = None

        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(png_path),
            dpi=dpi,
            output_width=output_w,
            output_height=output_h,
        )
        return True
    except Exception as e:
        print(f"CairoSVG error: {e}", file=sys.stderr)
        return False


def svg_to_png_inkscape(svg_path: Path, png_path: Path, dpi: int = DPI) -> bool:
    try:
        subprocess.run(
            [
                "inkscape",
                str(svg_path),
                "--export-filename", str(png_path),
                "--export-dpi", str(dpi),
                "--export-type", "png",
            ],
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Inkscape error: {e.stderr}", file=sys.stderr)
        return False


def svg_to_png_placeholder(png_path: Path, width_in: float = 4, height_in: float = 3) -> bool:
    try:
        from PIL import Image, ImageDraw

        w_px = int(width_in * DPI)
        h_px = int(height_in * DPI)
        img = Image.new("RGB", (w_px, h_px), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w_px - 1, h_px - 1], outline="#333333", width=4)
        draw.text((w_px // 2 - 80, h_px // 2 - 10), "SVG placeholder", fill="#333333")
        img.save(png_path, "PNG", dpi=(DPI, DPI))
        return True
    except ImportError:
        print("Error: Neither CairoSVG nor Inkscape is available.", file=sys.stderr)
        print("Install cairosvg: pip install cairosvg", file=sys.stderr)
        print("Or install Inkscape: https://inkscape.org/", file=sys.stderr)
        return False


def svg_to_png(spec_id: str, dry_run: bool = False, dpi: int = DPI,
               filename: str = "label.svg") -> Path | None:
    """
    Convert renders/{spec_id}/{filename} to PNG at the specified DPI.
    Returns PNG path or None on failure.
    """
    svg_path = RENDERS_DIR / spec_id / filename
    png_path = RENDERS_DIR / spec_id / f"{Path(filename).stem}.png"

    if not svg_path.exists():
        print(f"SVG not found: {svg_path}", file=sys.stderr)
        return None

    if dry_run:
        print(f"Would convert {svg_path} -> {png_path} at {dpi} DPI")
        return None

    if is_cairosvg_available():
        ok = svg_to_png_cairo(svg_path, png_path, dpi=dpi)
    elif is_inkscape_available():
        ok = svg_to_png_inkscape(svg_path, png_path, dpi=dpi)
    else:
        ok = svg_to_png_placeholder(png_path)

    if ok:
        return png_path
    return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Rasterize label SVG to 300 DPI PNG")
    parser.add_argument("spec_id", help="Spec ID")
    parser.add_argument("--dpi", type=int, default=DPI, help=f"Output DPI (default {DPI})")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    path = svg_to_png(args.spec_id, dry_run=args.dry_run, dpi=args.dpi)
    if path:
        print(f"PNG: {path}")


if __name__ == "__main__":
    main()
