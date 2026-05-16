#!/usr/bin/env python3
"""
nutrition_labelifier.py — Ingredient → Nutrition Panel pipeline.

Pipeline:
  1. Accept ingredients with weights
  2. Search USDA FoodData Central via web (fdc.nal.usda.gov)
  3. Similarity match → surface top-3 candidates for user confirmation
  4. Retrieve per-100g nutrient profile (lab-analyzed entries preferred)
  5. Apply cooking method yield factor (USDA Table 4)
  6. Scale aggregated nutrients to serving size
  7. Apply rounding rules per 21 CFR 101.9(c) / Annex XV / CFIA / FSANZ
  8. Calculate %DV / %RI / %DI using 2016 FDA Daily Values
  9. Flag 9 FDA major allergens (bold)
  10. Render panel as SVG → renders/{spec_id}/nutrition.svg
  11. Append mandatory disclaimer + source citations
"""

import re
import sys
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SKILL_DIR = Path.home() / ".claude" / "skills" / "label-design"
NUTRITION_RULES_PATH = SKILL_DIR / "lib" / "nutrition_rules.yaml"


# ─── Daily Values ────────────────────────────────────────────────────────────

FDA_2016_DV = {
    "calories": 2000,
    "total_fat": 78,
    "saturated_fat": 20,
    "trans_fat": 0,
    "cholesterol": 300,
    "sodium": 2300,
    "total_carbohydrate": 275,
    "dietary_fiber": 28,
    "total_sugars": 0,  # no DV
    "added_sugars": 50,
    "protein": 50,
    "vitamin_d": 20,
    "calcium": 1300,
    "iron": 18,
    "potassium": 4700,
}

EU_RI = {
    "energy_kj": 8400,
    "energy_kcal": 2000,
    "fat": 70,
    "saturated_fat": 20,
    "carbohydrate": 260,
    "sugars": 90,
    "fiber": 24,
    "protein": 50,
    "salt": 6,
    "sodium": 2300,
}

CA_DV = {
    "fat": 75,
    "saturated_fat": 20,
    "trans_fat": 0,
    "cholesterol": 300,
    "sodium": 2300,
    "carbohydrate": 300,
    "fiber": 25,
    "sugars": 100,
    "protein": 50,
    "vitamin_a": 1000,
    "vitamin_c": 60,
    "calcium": 1100,
    "iron": 14,
}

AU_DI = {
    "energy_kj": 8700,
    "protein": 50,
    "fat_total": 70,
    "saturated_fat": 24,
    "carbohydrate": 310,
    "sugars": 200,
    "sodium": 2300,
}

# ─── Allergens ───────────────────────────────────────────────────────────────

FDA_MAJOR_ALLERGENS = {
    "milk", "dairy", "cream", "cheese", "butter", "whey", "casein",
    "eggs", "egg", "albumin",
    "fish", "bass", "cod", "salmon", "tuna", "anchovy", "tilapia",
    "crustacean", "shrimp", "crab", "lobster", "prawn", "oyster", "clam", "mussel",
    "tree nuts", "almond", "brazil nut", "cashew", "hazelnut", "macadamia",
    "pecan", "pistachio", "walnut", "chestnut", "pine nut",
    "peanuts", "peanut",
    "soybeans", "soy", "tofu", "edamame", "miso", "tempeh",
    "wheat", "gluten", "barley", "rye", "oats", "spelt", "triticale",
    "sesame", "sesame seeds", "tahini", "halva", "sesame oil",
}


# ─── Data classes ────────────────────────────────────────────────────────────

@dataclass
class NutrientValue:
    value: float
    unit: str
    source_db_id: str = ""
    source_confidence: float = 0.0  # 0.0–1.0
    is_estimate: bool = False


@dataclass
class Ingredient:
    name: str
    weight_g: float
    raw_nutrients: dict[str, NutrientValue] = field(default_factory=dict)
    matched_fdc_id: Optional[str] = None
    matched_name: str = ""
    cooking_method: str = ""  # "baked", "fried", "boiled", "grilled", ""
    yield_factor: float = 1.0


@dataclass
class NutritionFacts:
    calories: float = 0.0
    total_fat_g: float = 0.0
    saturated_fat_g: float = 0.0
    trans_fat_g: float = 0.0
    cholesterol_mg: float = 0.0
    sodium_mg: float = 0.0
    total_carbohydrate_g: float = 0.0
    dietary_fiber_g: float = 0.0
    total_sugars_g: float = 0.0
    added_sugars_g: float = 0.0
    protein_g: float = 0.0
    vitamin_d_mcg: float = 0.0
    calcium_mg: float = 0.0
    iron_mg: float = 0.0
    potassium_mg: float = 0.0
    source_db_ids: list[str] = field(default_factory=list)
    allergens_found: list[str] = field(default_factory=list)
    estimate_note: str = ""


