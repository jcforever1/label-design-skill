#!/usr/bin/env python3
"""
spec_generator.py — Label spec creation, ID generation, and YAML persistence.

Spec ID format: {brand_slug}-{product_slug}-{sha256(timestamp+brand+product+seed)[:6]}
Collision suffix: -1, -2, ... added when spec ID already exists in specs directory.
"""

import hashlib
import re
import sys
import yaml
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path.home() / ".claude" / "skills" / "label-design"
SPECS_DIR = SKILL_DIR / "specs"


def generate_spec_id(brand: str, product: str, seed: str = "") -> str:
    """Generate a deterministic spec ID from brand + product + timestamp."""
    brand_slug = slugify(brand)
    product_slug = slugify(product)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{timestamp}|{brand}|{product}|{seed}"
    short_hash = hashlib.sha256(raw.encode()).hexdigest()[:6]
    return f"{brand_slug}-{product_slug}-{short_hash}"


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug: lowercase, hyphenated, no special chars."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"--+", "-", text)
    return text.strip("-")


def spec_id_exists(spec_id: str) -> bool:
    """Check if a spec with the given ID already exists."""
    return (SPECS_DIR / f"{spec_id}.yaml").exists()


def resolve_collision(spec_id: str) -> str:
    """If spec ID exists, return spec_id with -1, -2, ... suffix appended."""
    if not spec_id_exists(spec_id):
        return spec_id
    counter = 1
    while spec_id_exists(f"{spec_id}-{counter}"):
        counter += 1
    return f"{spec_id}-{counter}"


def write_spec(spec_data: dict, spec_id: str) -> Path:
    """
    Write a label spec to YAML.

    Args:
        spec_data: dict with all spec fields (brand, product, style, dimensions, etc.)
        spec_id: pre-generated spec ID (will be set in spec_data)

    Returns:
        Path to the written file
    """
    SPECS_DIR.mkdir(parents=True, exist_ok=True)

    spec_data["spec_id"] = spec_id
    spec_data.setdefault("created_at", datetime.now().isoformat())
    spec_data.setdefault("status", "draft")
    spec_data.setdefault("version", "1.0")

    # Ensure required top-level keys
    required = ["spec_id", "brand", "product", "status", "version"]
    for key in required:
        spec_data.setdefault(key, "")

    out_path = SPECS_DIR / f"{spec_id}.yaml"

    # YAML dump with standard formatting
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(spec_data, f, sort_keys=False, allow_unicode=True)

    return out_path


def read_spec(spec_id: str) -> dict | None:
    """Read a spec by ID. Returns None if not found."""
    path = SPECS_DIR / f"{spec_id}.yaml"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_specs(status: str | None = None) -> list[dict]:
    """
    List all specs, optionally filtered by status.
    Returns list of dicts with spec_id, brand, product, status, created_at.
    """
    if not SPECS_DIR.exists():
        return []
    specs = []
    for path in sorted(SPECS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        if spec and (status is None or spec.get("status") == status):
            specs.append({
                "spec_id": spec.get("spec_id", path.stem),
                "brand": spec.get("brand", ""),
                "product": spec.get("product", ""),
                "status": spec.get("status", "unknown"),
                "created_at": spec.get("created_at", ""),
            })
    return specs


def delete_spec(spec_id: str) -> bool:
    """Delete a spec by ID. Returns True if deleted, False if not found."""
    path = SPECS_DIR / f"{spec_id}.yaml"
    if path.exists():
        path.unlink()
        return True
    return False


if __name__ == "__main__":
    # CLI for quick testing: python scripts/spec_generator.py create "Acme Brand" "Chips"
    # python scripts/spec_generator.py list
    # python scripts/spec_generator.py read <spec_id>
    import argparse

    parser = argparse.ArgumentParser(description="Label spec generator")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list", help="List all specs")

    read_cmd = sub.add_parser("read", help="Read a spec")
    read_cmd.add_argument("spec_id", help="Spec ID")

    create_cmd = sub.add_parser("create", help="Create a new spec")
    create_cmd.add_argument("brand", help="Brand name")
    create_cmd.add_argument("product", help="Product name")
    create_cmd.add_argument("--seed", default="", help="Optional seed for ID diversity")

    delete_cmd = sub.add_parser("delete", help="Delete a spec")
    delete_cmd.add_argument("spec_id", help="Spec ID")

    args = parser.parse_args()

    if args.cmd == "list":
        specs = list_specs()
        if not specs:
            print("No specs found.")
        else:
            for s in specs:
                print(f"[{s['status']}] {s['spec_id']} — {s['brand']} / {s['product']} ({s['created_at'][:10]})")

    elif args.cmd == "read":
        spec = read_spec(args.spec_id)
        if spec:
            print(yaml.dump(spec, sort_keys=False, allow_unicode=True))
        else:
            print(f"Spec '{args.spec_id}' not found.", file=sys.stderr)
            sys.exit(1)

    elif args.cmd == "create":
        spec_id = generate_spec_id(args.brand, args.product, args.seed)
        spec_id = resolve_collision(spec_id)
        path = write_spec({"brand": args.brand, "product": args.product}, spec_id)
        print(f"Created: {spec_id} at {path}")

    elif args.cmd == "delete":
        ok = delete_spec(args.spec_id)
        if ok:
            print(f"Deleted: {args.spec_id}")
        else:
            print(f"Spec '{args.spec_id}' not found.", file=sys.stderr)
            sys.exit(1)