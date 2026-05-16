#!/usr/bin/env python3
"""
render_nutrition_panel.py — Generate region-specific nutrition fact panels as SVG.

Supported regions:
  - US_FDA: FDA Nutrition Facts panel (standard/vertical format)
  - EU_1169: EU mandatory nutrition declaration (horizontal table)
  - CA_CFIA: Canadian nutrition facts table (Bilingual EN/FR)
  - AU_FSANZ: Australian/New Zealand nutrition information panel

Output: renders/{spec_id}/nutrition.svg
"""

import sys
import yaml
from pathlib import Path
from dataclasses import dataclass

SKILL_DIR = Path.home() / ".claude" / "skills" / "label-design"
SPECS_DIR = SKILL_DIR / "specs"
RENDERS_DIR = SKILL_DIR / "renders"


@dataclass
class NutritionPanelConfig:
    """Configuration for a nutrition panel."""
    region: str
    width: float  # pts
    height: float  # pts
    font_family: str
    background: str
    text_color: str
    border_color: str
    rule_color: str
    serving_size: str
    servings_per_container: str
    calories: int
    fat_g: float
    saturated_g: float
    trans_g: float
    sodium_mg: int
    carbs_g: float
    fiber_g: float
    sugars_g: float
    protein_g: float
    vitamins: list[str]  # e.g. ["Vitamin D", "Calcium", "Iron"]
    vitamins_vals: list[str]  # e.g. ["0 mcg", "130 mg", "4 mg"]