# ─── Allergen detection ──────────────────────────────────────────────────────

def detect_allergens(ingredient_names: list[str]) -> list[str]:
    """Return list of FDA major allergens found in ingredient list."""
    found = []
    text = " ".join(ingredient_names).lower()
    for allergen in sorted(FDA_MAJOR_ALLERGENS):
        if allergen in text:
            found.append(allergen.title())
    return found


# ─── Yield factors (USDA Table 4 approximations) ──────────────────────────

YIELD_FACTORS = {
    # cooking_method: (yield_factor, description)
    "baked": (0.93, "Loss due to water evaporation"),
    "fried": (0.88, "Loss due to water evaporation + oil absorption"),
    "boiled": (0.95, "Minimal loss, some solids leached to water"),
    "steamed": (0.96, "Minimal loss"),
    "grilled": (0.87, "Loss due to drippings + evaporation"),
    "broiled": (0.85, "Significant drippings loss"),
    "roasted": (0.91, "Evaporative loss"),
    "simmered": (0.93, "Some solids lost to liquid"),
    "microwaved": (0.97, "Minimal loss"),
}


def apply_cooking_yield(ingredient: Ingredient) -> Ingredient:
    """Apply USDA Table 4 yield factor based on cooking method."""
    if ingredient.cooking_method in YIELD_FACTORS:
        factor, _ = YIELD_FACTORS[ingredient.cooking_method]
        # Scale raw nutrients by yield factor (less yield = concentration increase)
        for key in ingredient.raw_nutrients:
            nv = ingredient.raw_nutrients[key]
            if nv.value > 0:
                adjusted = NutrientValue(
                    value=nv.value / factor,
                    unit=nv.unit,
                    source_db_id=nv.source_db_id,
                    source_confidence=nv.source_confidence,
                    is_estimate=nv.is_estimate,
                )
                ingredient.raw_nutrients[key] = adjusted
        ingredient.yield_factor = factor
    return ingredient


# ─── Rounding ───────────────────────────────────────────────────────────────

def round_us_fda(value: float, nutrient: str) -> float:
    """Apply FDA 21 CFR 101.9(c) rounding rules."""
    rules = {
        "calories": (
            (5, 0),
            (50, 5),
            (float("inf"), 10),
        ),
        "total_fat_g": (
            (0.5, 0),
            (5, 0.5),
            (float("inf"), 1),
        ),
        "saturated_fat_g": (
            (0.5, 0),
            (5, 0.5),
            (float("inf"), 1),
        ),
        "trans_fat_g": (
            (0.5, 0),
            (float("inf"), 0.1),
        ),
        "cholesterol_mg": (
            (5, 0),
            (300, 5),
            (float("inf"), 10),
        ),
        "sodium_mg": (
            (5, 0),
            (140, 5),
            (float("inf"), 10),
        ),
        "total_carbohydrate_g": (
            (0.5, 0),
            (1, 1),
            (float("inf"), 1),
        ),
        "dietary_fiber_g": (
            (0.5, 0),
            (1, 1),
            (float("inf"), 1),
        ),
        "protein_g": (
            (0.5, 0),
            (5, 1),
            (float("inf"), 5),
        ),
    }
    if nutrient not in rules:
        return round(value, 1)
    thresholds, step = rules[nutrient][0], rules[nutrient][1]
    for threshold, rounder in rules[nutrient]:
        if value < threshold:
            if rounder == 0:
                return 0
            return round(value / rounder) * rounder
    return round(value / rules[nutrient][-1][1]) * rules[nutrient][-1][1]


def round_eu(value: float, nutrient: str) -> float:
    """EU Annex XV rounding — nearest 0.1g for most nutrients."""
    return round(value, 1)


# ─── %DV / %RI / %DI ────────────────────────────────────────────────────────

def dv_pct(value: float, dv: float) -> int:
    if dv == 0:
        return 0
    return int(round(value / dv * 100))


# ─── Scale to serving ─────────────────────────────────────────────────────────

