#!/usr/bin/env python3
"""
logo_generator.py — Strategic logo type recommendation and creative brief generation.

Implements the Professional Product Label Generator's logo/brand identity framework:
  - Seven logo types (Pictorial, Letter Mark, Word Mark, Combination, Emblem, Abstract, Mascot)
  - Four brand architecture models (Branded House, Sub-Brands, Endorsed Brands, House of Brands)
  - 12-section output: diagnosis → architecture → logo type → alignment → front panel →
    visual direction → emotional trigger → scalability → copy framework → Logo System Bible →
    stress test → creative brief

Usage:
  python3 logo_generator.py diagnose "Brand Name" "Product Name" [--category C] [--audience A]
  python3 logo_generator.py generate [--brand B] [--product P] [--category C] [...]
  python3 logo_generator.py brief  (interactive)
"""

import argparse
import sys
import textwrap
import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

SKILL_DIR = Path.home() / ".claude" / "skills" / "label-design"
LOGOS_DIR = SKILL_DIR / "logos"


# ─────────────────────────────────────────────────────────────────────────────
# Logo Types
# ─────────────────────────────────────────────────────────────────────────────

class LogoType(Enum):
    PICTORIAL = "Pictorial Mark"
    LETTER_MARK = "Letter Mark or Monogram"
    WORD_MARK = "Word Mark or Logotype"
    COMBINATION = "Combination Mark"
    EMBLEM = "Emblem"
    ABSTRACT = "Abstract Mark"
    MASCOT = "Mascot"