def us_fda_panel(cfg: NutritionPanelConfig) -> str:
    """Generate FDA-style Nutrition Facts SVG."""
    fat_cal = cfg.fat_g * 9
    carbs_cal = cfg.carbs_g * 4
    protein_cal = cfg.protein_g * 4
    total_cal = cfg.calories  # use labeled calories, not calculated

    lines = [
        "  <g id=\"nutrition-panel\" font-family=\"Helvetica, Arial, sans-serif\">",
        "    <!-- FDA Nutrition Facts -->",
        "    <rect x=\"0\" y=\"0\" width=\"" + f"{cfg.width:.2f}" + "\" height=\"" + f"{cfg.height:.2f}" + "\" fill=\"" + cfg.background + "\" />",
        "    <rect x=\"0\" y=\"0\" width=\"" + f"{cfg.width:.2f}" + "\" height=\"" + f"{cfg.height:.2f}" + "\" fill=\"none\" stroke=\"" + cfg.border_color + "\" stroke-width=\"1\"/>",
        "",
        "    <!-- Title -->",
        "    <text x=\"" + f"{cfg.width/2:.2f}" + "\" y=\"22\" text-anchor=\"middle\" font-size=\"16\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">Nutrition Facts</text>",
        "    <line x1=\"0\" y1=\"26\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"26\" stroke=\"" + cfg.border_color + "\" stroke-width=\"1\"/>",
        "",
        "    <!-- Serving Size -->",
        "    <text x=\"4\" y=\"38\" font-size=\"9\" fill=\"" + cfg.text_color + "\">Serving Size</text>",
        "    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"38\" text-anchor=\"end\" font-size=\"9\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">" + cfg.serving_size + "</text>",
        "    <line x1=\"0\" y1=\"42\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"42\" stroke=\"" + cfg.border_color + "\" stroke-width=\"0.5\"/>",
        "",
        "    <!-- Servings Per Container -->",
        "    <text x=\"4\" y=\"52\" font-size=\"9\" fill=\"" + cfg.text_color + "\">Servings Per Container</text>",
        "    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"52\" text-anchor=\"end\" font-size=\"9\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">" + cfg.servings_per_container + "</text>",
        "    <line x1=\"0\" y1=\"56\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"56\" stroke=\"" + cfg.border_color + "\" stroke-width=\"4\"/>",
        "",
        "    <!-- Calories -->",
        "    <text x=\"4\" y=\"68\" font-size=\"11\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">Calories</text>",
        "    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"68\" text-anchor=\"end\" font-size=\"11\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">" + str(cfg.calories) + "</text>",
        "    <line x1=\"0\" y1=\"72\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"72\" stroke=\"" + cfg.border_color + "\" stroke-width=\"4\"/>",
        "",
        "    <!-- Daily Value header -->",
        "    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"82\" text-anchor=\"end\" font-size=\"8\" fill=\"" + cfg.text_color + "\">% Daily Value*</text>",
        "    <line x1=\"0\" y1=\"86\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"86\" stroke=\"" + cfg.border_color + "\" stroke-width=\"1\"/>",
    ]

    # Nutrient rows: (name, value, dv_pct, is_bold)
    nutrients = [
        ("Total Fat", f"{cfg.fat_g:.1f}g", int(fat_cal / 78 * 100), True),
        ("  Saturated Fat", f"{cfg.saturated_g:.1f}g", int(cfg.saturated_g / 20 * 100), False),
        ("  Trans Fat", f"{cfg.trans_g:.1f}g", 0, False),
        ("Cholesterol", f"{cfg.sodium_mg}mg", int(cfg.sodium_mg / 2.4), True),
        ("Sodium", f"{cfg.sodium_mg}mg", int(cfg.sodium_mg / 2.3), True),
        ("Total Carbohydrate", f"{cfg.carbs_g:.1f}g", int(cfg.carbs_g / 275 * 100), True),
        ("  Dietary Fiber", f"{cfg.fiber_g:.1f}g", int(cfg.fiber_g / 28 * 100), False),
        ("  Total Sugars", f"{cfg.sugars_g:.1f}g", 0, False),
        ("Protein", f"{cfg.protein_g:.1f}g", int(cfg.protein_g / 50 * 100), True),
    ]

    y = 94
    for name, value, dv, bold in nutrients:
        fw = "bold" if bold else "normal"
        lines.append(f"    <text x=\"4\" y=\"" + f"{y:.0f}" + "\" font-size=\"9\" font-weight=\"" + fw + "\" fill=\"" + cfg.text_color + "\">" + name + "</text>")
        if dv > 0:
            lines.append(f"    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"" + f"{y:.0f}" + "\" text-anchor=\"end\" font-size=\"9\" font-weight=\"" + fw + "\" fill=\"" + cfg.text_color + "\">" + value + "  <tspan font-weight=\"normal\">" + str(dv) + "%</tspan></text>")
        else:
            lines.append(f"    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"" + f"{y:.0f}" + "\" text-anchor=\"end\" font-size=\"9\" font-weight=\"" + fw + "\" fill=\"" + cfg.text_color + "\">" + value + "</text>")
        lines.append(f"    <line x1=\"0\" y1=\"" + f"{y+3:.0f}" + "\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"" + f"{y+3:.0f}" + "\" stroke=\"" + cfg.rule_color + "\" stroke-width=\"0.5\"/>")
        y += 11

    # Vitamins
    y += 2
    lines.append(f"    <line x1=\"0\" y1=\"" + f"{y:.0f}" + "\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"" + f"{y:.0f}" + "\" stroke=\"" + cfg.border_color + "\" stroke-width=\"4\"/>")
    y += 10
    for vit, val in zip(cfg.vitamins, cfg.vitamins_vals):
        lines.append(f"    <text x=\"4\" y=\"" + f"{y:.0f}" + "\" font-size=\"8\" fill=\"" + cfg.text_color + "\">" + vit + "</text>")
        lines.append(f"    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"" + f"{y:.0f}" + "\" text-anchor=\"end\" font-size=\"8\" fill=\"" + cfg.text_color + "\">" + val + "</text>")
        y += 10

    # Footer
    y += 4
    lines.append(f"    <line x1=\"0\" y1=\"" + f"{y:.0f}" + "\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"" + f"{y:.0f}" + "\" stroke=\"" + cfg.border_color + "\" stroke-width=\"4\"/>")
    y += 10
    lines.append(f"    <text x=\"" + f"{cfg.width/2:.2f}" + "\" y=\"" + f"{y:.0f}" + "\" text-anchor=\"middle\" font-size=\"7\" fill=\"" + cfg.text_color + "\">* Percent Daily Values are based on a 2,000 calorie diet.</text>")

    lines.append("  </g>")
    return "\n".join(lines)