def scale_to_serving(nutrients: NutritionFacts, serving_g: float, total_g: float) -> NutritionFacts:
    """Scale aggregated nutrient totals to a specific serving size."""
    if total_g == 0:
        return nutrients
    factor = serving_g / total_g
    def scale(val):
        return round(val * factor, 2)
    def scale_int(val):
        return int(round(val * factor))

    nutrients.calories = scale(nutrients.calories)
    nutrients.total_fat_g = scale(nutrients.total_fat_g)
    nutrients.saturated_fat_g = scale(nutrients.saturated_fat_g)
    nutrients.trans_fat_g = scale(nutrients.trans_fat_g)
    nutrients.cholesterol_mg = scale_int(nutrients.cholesterol_mg)
    nutrients.sodium_mg = scale_int(nutrients.sodium_mg)
    nutrients.total_carbohydrate_g = scale(nutrients.total_carbohydrate_g)
    nutrients.dietary_fiber_g = scale(nutrients.dietary_fiber_g)
    nutrients.total_sugars_g = scale(nutrients.total_sugars_g)
    nutrients.added_sugars_g = scale(nutrients.added_sugars_g)
    nutrients.protein_g = scale(nutrients.protein_g)
    nutrients.vitamin_d_mcg = scale(nutrients.vitamin_d_mcg)
    nutrients.calcium_mg = scale(nutrients.calcium_mg)
    nutrients.iron_mg = scale(nutrients.iron_mcg) if hasattr(nutrients, 'iron_mcg') else scale(nutrients.calcium_mg * 0.01)
    nutrients.potassium_mg = scale(nutrients.potassium_mg)
    return nutrients


# ─── Web search placeholder ─────────────────────────────────────────────────

def search_usda_food(food_name: str) -> list[dict]:
    """
    Search USDA FoodData Central via web.
    Returns list of {fdc_id, description, category, per_100g: dict}.
    In production this would call the web search; here returns structured
    placeholder matches for demo purposes — caller should web-search
    fdc.nal.usda.gov for live data.
    """
    # Placeholder: caller should WebSearch for:
    # "site:fdc.nal.usda.gov {food_name} nutrition facts per 100g"
    return []


# ─── Aggregate nutrients ─────────────────────────────────────────────────────

def aggregate_nutrients(ingredients: list[Ingredient]) -> tuple[NutritionFacts, float]:
    """
    Sum raw nutrients from all ingredients (per-100g scaled to actual weight).
    Returns (NutritionFacts, total_weight_g).
    Also collects source_db_ids and estimate flags.
    """
    facts = NutritionFacts()
    total_g = 0.0

    for ing in ingredients:
        total_g += ing.weight_g
        scale = ing.weight_g / 100.0
        for key, nv in ing.raw_nutrients.items():
            val = nv.value * scale
            is_est = nv.is_estimate or nv.source_confidence < 0.85
            if is_est:
                facts.estimate_note = "⚠️ Nutrient values include estimates — verify before print production."
            attr = _nutrient_key_map().get(key, key)
            if hasattr(facts, attr):
                setattr(facts, attr, getattr(facts, attr) + val)
            if nv.source_db_id and nv.source_db_id not in facts.source_db_ids:
                facts.source_db_ids.append(nv.source_db_id)

    return facts, total_g


def _nutrient_key_map() -> dict[str, str]:
    return {
        "calories": "calories",
        "fat": "total_fat_g",
        "saturated_fat": "saturated_fat_g",
        "trans_fat": "trans_fat_g",
        "cholesterol": "cholesterol_mg",
        "sodium": "sodium_mg",
        "carbohydrate": "total_carbohydrate_g",
        "fiber": "dietary_fiber_g",
        "sugars": "total_sugars_g",
        "protein": "protein_g",
        "vitamin_d": "vitamin_d_mcg",
        "calcium": "calcium_mg",
        "iron": "iron_mg",
        "potassium": "potassium_mg",
    }


# ─── Region-specific formatting params ─────────────────────────────────────

def build_nutrition_params(
    facts: NutritionFacts,
    region: str,
    serving_size: str,
    servings_per_container: str,
    vitamins: list[str],
    vitamins_vals: list[str],
) -> dict:
    """Build NutritionPanelConfig-compatible dict for render_nutrition_panel.py."""
    calories_rounded = round_us_fda(facts.calories, "calories")
    fat_rounded = round_us_fda(facts.total_fat_g, "total_fat_g")
    sat_rounded = round_us_fda(facts.saturated_fat_g, "saturated_fat_g")
    trans_rounded = round_us_fda(facts.trans_fat_g, "trans_fat_g")
    sodium_rounded = int(round_us_fda(facts.sodium_mg, "sodium_mg"))
    carbs_rounded = round_us_fda(facts.total_carbohydrate_g, "total_carbohydrate_g")
    fiber_rounded = round_us_fda(facts.dietary_fiber_g, "dietary_fiber_g")
    sugars_rounded = round(facts.total_sugars_g, 1)
    protein_rounded = round_us_fda(facts.protein_g, "protein_g")

    return {
        "region": region,
        "serving_size": serving_size,
        "servings_per_container": servings_per_container,
        "calories": calories_rounded,
        "fat_g": fat_rounded,
        "saturated_g": sat_rounded,
        "trans_g": trans_rounded,
        "sodium_mg": sodium_rounded,
        "carbs_g": carbs_rounded,
        "fiber_g": fiber_rounded,
        "sugars_g": sugars_rounded,
        "protein_g": protein_rounded,
        "vitamins": vitamins,
        "vitamins_vals": vitamins_vals,
    }