LOGO_TYPE_DESCRIPTIONS = {
    LogoType.PICTORIAL: (
        "A single recognizable image carries the brand identity. "
        "Use when the brand essence can be visually distilled into an ownable, memorable image. "
        "Best for brands with a clear object, symbol, ingredient, origin story, animal, "
        "natural element, or iconic visual metaphor."
    ),
    LogoType.LETTER_MARK: (
        "Initials become the identity. "
        "Use when the brand name is long, technical, multi-word, difficult to fit on packaging, "
        "or needs faster recall. "
        "Best for premium, corporate, technical, institutional, fashion, beauty, "
        "or professional brands with long names."
    ),
    LogoType.WORD_MARK: (
        "Typography alone carries the brand. "
        "Use when the brand name is short, distinctive, memorable, and visually strong. "
        "Best for brands where the name itself is the main asset and the type treatment "
        "can become the visual signature."
    ),
    LogoType.COMBINATION: (
        "Text and symbol work together. "
        "Use when the brand needs maximum flexibility, recognition, and future evolution. "
        "Best for new brands, growing product lines, ecommerce-first products, retail packaging, "
        "and brands that may later simplify to a standalone symbol."
    ),
    LogoType.EMBLEM: (
        "Text is enclosed within a badge, crest, seal, shield, or contained mark. "
        "Use when the brand needs to communicate heritage, authority, trust, tradition, "
        "craftsmanship, certification, or institutional credibility. "
        "Best for luxury goods, coffee, alcohol, heritage foods, schools, clubs, official products, "
        "premium grooming, and artisanal brands."
    ),
    LogoType.ABSTRACT: (
        "A non-literal symbol carries the identity. "
        "Use when the brand wants a unique, ownable, modern, conceptual, or future-facing identity. "
        "Best for innovation-driven brands, tech-enabled products, modern wellness, "
        "design-led goods, and brands willing to invest in storytelling and consistent meaning-building."
    ),
    LogoType.MASCOT: (
        "A character represents the brand. "
        "Use when the brand needs personality, friendliness, emotional warmth, humor, "
        "or direct customer connection. "
        "Best for family-friendly products, snacks, beverages, pet products, children's goods, "
        "casual consumer brands, and brands that benefit from repeat character interaction."
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Brand Architecture
# ─────────────────────────────────────────────────────────────────────────────

class BrandArchitecture(Enum):
    BRANDED_HOUSE = "Branded House"
    SUB_BRANDS = "Sub-Brands"
    ENDORSED_BRANDS = "Endorsed Brands"
    HOUSE_OF_BRANDS = "House of Brands"


ARCHITECTURE_DESCRIPTIONS = {
    BrandArchitecture.BRANDED_HOUSE: (
        "One master brand supports multiple products or services. "
        "Use when unity, trust transfer, cross-selling, and master-brand recognition "
        "are more important than individual product independence. "
        "Label implication: the master brand should dominate the label. "
        "Product names should appear as variants, lines, formulas, flavors, or editions "
        "under the main brand."
    ),
    BrandArchitecture.SUB_BRANDS: (
        "A parent brand supports distinct product lines with their own names or identities. "
        "Use when products serve different audiences or use cases but still share core brand values. "
        "Label implication: both parent brand and sub-brand must be visible. "
        "The sub-brand may have its own visual personality, "
        "but it must remain connected to the parent system."
    ),
    BrandArchitecture.ENDORSED_BRANDS: (
        "Semi-independent brands receive credibility from a parent brand. "
        "Use when the product brand needs its own market identity "
        "but benefits from parent-brand trust. "
        "Label implication: the product brand should lead, "
        "while the parent endorsement appears as a secondary trust signal, "
        "such as 'by [Parent Brand]' or 'from the makers of [Parent Brand].'"
    ),
    BrandArchitecture.HOUSE_OF_BRANDS: (
        "Multiple independent brands operate under one corporate owner "
        "with little or no visible connection. "
        "Use when each brand targets a distinct market, price point, audience, "
        "or category with minimal overlap. "
        "Label implication: the individual product brand should stand alone. "
        "Parent-company presence should be minimized or omitted unless legally required."
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Intake dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BrandIntake:
    brand_name: str = ""
    product_name: str = ""
    product_category: str = ""
    product_type: str = ""
    target_customer: str = ""
    price_positioning: str = ""  # budget, mid-market, premium, luxury
    brand_personality: str = ""
    emotional_response: str = ""  # trust, desire, calm, energy, indulgence, etc.
    sales_channel: str = ""  # retail, ecommerce, boutique, wholesale, marketplace, DTC
    parent_brand: str = ""
    portfolio_size: int = 1  # current number of products
    portfolio_future: int = 1  # expected future products
    is_sub_brand: bool = False
    required_claims: list[str] = field(default_factory=list)
    required_certifications: list[str] = field(default_factory=list)
    visual_preferences: str = ""
    competitors: str = ""

    def missing_fields(self) -> list[str]:
        fields = []
        if not self.brand_name:
            fields.append("brand_name")
        if not self.product_name:
            fields.append("product_name")
        if not self.product_category:
            fields.append("product_category")
        if not self.target_customer:
            fields.append("target_customer")
        if not self.price_positioning:
            fields.append("price_positioning")
        return fields


# ─────────────────────────────────────────────────────────────────────────────
# Logo Recommendation Engine
# ─────────────────────────────────────────────────────────────────────────────

def recommend_logo_type(intake: BrandIntake) -> tuple[LogoType, str]:
    """Recommend a logo type based on brand strategy logic."""

    # Long brand name → Letter Mark or Combination
    if len(intake.brand_name) > 20:
        return LogoType.LETTER_MARK, (
            "The brand name is long and would be difficult to render legibly at small label sizes. "
            "A monogram or letter mark provides fast recognition and scalable identity."
        )

    if len(intake.brand_name) > 12:
        if intake.price_positioning in ("premium", "luxury"):
            return LogoType.COMBINATION, (
                "A moderate-length name benefits from a combination mark that pairs a compact "
                "symbol with the full word mark, giving flexibility for premium label layouts."
            )
        return LogoType.LETTER_MARK, (
            "A monogram distills the brand name into a compact, ownable symbol "
            "that scales well across product labels."
        )

    # Brand needs warmth/personality → Mascot
    if intake.brand_personality.lower() in ("playful", "friendly", "warm", "humorous", "family"):
        return LogoType.MASCOT, (
            "The brand personality calls for warmth, humor, or emotional connection. "
            "A mascot character creates direct customer relationship and repeat engagement."
        )

    # Heritage / craft / artisanal → Emblem
    if intake.brand_personality.lower() in ("heritage", "traditional", "artisan", "craftsmanship"):
        return LogoType.EMBLEM, (
            "The brand needs to communicate heritage, authority, trust, or traditional craftsmanship. "
            "An emblem communicates institutional credibility and timelessness."
        )

    # Modern / tech / conceptual → Abstract
    if intake.brand_personality.lower() in ("innovative", "modern", "futuristic", "conceptual"):
        return LogoType.ABSTRACT, (
            "A modern, ownable symbol builds distinct brand meaning over time. "
            "An abstract mark works well for innovation-driven or tech-enabled products."
        )

    # New brand, no special constraints → Combination (safe default)
    if intake.portfolio_size <= 1 and intake.portfolio_future <= 3:
        return LogoType.COMBINATION, (
            "A new brand with growth potential benefits from a combination mark that provides "
            "both symbol recognition and word-mark recognition, with flexibility to simplify "
            "to a standalone symbol once the mark gains recognition."
        )

    # Short, distinctive name → Word Mark
    if len(intake.brand_name) <= 8:
        return LogoType.WORD_MARK, (
            "A short, distinctive name that is visually strong works well as a word mark, "
            "where the type treatment itself becomes the visual signature."
        )

    # Default: Combination
    return LogoType.COMBINATION, (
        "A combination mark provides maximum flexibility for label design, "
        "with both symbol and word-mark recognition that can evolve over time."
    )


def recommend_architecture(intake: BrandIntake) -> tuple[BrandArchitecture, str]:
    """Recommend brand architecture based on portfolio structure."""

    if intake.is_sub_brand:
        return (
            BrandArchitecture.SUB_BRANDS,
            "This product is a sub-brand and should be positioned within "
            "a sub-branding architecture that balances parent recognition with sub-brand distinction."
        )

    if intake.parent_brand:
        return (
            BrandArchitecture.ENDORSED_BRANDS,
            "An endorsed brand structure allows the product brand to lead "
            "while receiving credibility from the parent brand."
        )

    if intake.portfolio_size > 5 or intake.portfolio_future > 10:
        return (
            BrandArchitecture.BRANDED_HOUSE,
            "A broad product portfolio benefits from a branded house structure "
            "where the master brand dominates and variant products are clearly organized."
        )

    if intake.portfolio_size == 1:
        return (
            BrandArchitecture.BRANDED_HOUSE,
            "A single-product brand can establish its identity with a branded house structure "
            "that prepares for future portfolio expansion."
        )

    return (
        BrandArchitecture.BRANDED_HOUSE,
        "Defaulting to branded house for clarity and scalability."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Output Formatter
# ─────────────────────────────────────────────────────────────────────────────

def green(text: str) -> str:
    return f"\033[92m{text}\033[0m"


def yellow(text: str) -> str:
    return f"\033[93m{text}\033[0m"


def bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"


def section(num: int, title: str) -> str:
    return f"\n{'='*60}\n{bold(f'{num}. {title}')}\n{'='*60}"


def diagnose(intake: BrandIntake) -> str:
    """Generate Brand and Product Diagnosis section."""
    category_signal = {
        "food": ("health-conscious consumers", "taste and ingredient quality", "shelf visibility among alternatives"),
        "beverage": ("refreshment-seekers", "hydration or energy", "cooler or grab-and-go visibility"),
        "cosmetic": ("self-care focused buyers", "skin health and aesthetic appeal", "vanity and premium feel"),
        "supplement": ("health-conscious consumers", "efficacy and trust", "clinical credibility"),
        "household": ("practical households", "cleaning efficacy and safety", "utility shelf presence"),
        "tech": ("early adopters", "functionality and innovation", "feature comparison"),
        "artisan": ("conscious consumers", "authenticity and craftsmanship", "story and origin"),
    }

    cat_lower = intake.product_category.lower()
    diagnosis = category_signal.get(cat_lower, ("target customers", "product value", "market positioning"))
    logo, _ = recommend_logo_type(intake)
    arch, _ = recommend_architecture(intake)

    return f"""**Product Category:** {intake.product_category}
**Brand:** {intake.brand_name}
**Product:** {intake.product_name}
**Likely Target Buyer:** {intake.target_customer or diagnosis[0]}
**Primary Purchase Trigger:** {diagnosis[1]}
**Shelf or Screen Context:** {intake.sales_channel or "retail shelf / ecommerce listing"}
**Logo Type Recommendation:** {logo.value}
**Brand Architecture:** {arch.value}
**Main Trust Barrier:** Unfamiliar brand, unverified claims, or missing certification signals
**Main Differentiation Opportunity:** Distinctive visual identity, clear product claim, ownable brand mark"""


def stress_test(intake: BrandIntake, logo_type: LogoType, arch: BrandArchitecture) -> str:
    """Generate Strategic Stress Test section."""

    def rating(label: str, pass_: bool, note: str) -> str:
        icon = green("PASS") if pass_ else yellow("CAUTION")
        return f"  [{icon}] {label}: {note}"

    brand_short = len(intake.brand_name) <= 10
    has_symbol = logo_type in (LogoType.PICTORIAL, LogoType.COMBINATION, LogoType.ABSTRACT, LogoType.MASCOT)

    tests = []
    tests.append(rating(
        "5-Second Rule",
        True,
        f"Viewer should understand brand name and product category within 5 seconds."
    ))
    tests.append(rating(
        "1-Inch Test",
        brand_short or has_symbol,
        "Monogram or symbol mark remains legible at 1-inch scale; long word marks may suffer."
    ))
    tests.append(rating(
        "Black-and-White Test",
        logo_type not in (LogoType.MASCOT, LogoType.ABSTRACT),
        "Emblem, word mark, and combination work without color; mascot and abstract may lose impact."
    ))
    tests.append(rating(
        "Architecture Test",
        arch in (BrandArchitecture.BRANDED_HOUSE, BrandArchitecture.SUB_BRANDS),
        f"Architecture ({arch.value}) is {'visible' if arch != BrandArchitecture.HOUSE_OF_BRANDS else 'minimized'} in label hierarchy."
    ))
    tests.append(rating(
        "Shelf Test",
        has_symbol or logo_type == LogoType.COMBINATION,
        "A distinctive mark or symbol creates shelf recognition against competitors."
    ))
    tests.append(rating(
        "Extension Test",
        intake.portfolio_future > 3,
        f"System can support ~{intake.portfolio_future} future products "
        f"through variant naming, color changes, and sub-brand structure."
    ))
    tests.append(rating(
        "Simplification Test",
        logo_type == LogoType.COMBINATION,
        "A combination mark can simplify to symbol-only once recognition builds, "
        "but pure word marks cannot."
    ))

    return "\n".join(tests)


def creative_brief(
    intake: BrandIntake,
    logo_type: LogoType,
    arch: BrandArchitecture,
    color_palette: str,
    visual_motif: str,
) -> str:
    """Generate Final Creative Brief section."""
    return f"""**Brand Architecture:** {arch.value}
**Logo Type:** {logo_type.value}
**Label Style:** {intake.brand_personality or 'modern, clean, professional'}
**Color Palette:** {color_palette}
**Typography Direction:** Sans-serif for modern; serif for premium/heritage; monospace for technical
**Visual Motif:** {visual_motif}
**Layout Hierarchy:** Logo → Product Name → Key Claim → Variant/Flavor → Trust Signals → Legal Copy
**Emotional Tone:** {intake.emotional_response or 'trustworthy, professional, differentiated'}
**Scalability Rule:** Master brand fixed; product name changes by line; variant color changes by flavor
**Avoid:** Fake certifications, unreadable microcopy, unsupported health claims, distorted logo"""


def write_brief(intake: BrandIntake, logo: LogoType, arch: BrandArchitecture,
                color_palette: str, visual_motif: str) -> Path:
    """Write structured YAML brief to logos/ directory."""
    brand_slug = slugify(intake.brand_name)
    product_slug = slugify(intake.product_name)
    filename = f"{brand_slug}-{product_slug}.yaml"
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    path = LOGOS_DIR / filename

    # AI prompts for image generation
    ai_prompts = {
        "logo_mark": (
            f"Professional logo mark for {intake.brand_name}, "
            f"style: {logo.value}, bold geometric, clean lines, "
            f"color palette: {color_palette}, transparent background"
        ),
        "label_mockup": (
            f"Product label mockup for {intake.product_name}, brand: {intake.brand_name}, "
            f"premium retail packaging, {color_palette}, clean modern design, "
            f"photorealistic, white background"
        ),
    }

    data = {
        "brand": intake.brand_name,
        "product": intake.product_name,
        "price_positioning": intake.price_positioning or "general",
        "brand_personality": intake.brand_personality or "professional",
        "emotional_response": intake.emotional_response or "trust and confidence",
        "sales_channel": intake.sales_channel or "retail",
        "sections": {
            "logo_type": {
                "recommendation": logo.value,
                "rationale": LOGO_TYPE_DESCRIPTIONS[logo],
            },
            "icon_direction": {
                "description": "Avoid generic stock art; prefer ownable symbolic elements",
                "visual_motif": visual_motif,
            },
            "typography": {
                "style": "Maximum 2–3 font families with strong hierarchy",
                "product_name": "Bold display sans-serif or serif based on personality",
                "body_legal": "Clean sans-serif, minimum 6pt for legal text",
                "brand_line": "Light weight or small caps for secondary information",
            },
            "color_palette": {
                "palette": color_palette,
                "note": "Test all approved color versions for contrast and accessibility",
            },
            "mark_positioning": {
                "primary": "Within safe zone (0.25\" from trim)",
                "minimum_size": "Do not reduce below 0.5\" width on any axis",
                "clear_space": "Minimum equal to mark height on all sides",
            },
            "composition": {
                "layout": "Horizontal lockup preferred for label application",
                "symbol_only": "Permitted only if mark was designed for standalone recognition",
                "orientation": "Do not rotate beyond ±5° from horizontal or vertical axis",
            },
            "restrictions": {
                "forbidden": [
                    "Do not stretch or distort the mark",
                    "Do not recolor outside approved palette",
                    "Do not add drop shadows unless part of official system",
                    "Do not rotate the mark or word mark",
                    "Do not use mascot or icon separately unless designed for standalone recognition",
                ],
                "background_contrast": "Light backgrounds: full-color or reversed. Dark backgrounds: reversed (white) logo",
            },
            "competitive": {
                "positioning": f"Premium {intake.price_positioning or 'general'} positioning",
                "differentiation": "Clear hierarchy, ownable mark, verified claims only",
            },
            "brand_architecture": {
                "model": arch.value,
                "description": ARCHITECTURE_DESCRIPTIONS[arch].split("Label implication:")[0].strip(),
            },
            "scalability": {
                "flavors": "Product name fixed; variant name changes by flavor; color shifts by flavor",
                "sizes": "Proportional scaling; font sizes scale with label dimensions",
                "premium_economy": "Sub-brand names differentiate tiers",
                "seasonal": "Seasonal color palette applied within approved palette",
            },
            "production_notes": {
                "bleed": "0.125\" on all edges",
                "safe_zone": "0.25\" minimum content inset",
                "dpi": "300 DPI minimum for raster elements",
                "color_profile": "CMYK for press, simulate on screen before approval",
                "font_handling": "Embed fonts or convert to outlines for production",
            },
            "ai_prompts": ai_prompts,
        },
    }

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    return path


def slugify(text: str) -> str:
    """Convert text to a lowercase hyphenated slug."""
    import re
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"^-|-$", "", text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Main Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate(intake: BrandIntake) -> str:
    """Generate full 12-section logo strategy and creative brief."""

    arch, arch_reason = recommend_architecture(intake)
    logo, logo_reason = recommend_logo_type(intake)

    # Visual direction defaults
    personality = intake.brand_personality.lower()
    if "luxury" in personality or "premium" in personality:
        color_palette = "Deep navy, gold accent, cream, matte black"
        visual_motif = "Minimal ornament, refined typography, generous whitespace"
    elif "modern" in personality or "tech" in personality:
        color_palette = "Cobalt blue, white, light gray, electric accent"
        visual_motif = "Geometric grid, monospace accents, clean sans-serif"
    elif "artisan" in personality or "vintage" in personality or "heritage" in personality:
        color_palette = "Kraft brown, deep green, cream, aged gold"
        visual_motif = "Paper texture, hand-drawn details, stamp or seal motif"
    elif "playful" in personality or "family" in personality:
        color_palette = "Bright primary + secondary, white, soft pastels"
        visual_motif = "Rounded forms, friendly iconography, dynamic layout"
    else:
        color_palette = "Navy, white, warm gray, single accent color"
        visual_motif = "Clean geometric, balanced hierarchy, professional finish"

    output = []
    output.append(bold(f"\n{'#'*60}"))
    output.append(bold(f"# Logo Strategy & Creative Brief — {intake.brand_name}"))
    output.append(bold(f"# Product: {intake.product_name}"))
    output.append(bold(f"{'#'*60}\n"))

    # 1. Diagnosis
    output.append(section(1, "Brand and Product Diagnosis"))
    output.append(diagnose(intake))

    # 2. Architecture
    output.append(section(2, "Recommended Brand Architecture"))
    output.append(f"**Model:** {bold(arch.value)}\n")
    output.append(arch_reason)
    output.append(f"\n**Label Implication:** {ARCHITECTURE_DESCRIPTIONS[arch].split('Label implication:')[1].strip()}")

    # 3. Logo Type
    output.append(section(3, "Recommended Logo Type"))
    output.append(f"**Primary Logo Type:** {bold(logo.value)}\n")
    output.append(LOGO_TYPE_DESCRIPTIONS[logo])
    output.append(f"\n**Strategic Rationale:** {logo_reason}")

    # 4. Alignment
    output.append(section(4, "Logo and Brand Architecture Alignment"))
    alignment_map = {
        BrandArchitecture.BRANDED_HOUSE: (
            "Prioritize master-brand consistency across all labels. "
            "Product variants should be clearly subordinate to the master brand. "
            "The recommended system is a {logo.value} within a {arch.value} model "
            "because the master brand must dominate and remain consistent "
            "across all products in the portfolio."
        ),
        BrandArchitecture.SUB_BRANDS: (
            "Balance parent recognition with sub-brand distinction. "
            "The recommended system is a {logo.value} within a {arch.value} model "
            "because both parent and sub-brand must be visible, "
            "with the sub-brand having its own visual personality "
            "while remaining connected to the parent system."
        ),
        BrandArchitecture.ENDORSED_BRANDS: (
            "The product brand leads; the parent endorsement supports credibility. "
            "The recommended system is a {logo.value} within a {arch.value} model "
            "because the product brand should be visually dominant "
            "with the parent brand appearing as a secondary trust signal."
        ),
        BrandArchitecture.HOUSE_OF_BRANDS: (
            "Let the product brand stand alone with minimal parent visibility. "
            "The recommended system is a {logo.value} within a {arch.value} model "
            "because each brand operates independently "
            "with its own complete identity."
        ),
    }
    output.append(alignment_map[arch].format(logo=logo, arch=arch))

    # 5. Front Panel Strategy
    output.append(section(5, "Label Front Panel Strategy"))
    front_panel = textwrap.dedent(f"""\
    **Layout Hierarchy (top to bottom):**
    1. **Logo zone** — top-left or top-center; master brand dominant per architecture
    2. **Product name** — center-hero; largest text element; product identity
    3. **Key benefit or claim** — below product name; one line; differentiation
    4. **Variant / flavor indicator** — clear, secondary text; flavor, scent, or size
    5. **Trust signals** — certification badges or icons; only verified marks
    6. **Visual focal point** — brand mark, hero graphic, or decorative element
    7. **Barcode zone** — bottom-right or back panel; GS1 placeholder or UPC area
    8. **Legal copy** — bottom; smallest text; country of origin, net weight

    **White space guidance:** Maintain 0.25" safe zone minimum. Do not crowd the hero zone.
    """)
    output.append(front_panel)

    # 6. Visual Identity Direction
    output.append(section(6, "Visual Identity Direction"))
    visual = textwrap.dedent(f"""\
    **Color Palette:** {color_palette}

    **Typography Style:** Maximum 2–3 font families. Strong hierarchy:
      - Product name: Bold display sans-serif or serif (based on personality)
      - Body/legal: Clean sans-serif, minimum 6pt for legal text
      - Brand line: Light weight or small caps for secondary information

    **Icon or Illustration Style:**
      - {visual_motif}
      - Avoid generic stock art; prefer ownable symbolic elements

    **Photography or Graphic Treatment:**
      - Clean studio render for mockups
      - Flat label artwork for production vectors
      - No AI-generated text inside the logo mark

    **Material and Finish:**
      - Matte paper for natural/organic; glossy for bold/retail
      - Consider foil stamping or spot UV for premium tiers
    """)
    output.append(visual)

    # 7. Emotional Trigger
    output.append(section(7, "Emotional Trigger Strategy"))
    emotional = textwrap.dedent(f"""\
    **Primary Emotional Response:** {intake.emotional_response or 'Trust and confidence'}

    **How logo, color, typography, and layout support this:**
    - *Logo type ({logo.value}):* Establishes brand personality ({intake.brand_personality or 'professional'})
    - *Color palette:* Communicates category expectations and price positioning ({intake.price_positioning})
    - *Typography:* Hierarchy signals quality and attention to detail
    - *Layout:* Clean structure builds trust; overcrowding creates doubt

    **Shelf Emotional Test:** Does the label feel {intake.emotional_response or 'confident'} and differentiated
    from adjacent products?
    """)
    output.append(emotional)

    # 8. Scalability
    output.append(section(8, "Product Line and Scalability System"))
    scalability = textwrap.dedent(f"""\
    **How this label scales across:**
    - **Flavors:** Product name fixed; variant name changes by flavor; color shifts by flavor
    - **Sizes:** Proportional scaling; font sizes scale with label dimensions
    - **Product formats:** Same structure; layout adapts to rectangle/circle/oval
    - **Premium / economy tiers:** Sub-brand names differentiate tiers
    - **Seasonal editions:** Seasonal color palette applied within approved palette
    - **Sub-brands:** New spec required; architecture follows sub-brand model

    **Repeatable variant system:**
      - Master brand remains fixed
      - Product name changes by line
      - Variant color changes by flavor
      - Descriptor in same location
      - Icon system changes by benefit or ingredient
    """)
    output.append(scalability)

    # 9. Copy Framework
    output.append(section(9, "Label Copy Framework"))
    copy = textwrap.dedent(f"""\
    **Brand line / tagline:** [Brand tagline if established — omit if not]
    **Product descriptor:** {intake.product_name} — [short benefit or product type]
    **Primary claim:** [One clear benefit — requires substantiation if medical/health]
    **Secondary claim:** [Supporting benefit or differentiator]
    **Variant naming pattern:** {intake.product_name} — [Flavor/Scent/Formula]
    **Short benefit statement:** [Single sentence product value proposition]
    **Optional microcopy:** [Story or origin note if applicable]

    ⚠️ All claims must be verified before commercial printing. Claims related to
    health, organic, non-GMO, or certification require documented substantiation.
    """)
    output.append(copy)

    # 10. Logo System Bible
    output.append(section(10, "Logo System Bible"))
    bible = textwrap.dedent(f"""\
    **Primary Logo Lockup:** {logo.value} with full brand name; prefer horizontal layout
    **Secondary Logo Lockup:** {logo.value} symbol only; for small applications (≤1" label width)
    **Icon-Only or Simplified Mark Usage:** Permitted only if mark was designed for standalone recognition
    **Minimum Size:** Do not reduce below 0.5" width on any axis
    **Clear Space:** Minimum equal to the mark height on all sides
    **Approved Color Versions:**
      - Full color (brand palette)
      - Black-and-white (one-color imprint)
      - Reversed (white on dark background)
    **Black-and-White Version:** Required; test legibility without color
    **One-Color Version:** Required for single-ink printing; use black or approved single PMS
    **Placement Rules:**
      - Always within safe zone (0.25" from trim)
      - Do not rotate beyond ±5° from horizontal or vertical axis
      - Do not place on low-contrast or patterned backgrounds
    **Background Contrast Rules:**
      - Light backgrounds: use full-color or reversed logo
      - Dark backgrounds: use reversed (white) logo or approved dark-logo variant
    **Forbidden Modifications:**
      - Do not stretch or distort the mark
      - Do not recolor outside approved palette
      - Do not add drop shadows unless part of the official system
      - Do not rotate the mark or word mark
      - Do not rearrange symbol and word mark without approval
      - Do not use mascot or icon separately unless designed for standalone recognition
      - Do not place on competing color backgrounds that reduce contrast below 4.5:1
    """)
    output.append(bible)

    # 11. Stress Test
    output.append(section(11, "Strategic Stress Test"))
    output.append(stress_test(intake, logo, arch))

    # 12. Creative Brief
    output.append(section(12, "Final Creative Brief"))
    output.append(creative_brief(intake, logo, arch, color_palette, visual_motif))

    output.append("\n" + bold(f"{'='*60}"))
    output.append(bold("End of Logo Strategy"))
    output.append(bold(f"{'='*60}\n"))

    # Write YAML brief as side effect
    write_brief(intake, logo, arch, color_palette, visual_motif)

    return "\n".join(output)


# ─────────────────────────────────────────────────────────────────────────────
# Interactive intake
# ─────────────────────────────────────────────────────────────────────────────

def interactive_intake() -> BrandIntake:
    """Collect brand/product information via prompts."""
    intake = BrandIntake()

    print("\n📋 Logo Strategy — Brand Intake\n")

    intake.brand_name = input("1. Brand name: ").strip()
    intake.product_name = input("2. Product name: ").strip()
    intake.product_category = input("3. Product category (e.g., food, beverage, cosmetics, supplement): ").strip()
    intake.target_customer = input("4. Target customer (e.g., health-conscious women 25–45): ").strip()
    intake.price_positioning = input(
        "5. Price positioning (budget / mid-market / premium / luxury): "
    ).strip().lower()
    intake.brand_personality = input(
        "6. Brand personality (e.g., modern, artisan, playful, luxury, tech): "
    ).strip().lower()
    intake.emotional_response = input(
        "7. Desired emotional response (trust / desire / calm / energy / indulgence / craftsmanship): "
    ).strip()
    intake.sales_channel = input(
        "8. Sales channel (retail / ecommerce / boutique / wholesale / DTC): "
    ).strip().lower()
    intake.parent_brand = input("9. Parent brand (if any, leave blank if standalone): ").strip()
    intake.portfolio_size = int(input("10. Current number of products in portfolio (default 1): ").strip() or 1)
    intake.portfolio_future = int(input("11. Expected future products (default 3): ").strip() or 3)
    intake.required_claims = [
        x.strip() for x in input(
            "12. Required claims or certifications (comma-separated, e.g., USDA Organic, Vegan): "
        ).split(",") if x.strip()
    ]

    return intake


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Logo Strategy Generator")
    sub = parser.add_subparsers(dest="cmd")

    diagnose_cmd = sub.add_parser("diagnose", help="Run brand diagnosis")
    diagnose_cmd.add_argument("brand")
    diagnose_cmd.add_argument("product")
    diagnose_cmd.add_argument("--category", default="general")
    diagnose_cmd.add_argument("--audience", default="")

    generate_cmd = sub.add_parser("generate", help="Generate full logo strategy")
    generate_cmd.add_argument("--brand", default="")
    generate_cmd.add_argument("--product", default="")
    generate_cmd.add_argument("--category", default="")
    generate_cmd.add_argument("--audience", default="")
    generate_cmd.add_argument("--price", default="mid-market")
    generate_cmd.add_argument("--personality", default="")
    generate_cmd.add_argument("--emotion", default="")
    generate_cmd.add_argument("--channel", default="")
    generate_cmd.add_argument("--parent", default="")
    generate_cmd.add_argument("--portfolio", type=int, default=1)
    generate_cmd.add_argument("--future", type=int, default=3)
    generate_cmd.add_argument("--claims", default="")

    brief_cmd = sub.add_parser("brief", help="Interactive creative brief (supply args to skip prompts)")
    brief_cmd.add_argument("brand", nargs="?", default="")
    brief_cmd.add_argument("product", nargs="?", default="")
    brief_cmd.add_argument("--category", default="")
    brief_cmd.add_argument("--audience", default="")
    brief_cmd.add_argument("--price", default="mid-market")
    brief_cmd.add_argument("--personality", default="")
    brief_cmd.add_argument("--emotion", default="")
    brief_cmd.add_argument("--channel", default="")
    brief_cmd.add_argument("--parent", default="")
    brief_cmd.add_argument("--portfolio", type=int, default=1)
    brief_cmd.add_argument("--future", type=int, default=3)
    brief_cmd.add_argument("--claims", default="")

    args = parser.parse_args()

    if args.cmd == "diagnose":
        intake = BrandIntake(
            brand_name=args.brand,
            product_name=args.product,
            product_category=args.category,
            target_customer=args.audience,
        )
        print(diagnose(intake))
        return

    if args.cmd == "generate":
        intake = BrandIntake(
            brand_name=args.brand,
            product_name=args.product,
            product_category=args.category,
            target_customer=args.audience,
            price_positioning=args.price,
            brand_personality=args.personality,
            emotional_response=args.emotion,
            sales_channel=args.channel,
            parent_brand=args.parent,
            portfolio_size=args.portfolio,
            portfolio_future=args.future,
            required_claims=[x for x in args.claims.split(",") if x.strip()],
        )
        missing = intake.missing_fields()
        if missing:
            print(f"⚠️ Missing required fields: {', '.join(missing)}", file=sys.stderr)
            print("Use interactive mode: python3 logo_generator.py brief", file=sys.stderr)
            sys.exit(1)
        print(generate(intake))
        return

    if args.cmd == "brief":
        if args.brand or args.product or args.category or args.audience:
            intake = BrandIntake(
                brand_name=args.brand,
                product_name=args.product,
                product_category=args.category,
                target_customer=args.audience,
                price_positioning=args.price,
                brand_personality=args.personality,
                emotional_response=args.emotion,
                sales_channel=args.channel,
                parent_brand=args.parent,
                portfolio_size=args.portfolio,
                portfolio_future=args.future,
                required_claims=[x for x in args.claims.split(",") if x.strip()],
            )
        else:
            intake = interactive_intake()
        missing = intake.missing_fields()
        if missing:
            print(f"\n⚠️ Missing: {', '.join(missing)} — filling with reasonable defaults.\n")
            for field in missing:
                setattr(intake, field, "general")
        print(generate(intake))
        return

    parser.print_help()


if __name__ == "__main__":
    main()