def eu_panel(cfg: NutritionPanelConfig) -> str:
    """Generate EU 1169-style nutrition declaration table SVG."""
    # EU uses per 100g/100ml and % RI
    lines = [
        "  <g id=\"nutrition-panel\" font-family=\"Helvetica, Arial, sans-serif\">",
        "    <!-- EU Nutrition Declaration (1169/2011) -->",
        "    <rect x=\"0\" y=\"0\" width=\"" + f"{cfg.width:.2f}" + "\" height=\"" + f"{cfg.height:.2f}" + "\" fill=\"" + cfg.background + "\" />",
        "    <rect x=\"0\" y=\"0\" width=\"" + f"{cfg.width:.2f}" + "\" height=\"" + f"{cfg.height:.2f}" + "\" fill=\"none\" stroke=\"" + cfg.border_color + "\" stroke-width=\"1\"/>",
        "",
        "    <text x=\"4\" y=\"16\" font-size=\"10\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">Nutrition Information</text>",
        "    <line x1=\"0\" y1=\"20\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"20\" stroke=\"" + cfg.border_color + "\" stroke-width=\"0.5\"/>",
        "    <text x=\"4\" y=\"32\" font-size=\"8\" fill=\"" + cfg.text_color + "\">Per 100g</text>",
        "    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"32\" text-anchor=\"end\" font-size=\"8\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">% RI*</text>",
        "    <line x1=\"0\" y1=\"36\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"36\" stroke=\"" + cfg.border_color + "\" stroke-width=\"0.5\"/>",
    ]

    nutrients = [
        ("Energy", f"{cfg.calories} kJ", int(cfg.calories / 8400 * 100)),
        ("Fat", f"{cfg.fat_g:.1f}g", int(cfg.fat_g / 70 * 100)),
        ("  of which saturates", f"{cfg.saturated_g:.1f}g", int(cfg.saturated_g / 20 * 100)),
        ("Carbohydrate", f"{cfg.carbs_g:.1f}g", int(cfg.carbs_g / 260 * 100)),
        ("  of which sugars", f"{cfg.sugars_g:.1f}g", int(cfg.sugars_g / 90 * 100)),
        ("Fibre", f"{cfg.fiber_g:.1f}g", int(cfg.fiber_g / 24 * 100)),
        ("Protein", f"{cfg.protein_g:.1f}g", int(cfg.protein_g / 50 * 100)),
        ("Salt", f"{cfg.sodium_mg/1000:.2f}g", int(cfg.sodium_mg / 6 * 100)),
    ]

    y = 42
    for name, value, ri in nutrients:
        bold = not name.startswith("  ")
        fw = "bold" if bold else "normal"
        lines.append(f"    <text x=\"4\" y=\"" + f"{y:.0f}" + "\" font-size=\"8\" font-weight=\"" + fw + "\" fill=\"" + cfg.text_color + "\">" + name + "</text>")
        lines.append(f"    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"" + f"{y:.0f}" + "\" text-anchor=\"end\" font-size=\"8\" font-weight=\"" + fw + "\" fill=\"" + cfg.text_color + "\">" + value + "  <tspan font-weight=\"normal\">(" + str(ri) + "%)</tspan></text>")
        lines.append(f"    <line x1=\"0\" y1=\"" + f"{y+2:.0f}" + "\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"" + f"{y+2:.0f}" + "\" stroke=\"" + cfg.rule_color + "\" stroke-width=\"0.25\"/>")
        y += 11

    y += 4
    lines.append(f"    <text x=\"4\" y=\"" + f"{y:.0f}" + "\" font-size=\"7\" fill=\"" + cfg.text_color + "\">* Reference Intake for an average adult (8400 kJ / 2000 kcal).</text>")
    lines.append("  </g>")
    return "\n".join(lines)