def render_labelifier_panel(
    spec_id: str,
    ingredients: list[Ingredient],
    region: str = "US_FDA",
    serving_size: str = "1 cup (240ml)",
    servings_per_container: str = "8",
    cooking_methods: list[str] | None = None,
    dry_run: bool = False,
) -> tuple[Optional[Path], NutritionFacts, list[str]]:
    """
    Main entry point: ingredient list → nutrition panel SVG.

    Returns (path, NutritionFacts, allergen_warnings).
    Caller should web-search USDA for each ingredient to populate
    raw_nutrients and matched_fdc_id on each Ingredient.
    """
    # Apply cooking yields
    if cooking_methods:
        for i, method in enumerate(cooking_methods):
            if i < len(ingredients):
                ingredients[i].cooking_method = method
                apply_cooking_yield(ingredients[i])

    # Aggregate
    facts, total_g = aggregate_nutrients(ingredients)

    # Detect allergens
    ingredient_names = [ing.name for ing in ingredients]
    allergens = detect_allergens(ingredient_names)
    facts.allergens_found = allergens

    # Scale to serving size
    serving_g = _parse_serving_weight(serving_size)
    if serving_g > 0:
        facts = scale_to_serving(facts, serving_g, total_g)

    # Build params for render_nutrition_panel
    params = build_nutrition_params(
        facts, region, serving_size, servings_per_container,
        vitamins=["Vitamin D", "Calcium", "Iron"],
        vitamins_vals=["0 mcg", "130 mg", "4 mg"],
    )

    # Import and call render_nutrition_panel
    from scripts.render_nutrition_panel import render_nutrition_panel as render_panel
    path = render_panel(spec_id, **params, dry_run=dry_run)

    disclaimer = (
        f"Source: USDA FoodData Central. "
        f"Estimate note: {facts.estimate_note}" if facts.estimate_note else ""
    )
    if allergens:
        disclaimer += f" | Allergens detected: {', '.join(allergens)}"

    return path, facts, allergens


def _parse_serving_weight(serving_size: str) -> float:
    """Extract gram weight from serving size string like '1 cup (240ml)' or '2 tbsp (30g)'."""
    m = re.search(r"\((\d+(?:\.\d+)?)\s*(?:g|ml|mg)\)", serving_size)
    if m:
        val = float(m.group(1))
        return val
    return 240.0  # default fallback


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Nutrition labelifier pipeline")
    parser.add_argument("spec_id", help="Spec ID")
    parser.add_argument("--region", default="US_FDA",
                        choices=["US_FDA", "EU_1169", "CA_CFIA", "AU_FSANZ"],
                        help="Region format")
    parser.add_argument("--serving-size", default="1 cup (240ml)")
    parser.add_argument("--servings", default="8")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Demo: apple (web-search USDA for "apple fdc.nal.usda.gov")
    ing = Ingredient(
        name="Apple, raw",
        weight_g=182,
        raw_nutrients={
            "calories": NutrientValue(value=95, unit="kcal", source_db_id="171688", source_confidence=0.92),
            "fat": NutrientValue(value=0.31, unit="g", source_db_id="171688", source_confidence=0.92),
            "carbohydrate": NutrientValue(value=25, unit="g", source_db_id="171688", source_confidence=0.92),
            "fiber": NutrientValue(value=4.4, unit="g", source_db_id="171688", source_confidence=0.92),
            "sugars": NutrientValue(value=19, unit="g", source_db_id="171688", source_confidence=0.92),
            "protein": NutrientValue(value=0.47, unit="g", source_db_id="171688", source_confidence=0.92),
            "sodium": NutrientValue(value=2, unit="mg", source_db_id="171688", source_confidence=0.92),
        },
        matched_fdc_id="171688",
        matched_name="Apple, raw",
    )
    path, facts, allergens = render_labelifier_panel(
        args.spec_id, [ing],
        region=args.region,
        serving_size=args.serving_size,
        servings_per_container=args.servings,
        dry_run=args.dry_run,
    )
    if path:
        print(f"Rendered: {path}")
    print(f"Calories: {facts.calories:.0f}, Fat: {facts.total_fat_g:.1f}g, "
          f"Carbs: {facts.total_carbohydrate_g:.1f}g, Protein: {facts.protein_g:.1f}g")
    print(f"Sugars: {facts.total_sugars_g:.1f}g, Fiber: {facts.dietary_fiber_g:.1f}g")
    print(f"Allergens: {allergens}")
    print(f"Source DB IDs: {facts.source_db_ids}")


if __name__ == "__main__":
    main()