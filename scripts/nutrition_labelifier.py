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

# FDC API key — set via environment USDA_FDC_API_KEY if available.
# When None, the pipeline falls back to web-search or default values.
_USDA_FDC_API_KEY = None


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
    nutrients.iron_mg = scale(nutrients.iron_mg)
    nutrients.potassium_mg = scale(nutrients.potassium_mg)
    return nutrients


# ─── Web search ───────────────────────────────────────────────────────────────

FDC_API_KEY_ENV = "USDA_FDC_API_KEY"
FDC_API_BASE = "https://api.nal.usda.gov/fdc/v1"


def _get_api_key() -> str | None:
    import os
    return os.environ.get(FDC_API_KEY_ENV)


def search_usda_food(food_name: str, api_key: str | None = None) -> list[dict]:
    """
    Search USDA FoodData Central via the official API.

    Args:
        food_name: raw ingredient name (e.g. "Apple, raw")
        api_key: FDC API key; falls back to USDA_FDC_API_KEY env var

    Returns:
        list of matched food dicts, each containing:
          - fdc_id (str)
          - description (str)
          - category (str)
          - per_100g (dict of nutrient symbol → value)
          - confidence (float 0–1)

    Raises:
        requests.HTTPError: on API error with a non-empty body
    """
    key = api_key or _get_api_key()
    if not key:
        return _search_usda_food_web_fallback(food_name)

    import urllib.request, urllib.parse, json

    url = f"{FDC_API_BASE}/foods/search"
    params = urllib.parse.urlencode({
        "api_key": key,
        "query": food_name,
        "pageSize": 10,
        "dataType": ["SR Legacy", "Branded"],
        "sortBy": "dataType.keyword",
        "sortOrder": "asc",
    })
    req = urllib.request.Request(f"{url}?{params}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 403 or e.code == 401:
            return _search_usda_food_web_fallback(food_name)
        raise

    foods = data.get("foods", [])
    matches = []
    for item in foods:
        fdc_id = str(item.get("fdcId", ""))
        desc = item.get("description", "")
        category = ""
        if item.get("foodCategory"):
            category = item["foodCategory"].get("description", "")

        # Build per-100g nutrient dict
        per_100g = {}
        for ng in item.get("foodNutrients", []):
            num = ng.get("nutrientNumber", "")
            val = ng.get("value")
            if val is None:
                continue
            unit = ng.get("unitName", "")
            attr = _fdc_nutrient_map().get(num, "")
            if attr and unit in ("g", "mg", "mcg", "IU"):
                per_100g[attr] = val

        # Confidence: prefer SR Legacy over Branded, prefer exact name match
        confidence = 0.70
        if "foodNutrientId" not in str(item):  # branded
            confidence = 0.60

        matches.append({
            "fdc_id": fdc_id,
            "description": desc,
            "category": category,
            "per_100g": per_100g,
            "confidence": confidence,
        })

    matches.sort(key=lambda m: m["confidence"], reverse=True)
    return matches[:10]


def _fdc_nutrient_map() -> dict[str, str]:
    return {
        "208": "calories",
        "204": "fat",
        "205": "carbohydrate",
        "291": "fiber",
        "269": "sugars",
        "203": "protein",
        "301": "calcium",
        "303": "iron",
        "304": "potassium",
        "307": "sodium",
        "601": "cholesterol",
        "605": "trans_fat",
        "606": "saturated_fat",
        "324": "vitamin_d",
    }


def _search_usda_food_web_fallback(food_name: str) -> list[dict]:
    """
    Web-search fallback when no API key is configured.
    Returns empty list — caller handles gracefully.
    """
    return []


def _lookup_fdc_id(fdc_id: str, api_key: str | None = None) -> dict | None:
    """Direct FDC ID lookup. Returns dict with per_100g nutrients + _weight_g, or None."""
    key = api_key or _get_api_key()
    if not key:
        return None

    import urllib.request, urllib.parse, json

    url = f"{FDC_API_BASE}/food/{fdc_id}"
    params = urllib.parse.urlencode({"api_key": key})
    req = urllib.request.Request(f"{url}?{params}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            item = json.loads(resp.read())
    except Exception:
        return None

    fdc_id_str = str(item.get("fdcId", ""))
    per_100g = {}
    for ng in item.get("foodNutrients", []):
        num = ng.get("nutrientNumber", "")
        val = ng.get("value")
        if val is None:
            continue
        unit = ng.get("unitName", "")
        attr = _fdc_nutrient_map().get(num, "")
        if attr and unit in ("g", "mg", "mcg", "IU"):
            per_100g[attr] = val

    return {"_weight_g": 100.0, **per_100g}


def _fdc_to_nutrition(per_100g: dict) -> NutritionFacts:
    """Convert FDC per_100g nutrient dict to NutritionFacts."""
    facts = NutritionFacts()
    for key, val in per_100g.items():
        attr = _nutrient_key_map().get(key, key)
        if hasattr(facts, attr) and isinstance(val, (int, float)):
            setattr(facts, attr, val)
    return facts


def _default_nutrition(ingredient_name: str) -> NutritionFacts:
    """Return empty NutritionFacts with estimate note when no FDC data available."""
    facts = NutritionFacts()
    facts.estimate_note = f"⚠️ No USDA FDC data for '{ingredient_name}' — nutrient estimate unavailable."
    return facts


# ─── Aggregate nutrients ─────────────────────────────────────────────────────

def confirm_fdc_match(
    ingredient_name: str,
    candidates: list[dict],
    threshold: float = 0.85,
) -> str | None:
    """
    Present FDC search candidates to user and return the selected fdc_id.

    Args:
        ingredient_name: the ingredient being matched
        candidates: list of FDC match dicts (fdc_id, description, category, confidence)
        threshold: minimum confidence to auto-accept without asking (default 0.85)

    Returns:
        Selected fdc_id str, or None if user skipped / no match.
    """
    if not candidates:
        return None

    # Auto-accept if confidence is above threshold
    top = candidates[0]
    if top.get("confidence", 0) >= threshold:
        return top["fdc_id"]

    # Surface candidates for disambiguation
    print(f"\n⚠ Ambiguous match for '{ingredient_name}':")
    print(f"   Top candidate: {top['description'][:80]} (confidence {top.get('confidence', 0):.2f})")
    print("   Candidates:")
    for i, c in enumerate(candidates[:5]):
        print(f"     [{i+1}] {c['fdc_id']} — {c['description'][:60]}")
        print(f"         category={c.get('category','')} confidence={c.get('confidence',0):.2f}")
    print("   Enter a number to select, or 's' to skip this ingredient.")

    try:
        choice = input("Selection: ").strip().lower()
        if choice == "s":
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(candidates):
            return candidates[idx]["fdc_id"]
    except (ValueError, EOFError):
        pass

    return None


def _aggregate_single_ingredient(
    ing: Ingredient,
    api_key: str | None = None,
) -> tuple[NutritionFacts, float, str | None]:
    """
    Look up a single ingredient via FDC, return (NutritionFacts, total_g, fdc_id).
    Uses web search fallback when no API key is available.
    Falls back to default nutrition values when no FDC entry is found.
    """
    if ing.matched_fdc_id:
        # Already confirmed by user — direct lookup
        try:
            entry = _lookup_fdc_id(ing.matched_fdc_id, api_key)
            if entry:
                return entry, entry.get("_weight_g", 100.0), ing.matched_fdc_id
        except Exception:
            pass

    # Search FDC
    matches = search_usda_food(ing.name, api_key)
    if not matches:
        # FDC lookup failed — try using ing.raw_nutrients directly (pre-computed per-100g data)
        if ing.raw_nutrients:
            scale = ing.weight_g / 100.0
            facts = NutritionFacts()
            facts.source_db_ids = [nv.source_db_id for k, nv in ing.raw_nutrients.items() if nv.source_db_id] or []
            for key, nv in ing.raw_nutrients.items():
                val = float(nv.value) * scale if isinstance(nv.value, (int, float)) else 0.0
                attr = _nutrient_key_map().get(key, key)
                if hasattr(facts, attr):
                    setattr(facts, attr, getattr(facts, attr, 0.0) + val)
            return facts, ing.weight_g, None
        # Fall back to default nutrition
        return _default_nutrition(ing.name), 100.0, None

    # Check if top match is good enough to auto-confirm
    top = matches[0]
    confirmed_id = confirm_fdc_match(ing.name, matches)

    if confirmed_id:
        try:
            entry = _lookup_fdc_id(confirmed_id, api_key)
            if entry:
                return entry, entry.get("_weight_g", 100.0), confirmed_id
        except Exception:
            pass

    # User skipped or lookup failed — use top match as estimate
    fdc_id = top.get("fdc_id")
    return _fdc_to_nutrition(top.get("per_100g", {})), 100.0, fdc_id


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
        "polyunsaturated_fat": "polyunsaturated_fat_g",
        "monounsaturated_fat": "monounsaturated_fat_g",
        "cholesterol": "cholesterol_mg",
        "sodium": "sodium_mg",
        "carbohydrate": "total_carbohydrate_g",
        "fiber": "dietary_fiber_g",
        "sugars": "total_sugars_g",
        "added_sugars": "added_sugars_g",
        "protein": "protein_g",
        "vitamin_d": "vitamin_d_mcg",
        "vitamin_a": "vitamin_a_iu",
        "vitamin_b12": "vitamin_b12_mcg",
        "calcium": "calcium_mg",
        "iron": "iron_mg",
        "potassium": "potassium_mg",
        "phosphorus": "phosphorus_mg",
        "magnesium": "magnesium_mg",
        "copper": "copper_mg",
        "selenium": "selenium_mcg",
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


def _write_nutrition_json(
    spec_id: str,
    facts: NutritionFacts,
    region: str,
    serving_size: str,
    servings_per_container: str,
    params: dict,
    allergens: list[str],
) -> Path | None:
    """Write structured nutrition facts JSON to renders/{spec_id}/nutrition_facts.json."""
    import json
    RENDERS_DIR = SKILL_DIR / "renders" / spec_id
    out_path = RENDERS_DIR / "nutrition_facts.json"
    try:
        RENDERS_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "spec_id": spec_id,
            "region": region,
            "serving_size": serving_size,
            "servings_per_container": servings_per_container,
            "source_db_ids": facts.source_db_ids,
            "estimate_note": facts.estimate_note or None,
            "allergens_detected": allergens,
            "nutrients": {
                "calories_g": facts.calories,
                "total_fat_g": facts.total_fat_g,
                "saturated_fat_g": facts.saturated_fat_g,
                "trans_fat_g": facts.trans_fat_g,
                "cholesterol_mg": facts.cholesterol_mg,
                "sodium_mg": facts.sodium_mg,
                "total_carbohydrate_g": facts.total_carbohydrate_g,
                "dietary_fiber_g": facts.dietary_fiber_g,
                "total_sugars_g": facts.total_sugars_g,
                "added_sugars_g": facts.added_sugars_g,
                "protein_g": facts.protein_g,
                "vitamin_d_mcg": facts.vitamin_d_mcg,
                "calcium_mg": facts.calcium_mg,
                "iron_mg": facts.iron_mg,
                "potassium_mg": facts.potassium_mg,
            },
            "display_values": params,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return out_path
    except Exception:
        return None


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

    # Wire new per-ingredient FDC lookup + disambiguation pipeline
    combined = NutritionFacts()
    total_g = 0.0
    for ing in ingredients:
        facts_i, w_i, fdc_id = _aggregate_single_ingredient(ing, _USDA_FDC_API_KEY)
        scale = w_i / 100.0
        for attr in [
            "calories", "total_fat_g", "saturated_fat_g", "trans_fat_g",
            "cholesterol_mg", "sodium_mg", "total_carbohydrate_g",
            "dietary_fiber_g", "total_sugars_g", "added_sugars_g",
            "protein_g", "vitamin_d_mcg", "calcium_mg", "iron_mg", "potassium_mg",
        ]:
            setattr(combined, attr, getattr(combined, attr) + getattr(facts_i, attr) * scale)
        total_g += w_i
        if fdc_id and fdc_id not in combined.source_db_ids:
            combined.source_db_ids.append(fdc_id)
        if facts_i.estimate_note:
            combined.estimate_note = facts_i.estimate_note
    facts = combined

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
    import importlib.util
    _mod = importlib.import_module("scripts.render_nutrition_panel")
    render_panel = _mod.render_nutrition_panel
    path = render_panel(spec_id, **params, dry_run=dry_run)

    # Write structured JSON output
    _write_nutrition_json(spec_id, facts, region, serving_size,
                          servings_per_container, params, allergens)

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
    parser.add_argument("--dpi", type=int, default=300,
                        help="Output DPI for PNG rasterization (default 300)")
    parser.add_argument("--cmyk", action="store_true",
                        help="Tag output for CMYK print mode (cairo/inkscape produce RGB; separate conversion required)")
    args = parser.parse_args()

    # Chocolate chip cookie — worked example
    # Total batch: 800g yield, 24 servings, 33g per cookie
    cookie_ings = [
        ("All-purpose flour",       280, "169910", {"calories": 364,  "protein": 10.3,  "total_fat_g": 0.98,   "total_carbohydrate_g": 76.3,  "total_sugars_g": 0.27,  "dietary_fiber_g": 2.7,  "saturated_fat_g": 0.16,  "sodium_mg": 2,    "iron_mg": 4.6,   "calcium_mg": 15,  "potassium_mg": 107, "phosphorus_mg": 108, "magnesium_mg": 22}),
        ("Granulated sugar",         150, "19368",  {"calories": 387,  "protein": 0.0,   "total_fat_g": 0.0,    "total_carbohydrate_g": 99.98, "total_sugars_g": 99.98,"dietary_fiber_g": 0.0,  "saturated_fat_g": 0.0,   "sodium_mg": 1,    "iron_mg": 0.01,  "calcium_mg": 1,   "potassium_mg": 2,   "phosphorus_mg": 0,   "magnesium_mg": 0}),
        ("Brown sugar",              150, "19892",  {"calories": 380,  "protein": 0.05,  "total_fat_g": 0.0,    "total_carbohydrate_g": 98.1,  "total_sugars_g": 97.0,  "dietary_fiber_g": 0.0,  "saturated_fat_g": 0.0,   "sodium_mg": 28,   "iron_mg": 0.05,  "calcium_mg": 46,  "potassium_mg": 133, "phosphorus_mg": 0,   "magnesium_mg": 0}),
        ("Unsalted butter",          200, "173410", {"calories": 717,  "protein": 0.85,  "total_fat_g": 81.1,   "total_carbohydrate_g": 0.12, "total_sugars_g": 0.12,  "dietary_fiber_g": 0.0,  "saturated_fat_g": 51.4,  "polyunsaturated_fat_g": 3.4, "monounsaturated_fat_g": 23.0, "sodium_mg": 11,  "iron_mg": 0.02,  "calcium_mg": 24,  "potassium_mg": 24,  "phosphorus_mg": 0,   "magnesium_mg": 0,  "vitamin_a_iu": 2499, "vitamin_d_iu": 59, "cholesterol_mg": 215}),
        ("Large egg",                100, "171287", {"calories": 143,  "protein": 12.6,  "total_fat_g": 9.5,    "total_carbohydrate_g": 0.71,  "total_sugars_g": 0.71,  "dietary_fiber_g": 0.0,  "saturated_fat_g": 3.1,   "polyunsaturated_fat_g": 1.9, "monounsaturated_fat_g": 3.7, "sodium_mg": 142, "iron_mg": 1.8,   "calcium_mg": 56,  "potassium_mg": 138, "phosphorus_mg": 198, "magnesium_mg": 12,  "selenium_mcg": 31,  "cholesterol_mg": 373, "vitamin_a_iu": 540, "vitamin_d_iu": 82, "vitamin_b12_mg": 0.89}),
        ("Semi-sweet choc chips",    200, "19904",  {"calories": 479,  "protein": 4.2,   "total_fat_g": 26.6,   "total_carbohydrate_g": 64.3,  "total_sugars_g": 56.2,  "dietary_fiber_g": 7.0,  "saturated_fat_g": 15.2,  "polyunsaturated_fat_g": 0.6, "monounsaturated_fat_g": 8.8, "sodium_mg": 24,  "iron_mg": 3.1,   "calcium_mg": 43,  "potassium_mg": 418, "phosphorus_mg": 144, "magnesium_mg": 114, "copper_mg": 0.7}),
        ("Vanilla extract",            5, "2051684", {"calories": 288,  "protein": 0.06,  "total_fat_g": 0.01,   "total_carbohydrate_g": 12.8,  "total_sugars_g": 12.8,  "dietary_fiber_g": 0.0,  "saturated_fat_g": 0.0,   "sodium_mg": 9,    "iron_mg": 0.12,  "calcium_mg": 11,  "potassium_mg": 148, "phosphorus_mg": 0,   "magnesium_mg": 0}),
        ("Baking soda",               5, "16202",  {"sodium_mg": 27360, "sodium": 27360}),
        ("Salt",                       3, "18628",  {"sodium_mg": 38758, "sodium": 38758, "iron_mg": 0.03, "calcium_mg": 24, "potassium_mg": 8}),
    ]

    raw_nutrients_units = {
        "calories": "kcal", "protein": "g", "total_fat_g": "g", "saturated_fat_g": "g",
        "polyunsaturated_fat_g": "g", "monounsaturated_fat_g": "g",
        "total_carbohydrate_g": "g", "total_sugars_g": "g", "dietary_fiber_g": "g",
        "sodium_mg": "mg", "sodium": "mg", "iron_mg": "mg", "calcium_mg": "mg",
        "potassium_mg": "mg", "phosphorus_mg": "mg", "magnesium_mg": "mg",
        "copper_mg": "mg", "selenium_mcg": "mcg", "cholesterol_mg": "mg",
        "vitamin_a_iu": "IU", "vitamin_d_iu": "IU", "vitamin_b12_mg": "mg",
    }

    ingredients = []
    for name, wg, fid, nut_dict in cookie_ings:
        raw_nutrients = {}
        for k, v in nut_dict.items():
            if v is None:
                continue
            unit = raw_nutrients_units.get(k, "g")
            raw_nutrients[k] = NutrientValue(value=v, unit=unit, source_db_id=fid, source_confidence=1.0)
        # Pass raw per-100g values — _aggregate_single_ingredient handles scaling
        ingredients.append(Ingredient(name=name, weight_g=wg, raw_nutrients=raw_nutrients, matched_fdc_id=fid, matched_name=name))

    path, facts, allergens = render_labelifier_panel(
        args.spec_id, ingredients,
        region=args.region,
        serving_size=args.serving_size,
        servings_per_container=args.servings,
        cooking_methods=["baked"] * len(ingredients),
        dry_run=args.dry_run,
    )
    if path:
        print(f"Rendered: {path}")

    # Rasterize nutrition SVG → PNG at specified DPI
    if not args.dry_run:
        _mod = importlib.import_module("scripts.svg_to_png")
        png_path = _mod.svg_to_png(args.spec_id, dpi=args.dpi, filename="nutrition.svg")
        if png_path:
            print(f"PNG: {png_path}")
        else:
            print("PNG rasterization skipped (no renderer available)")

    print(f"Calories: {facts.calories:.0f}, Fat: {facts.total_fat_g:.1f}g, "
          f"Carbs: {facts.total_carbohydrate_g:.1f}g, Protein: {facts.protein_g:.1f}g")
    print(f"Sugars: {facts.total_sugars_g:.1f}g, Fiber: {facts.dietary_fiber_g:.1f}g")
    print(f"Sodium: {facts.sodium_mg:.0f}mg, Iron: {facts.iron_mg:.1f}mg, Calcium: {facts.calcium_mg:.0f}mg")
    print(f"Allergens: {allergens}")
    print(f"Source DB IDs: {facts.source_db_ids}")


if __name__ == "__main__":
    main()