def ca_panel(cfg: NutritionPanelConfig) -> str:
    """Generate Canadian CFIA bilingual nutrition facts table SVG."""
    # Canada uses dual-language (EN/FR) and has specific formatting
    lines = [
        "  <g id=\"nutrition-panel\" font-family=\"Helvetica, Arial, sans-serif\">",
        "    <!-- Canadian Nutrition Facts Table (Bilingual EN/FR) -->",
        "    <rect x=\"0\" y=\"0\" width=\"" + f"{cfg.width:.2f}" + "\" height=\"" + f"{cfg.height:.2f}" + "\" fill=\"" + cfg.background + "\" />",
        "    <rect x=\"0\" y=\"0\" width=\"" + f"{cfg.width:.2f}" + "\" height=\"" + f"{cfg.height:.2f}" + "\" fill=\"none\" stroke=\"" + cfg.border_color + "\" stroke-width=\"1\"/>",
        "",
        "    <!-- Bilingual header -->",
        "    <text x=\"4\" y=\"14\" font-size=\"11\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">Nutrition Facts</text>",
        "    <text x=\"4\" y=\"26\" font-size=\"9\" fill=\"" + cfg.text_color + "\">Valeur nutritive</text>",
        "    <line x1=\"0\" y1=\"30\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"30\" stroke=\"" + cfg.border_color + "\" stroke-width=\"1\"/>",
        "",
        "    <!-- Serving size -->",
        "    <text x=\"4\" y=\"42\" font-size=\"8\" fill=\"" + cfg.text_color + "\">Per</text>",
        "    <text x=\"4\" y=\"52\" font-size=\"8\" fill=\"" + cfg.text_color + "\">Par</text>",
        "    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"47\" text-anchor=\"end\" font-size=\"9\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">" + cfg.serving_size + "</text>",
        "    <line x1=\"0\" y1=\"56\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"56\" stroke=\"" + cfg.border_color + "\" stroke-width=\"4\"/>",
    ]

    nutrients = [
        ("Calories", "Calories", str(cfg.calories), str(cfg.calories)),
        ("Fat / Lipides", f"{cfg.fat_g:.1f}g", int(cfg.fat_g / 75 * 100)),
        ("  Saturated / Satures", f"{cfg.saturated_g:.1f}g", int(cfg.saturated_g / 20 * 100)),
        ("  + Trans", f"{cfg.trans_g:.1f}g", 0),
        ("Cholesterol", f"{cfg.sodium_mg}mg", int(cfg.sodium_mg / 300 * 100)),
        ("Sodium", f"{cfg.sodium_mg}mg", int(cfg.sodium_mg / 2300 * 100)),
        ("Carbohydrate / Glucides", f"{cfg.carbs_g:.1f}g", int(cfg.carbs_g / 300 * 100)),
        ("  Fibre / Fibres", f"{cfg.fiber_g:.1f}g", int(cfg.fiber_g / 25 * 100)),
        ("  Sugars / Sucres", f"{cfg.sugars_g:.1f}g", int(cfg.sugars_g / 100 * 100)),
        ("Protein", f"{cfg.protein_g:.1f}g", int(cfg.protein_g / 50 * 100)),
    ]

    y = 64
    for item in nutrients:
        if len(item) == 4:
            en_name, fr_name, value, en_val = item
            lines.append(f"    <text x=\"4\" y=\"" + f"{y:.0f}" + "\" font-size=\"8\" fill=\"" + cfg.text_color + "\">" + en_name + "</text>")
            lines.append(f"    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"" + f"{y:.0f}" + "\" text-anchor=\"end\" font-size=\"8\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">" + value + "</text>")
        else:
            name, value, dv = item
            bold = not name.startswith("  ")
            fw = "bold" if bold else "normal"
            lines.append(f"    <text x=\"4\" y=\"" + f"{y:.0f}" + "\" font-size=\"8\" font-weight=\"" + fw + "\" fill=\"" + cfg.text_color + "\">" + name + "</text>")
            if dv > 0:
                lines.append(f"    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"" + f"{y:.0f}" + "\" text-anchor=\"end\" font-size=\"8\" font-weight=\"" + fw + "\" fill=\"" + cfg.text_color + "\">" + value + "  <tspan font-weight=\"normal\">" + str(dv) + "%</tspan></text>")
            else:
                lines.append(f"    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"" + f"{y:.0f}" + "\" text-anchor=\"end\" font-size=\"8\" font-weight=\"" + fw + "\" fill=\"" + cfg.text_color + "\">" + value + "</text>")
        lines.append(f"    <line x1=\"0\" y1=\"" + f"{y+2:.0f}" + "\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"" + f"{y+2:.0f}" + "\" stroke=\"" + cfg.rule_color + "\" stroke-width=\"0.5\"/>")
        y += 11

    y += 4
    lines.append(f"    <text x=\"4\" y=\"" + f"{y:.0f}" + "\" font-size=\"7\" fill=\"" + cfg.text_color + "\">* 5% DV or less is a little, 15% or more is a lot</text>")
    lines.append("  </g>")
    return "\n".join(lines)


def au_panel(cfg: NutritionPanelConfig) -> str:
    """Generate AU/FSANZ nutrition information panel SVG."""
    lines = [
        "  <g id=\"nutrition-panel\" font-family=\"Helvetica, Arial, sans-serif\">",
        "    <!-- Australian / New Zealand Nutrition Information Panel -->",
        "    <rect x=\"0\" y=\"0\" width=\"" + f"{cfg.width:.2f}" + "\" height=\"" + f"{cfg.height:.2f}" + "\" fill=\"" + cfg.background + "\" />",
        "    <rect x=\"0\" y=\"0\" width=\"" + f"{cfg.width:.2f}" + "\" height=\"" + f"{cfg.height:.2f}" + "\" fill=\"none\" stroke=\"" + cfg.border_color + "\" stroke-width=\"1\"/>",
        "",
        "    <text x=\"4\" y=\"14\" font-size=\"10\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">Nutrition Information</text>",
        "    <line x1=\"0\" y1=\"18\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"18\" stroke=\"" + cfg.border_color + "\" stroke-width=\"0.5\"/>",
        "    <text x=\"4\" y=\"30\" font-size=\"8\" fill=\"" + cfg.text_color + "\">Servings per package:</text>",
        "    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"30\" text-anchor=\"end\" font-size=\"8\" fill=\"" + cfg.text_color + "\">" + cfg.servings_per_container + "</text>",
        "    <text x=\"4\" y=\"42\" font-size=\"8\" fill=\"" + cfg.text_color + "\">Serving size:</text>",
        "    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"42\" text-anchor=\"end\" font-size=\"8\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">" + cfg.serving_size + "</text>",
        "    <line x1=\"0\" y1=\"46\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"46\" stroke=\"" + cfg.border_color + "\" stroke-width=\"0.5\"/>",
    ]

    # AU uses per serving and per 100g
    nutrients = [
        ("Energy", f"{cfg.calories} kJ", f"{int(cfg.calories / 4.2)} cal", int(cfg.calories / 8700 * 100)),
        ("Protein", f"{cfg.protein_g:.1f}g", f"{cfg.protein_g/5:.1f}g", int(cfg.protein_g / 50 * 100)),
        ("Fat, total", f"{cfg.fat_g:.1f}g", f"{cfg.fat_g/5:.1f}g", int(cfg.fat_g / 70 * 100)),
        ("  - Saturated", f"{cfg.saturated_g:.1f}g", f"{cfg.saturated_g/5:.1f}g", int(cfg.saturated_g / 24 * 100)),
        ("Carbohydrate", f"{cfg.carbs_g:.1f}g", f"{cfg.carbs_g/5:.1f}g", int(cfg.carbs_g / 310 * 100)),
        ("  - Sugars", f"{cfg.sugars_g:.1f}g", f"{cfg.sugars_g/5:.1f}g", int(cfg.sugars_g / 90 * 100)),
        ("Sodium", f"{cfg.sodium_mg}mg", f"{cfg.sodium_mg/5:.0f}mg", int(cfg.sodium_mg / 2300 * 100)),
    ]

    y = 54
    lines.append("    <line x1=\"0\" y1=\"" + f"{y-2:.0f}" + "\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"" + f"{y-2:.0f}" + "\" stroke=\"" + cfg.border_color + "\" stroke-width=\"4\"/>")
    lines.append("    <text x=\"4\" y=\"" + f"{y+8:.0f}" + "\" font-size=\"7\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">Per Serving</text>")
    lines.append("    <text x=\"" + f"{cfg.width/2:.2f}" + "\" y=\"" + f"{y+8:.0f}" + "\" text-anchor=\"middle\" font-size=\"7\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">Per 100g</text>")
    lines.append("    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"" + f"{y+8:.0f}" + "\" text-anchor=\"end\" font-size=\"7\" font-weight=\"bold\" fill=\"" + cfg.text_color + "\">% DI*</text>")

    y += 18
    for name, per_serving, per_100g, di in nutrients:
        lines.append(f"    <text x=\"4\" y=\"" + f"{y:.0f}" + "\" font-size=\"8\" fill=\"" + cfg.text_color + "\">" + name + "</text>")
        lines.append(f"    <text x=\"" + f"{cfg.width/2:.2f}" + "\" y=\"" + f"{y:.0f}" + "\" text-anchor=\"middle\" font-size=\"8\" fill=\"" + cfg.text_color + "\">" + per_100g + "</text>")
        lines.append(f"    <text x=\"" + f"{cfg.width-4:.2f}" + "\" y=\"" + f"{y:.0f}" + "\" text-anchor=\"end\" font-size=\"8\" fill=\"" + cfg.text_color + "\">" + str(di) + "%</text>")
        lines.append(f"    <line x1=\"0\" y1=\"" + f"{y+2:.0f}" + "\" x2=\"" + f"{cfg.width:.2f}" + "\" y2=\"" + f"{y+2:.0f}" + "\" stroke=\"" + cfg.rule_color + "\" stroke-width=\"0.25\"/>")
        y += 11

    y += 4
    lines.append(f"    <text x=\"4\" y=\"" + f"{y:.0f}" + "\" font-size=\"7\" fill=\"" + cfg.text_color + "\">* Percentage Daily Intakes are based on an average adult diet.</text>")
    lines.append("  </g>")
    return "\n".join(lines)


def build_nutrition_svg(cfg: NutritionPanelConfig) -> str:
    """Build nutrition panel SVG string."""
    region = cfg.region

    if region == "US_FDA":
        panel_content = us_fda_panel(cfg)
    elif region == "EU_1169":
        panel_content = eu_panel(cfg)
    elif region == "CA_CFIA":
        panel_content = ca_panel(cfg)
    elif region == "AU_FSANZ":
        panel_content = au_panel(cfg)
    else:
        panel_content = us_fda_panel(cfg)

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{cfg.width/72:.3f}in" height="{cfg.height/72:.3f}in"
     viewBox="0 0 {cfg.width:.2f} {cfg.height:.2f}">
  <title>Nutrition Panel — {region}</title>
{panel_content}
</svg>"""
    return svg


def render_nutrition_panel(
    spec_id: str,
    region: str = "US_FDA",
    serving_size: str = "1 cup (240ml)",
    servings_per_container: str = "8",
    calories: int = 120,
    fat_g: float = 0.5,
    saturated_g: float = 0.0,
    trans_g: float = 0.0,
    sodium_mg: int = 150,
    carbs_g: float = 28.0,
    fiber_g: float = 1.0,
    sugars_g: float = 24.0,
    protein_g: float = 1.0,
    vitamins: list[str] | None = None,
    vitamins_vals: list[str] | None = None,
    dry_run: bool = False,
) -> Path | None:
    """Render nutrition panel to SVG file. Returns path or None on failure."""
    if vitamins is None:
        vitamins = ["Vitamin D", "Calcium", "Iron"]
    if vitamins_vals is None:
        vitamins_vals = ["0 mcg", "130 mg", "4 mg"]

    path = SPECS_DIR / f"{spec_id}.yaml"
    if not path.exists():
        print(f"Spec not found: {spec_id}", file=sys.stderr)
        return None

    with open(path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    label = spec.get("label", {})
    dims = label.get("dimensions", {})

    # Panel width fits label width minus bleeds and margins
    width_in = float(dims.get("width", 3))
    panel_w = min(width_in * 72 * 0.85, 252)  # max ~3.5in in points
    panel_h = {"US_FDA": 290, "EU_1169": 220, "CA_CFIA": 290, "AU_FSANZ": 260}[region]
    cfg = NutritionPanelConfig(
        region=region,
        width=panel_w,
        height=panel_h,
        font_family="Helvetica, Arial, sans-serif",
        background="#FFFFFF",
        text_color="#1A1A1A",
        border_color="#1A1A1A",
        rule_color="#1A1A1A",
        serving_size=serving_size,
        servings_per_container=servings_per_container,
        calories=calories,
        fat_g=fat_g,
        saturated_g=saturated_g,
        trans_g=trans_g,
        sodium_mg=sodium_mg,
        carbs_g=carbs_g,
        fiber_g=fiber_g,
        sugars_g=sugars_g,
        protein_g=protein_g,
        vitamins=vitamins,
        vitamins_vals=vitamins_vals,
    )

    svg_content = build_nutrition_svg(cfg)

    if dry_run:
        print(svg_content)
        return None

    out_dir = RENDERS_DIR / spec_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "nutrition.svg"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    return out_path


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Render nutrition panel SVG")
    parser.add_argument("spec_id", help="Spec ID")
    parser.add_argument("--region", default="US_FDA",
                        choices=["US_FDA", "EU_1169", "CA_CFIA", "AU_FSANZ"],
                        help="Region for panel format")
    parser.add_argument("--serving-size", default="1 cup (240ml)", help="Serving size")
    parser.add_argument("--servings", default="8", help="Servings per container")
    parser.add_argument("--calories", type=int, default=120, help="Calories per serving")
    parser.add_argument("--fat", type=float, default=0.5, help="Fat (g)")
    parser.add_argument("--sodium", type=int, default=150, help="Sodium (mg)")
    parser.add_argument("--carbs", type=float, default=28.0, help="Carbohydrates (g)")
    parser.add_argument("--fiber", type=float, default=1.0, help="Fiber (g)")
    parser.add_argument("--sugars", type=float, default=24.0, help="Sugars (g)")
    parser.add_argument("--protein", type=float, default=1.0, help="Protein (g)")
    parser.add_argument("--dry-run", action="store_true", help="Print SVG to stdout")
    args = parser.parse_args()

    path = render_nutrition_panel(
        args.spec_id,
        region=args.region,
        serving_size=args.serving_size,
        servings_per_container=args.servings,
        calories=args.calories,
        fat_g=args.fat,
        sodium_mg=args.sodium,
        carbs_g=args.carbs,
        fiber_g=args.fiber,
        sugars_g=args.sugars,
        protein_g=args.protein,
        dry_run=args.dry_run,
    )
    if path:
        print(f"Rendered: {path}")


if __name__ == "__main__":
    main()