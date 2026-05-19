#!/usr/bin/env python3
"""
spec_validator.py — QA gate for the draft → locked lifecycle transition.

Hard failures (block locked):
  - Fake certifications (USDA Organic, FDA Approved, Non-GMO Verified without confirmation)
  - Fake barcode numbers (must be placeholder or GS1-registered)
  - Legal copy font < 6pt
  - Bleed < 0.125"
  - Safe zone < 0.125"

Warnings (flagged at reviewed → approved):
  - Contrast ratio < 4.5:1 on body text
  - > 3 type families
  - Barcode quiet zone < 10x module width
  - Color mode mismatch
"""

import sys
import yaml
from pathlib import Path
from dataclasses import dataclass, field

SKILL_DIR = Path.home() / ".claude" / "skills" / "label-design"
SPECS_DIR = SKILL_DIR / "specs"


@dataclass
class ValidationResult:
    hard_failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.hard_failures) == 0


def validate_spec(spec_id: str) -> ValidationResult:
    """Run all QA checks against a spec. Returns ValidationResult."""
    path = SPECS_DIR / f"{spec_id}.yaml"
    if not path.exists():
        return ValidationResult(hard_failures=[f"Spec not found: {spec_id}"])

    with open(path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    result = ValidationResult()

    label = spec.get("label", {})
    bleed = label.get("bleed", 0.125)
    safe_zone = label.get("safe_zone", 0.25)

    # Hard failures
    if bleed < 0.125:
        result.hard_failures.append(f"Bleed {bleed}\" is below minimum 0.125\"")

    if safe_zone < 0.125:
        result.hard_failures.append(f"Safe zone {safe_zone}\" is below minimum 0.125\"")

    # Barcode validation
    barcode = spec.get("content", {}).get("barcode", "")
    if barcode and barcode != "placeholder" and not barcode.startswith("GS1"):
        result.hard_failures.append(
            f"Barcode '{barcode}' appears to be a fake barcode number. "
            "Use 'placeholder' or a GS1-registered prefix."
        )

    # Certification validation
    claims = spec.get("claims", [])
    fake_certs = ["USDA Organic", "FDA Approved", "Non-GMO Verified", "Certified Organic"]
    for cert in fake_certs:
        if cert in claims and not spec.get("_cert_confirmed", False):
            result.hard_failures.append(
                f"Claim '{cert}' requires written confirmation before use. "
                "Set _cert_confirmed: true or remove the claim."
            )

    # Legal copy font size (if specified in spec)
    legal = spec.get("legal", {})
    font_size = legal.get("font_size")
    if font_size is not None and font_size < 6:
        result.hard_failures.append(
            f"Legal copy font size {font_size}pt is below 6pt minimum for readability."
        )

    # Warnings
    color_profile = spec.get("color_profile", "CMYK")
    if color_profile == "RGB":
        result.warnings.append(
            "Color mode is RGB. For print production, use CMYK and convert on export."
        )

    type_families = spec.get("typography", {}).get("families", [])
    if len(type_families) > 3:
        result.warnings.append(
            f"Typography uses {len(type_families)} type families (max 3 recommended)."
        )

    # Contrast check — CRITICAL for locked specs
    contrast = spec.get("contrast_ratio")
    status = spec.get("status", "draft")
    if contrast is not None and contrast < 4.5:
        if status == "locked":
            result.hard_failures.append(
                f"Contrast ratio {contrast}:1 is below 4.5:1 minimum for WCAG AA accessibility. "
                "Fix contrast before locking the spec."
            )
        else:
            result.warnings.append(
                f"Contrast ratio {contrast}:1 is below 4.5:1 minimum for body text accessibility."
            )

    # Barcode quiet zone
    barcode_quiet = spec.get("barcode_quiet_zone")
    module_width = spec.get("barcode_module_width", 0.33)  # mm, typical
    if barcode_quiet is not None and barcode_quiet < module_width * 10:
        result.warnings.append(
            f"Barcode quiet zone {barcode_quiet}mm is less than 10x module width ({module_width * 10}mm)."
        )

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: spec_validator.py <spec_id> [--strict]", file=sys.stderr)
        sys.exit(1)

    spec_id = sys.argv[1]
    strict = "--strict" in sys.argv

    result = validate_spec(spec_id)

    print(f"=== QA Report: {spec_id} ===")
    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"  ⚠  {w}")
    if result.hard_failures:
        print("\nHard Failures:")
        for f in result.hard_failures:
            print(f"  ✗  {f}")
    if result.is_valid:
        print("\nResult: PASS")

    if not result.is_valid:
        print("\nResult: FAIL — hard failures block locked status.")
        sys.exit(1)
    elif result.warnings and strict:
        print("\nResult: WARN — strict mode, warnings treated as failures.")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()