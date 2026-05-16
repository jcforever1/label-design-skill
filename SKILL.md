# Label Design Skill

**Version**: 1.0.0
**Date**: 2026-05-15
**Status**: Draft

---

## What This Skill Does

Generates professional, print-ready product label designs across multiple sizes, industries, and formats. Two phases:

- **Phase 1** — Spec creation via conversational wizard or single-shot command
- **Phase 2** — Multi-format rendering from approved specs

---

## Command Reference

### Phase 1 — Spec Creation

| Command | Description |
|---|---|
| `/label-design` | Start conversational wizard (10 steps) |
| `/label-design product="X" brand="Y" size="Z" style="W"` | Single-shot shortcut |
| `/label-design --from-template=<name>` | Start from existing template |
| `/label-spec [spec_id]` | Display or update an existing spec |
| `/refine-label spec_id=... change="..."` | Modify a specific field on an existing spec |
| `/save-label-spec spec_id=... status=draft` | Save spec to disk |
| `/approve-label-spec spec_id=...` | Approve spec for production |
| `/lock-label-spec spec_id=...` | Lock spec (no further edits) |
| `/duplicate-label-spec spec_id=... new_variant="..."` | Duplicate with changes |
| `/delete-label-spec spec_id=...` | Delete a spec |
| `/list-label-specs` | List all specs |
| `/analyze-reference-label path="..."` | Extract aesthetic DNA from reference image |
| `/create-template style="A" aesthetic="B"` | Save approved spec as reusable template |
| `/list-label-templates` | Show available templates |

### Phase 2 — Rendering

| Command | Description |
|---|---|
| `/render-label spec_id=... format=SVG` | Generate SVG (canonical production asset) |
| `/render-label spec_id=... format=PNG` | Generate PNG preview |
| `/render-label spec_id=... format=JSON` | Generate layout JSON |
| `/render-label spec_id=... format=PROMPT` | Generate AI image prompt (mockup only) |
| `/render-label spec_id=... format=PACKAGE` | Bundle all outputs |
| `/render-label spec_id=... format=SVG --dry-run` | Preview render without writing files |
| `/generate-nutrition-panel spec_id=... region=US_FDA` | Generate nutrition panel SVG |

---

## Spec Lifecycle

```
draft → reviewed → approved → locked
```

- **draft**: Generated, not reviewed. Edits allowed.
- **reviewed**: User reviewed concept. Edits allowed.
- **approved**: Design direction locked. Edits create new version.
- **locked**: Final version for print. No edits (must duplicate).

**QA Gate**: Before `approved` → `locked`, `scripts/spec_validator.py` runs. Zero hard failures required for `locked`.

---

## Spec ID Format

```
{brand_slug}-{product_slug}-{6char_hash}
Example: mountain-springs-bottled-water-a7f3c2
```

- Generated: `sha256(timestamp + brand + product + seed)[:6]`
- Slug: lowercase, alphanumeric + hyphens, max 30 chars/component, collapse multi-hyphens
- Collision: append `-2`, `-3`, etc. if file exists
- Aliases: `latest`, `approved`, `draft`

---

## Label Dimension Standards

| Property | Value |
|---|---|
| Bleed | 0.125" (3mm) |
| Safe zone | 0.25" (6mm) from trim |
| Minimum DPI | 300 |
| Color mode | CMYK (recommended), RGB (preview) |
| Barcode quiet zone | ≥ 10x module width |

Artboard: `{trim_width + 0.25}" × {trim_height + 0.25}"`

---

## Directory Structure

```
~/.claude/skills/label-design/
├── SKILL.md
├── README.md
├── scripts/
│   ├── spec_generator.py
│   ├── spec_validator.py
│   ├── render_svg.py
│   ├── render_nutrition_panel.py
│   ├── svg_to_png.py
│   └── reference_analyzer.py
├── lib/
│   ├── styles.yaml         # 25 styles
│   ├── aesthetics.yaml     # 20 advanced approaches
│   ├── micrographics.yaml  # intensity levels + placement
│   ├── nutrition_rules.yaml # rounding, daily values
│   ├── regions.yaml        # mandatory fields, allergen lists
│   └── label_templates/    # 6 built-in templates
├── specs/                  # user-generated specs
├── renders/               # SVG/PNG/JSON outputs
├── references/             # reference image + analysis
└── templates/              # user-saved templates
```

---

## Quick Style Reference (25 Styles)

| # | Style | Best For |
|---|-------|----------|
| 1 | Modern Minimalist | Skincare, supplements, premium beverages |
| 2 | Luxury Premium | Cosmetics, wine, luxury food |
| 3 | Eco-Friendly Natural | Organic food, natural cleaning |
| 4 | Bold Commercial | Energy drinks, snacks, retail |
| 5 | Vintage Artisan | Handmade goods, apothecary |
| 6 | Tech Futuristic | Electronics, supplements |
| 7 | Japanese Minimalism | Beauty, skincare |
| 8 | Scandinavian | Home goods, children's products |
| 9 | Mediterranean | Olive oil, spices, artisan food |
| 10 | Art Deco | Champagne, luxury goods, gin |
| 11 | Retro Diner | Candy, soda, nostalgic treats |
| 12 | Boho Handcrafted | Handmade jewelry, candles |
| 13 | High-Tech Industrial | Tools, automotive, safety |
| 14 | Farm-to-Table | Eggs, produce, local goods |
| 15 | Boutique Elegance | Perfume, skincare |
| 16 | Street Urban | Streetwear, urban food |
| 17 | Nautical Maritime | Seafood, coastal gifts |
| 18 | Candy Pop | Kids snacks, novelty |
| 19 | Dark Moody | Craft beer, whiskey |
| 20 | Fresh Scandinavian | Dairy, fresh produce |
| 21 | Rustic Farmhouse | Jams, pickles, farm goods |
| 22 | Chic Urban | Coffee, artisan goods |
| 23 | Tropical Paradise | Sunscreen, beach goods |
| 24 | Clean Medical | First aid, clinical supplements |
| 25 | Custom | User-described style |

Full details in `lib/styles.yaml`.

---

## Aesthetic Library

See `lib/aesthetics.yaml`. Categories:

| Category | Options |
|----------|---------|
| Typography mood | Refined Serif, Clean Sans, Monospace Technical, Hand-Lettered, Bold Display |
| Color strategy | Monochromatic, Complementary, Analogous, Neutral + One Pop, Full Spectrum |
| Material cue | Matte Paper, Glossy Plastic, Kraft Natural, Metallic Foil, Glass, Fabric |
| Layout principle | Center-Weighted, Asymmetric Calm, Grid-Strict, Editorial Asymmetric, Dense Information |
| Micrographics | None, Subtle Grain, Fine Lines, Geometric, Botanical, Wave Patterns |

---

## Nutrition Panel Regions

Supported: `US_FDA`, `EU_1169`, `CA_CFIA`, `AU_FSANZ`

- `lib/nutrition_rules.yaml` — rounding rules, daily values, unit math
- `lib/regions.yaml` — mandatory fields, allergen lists, units, date formats

**Never produce nutrition values directly. All values from `lib/nutrition_rules.yaml` or user-provided authoritative sources.**

---

## QA Checklist

`scripts/spec_validator.py` gates locking.

**Hard failures (block `locked`)**:
- Fake certifications (USDA Organic, FDA Approved, Non-GMO Verified without confirmation)
- Fake barcode numbers (must be placeholder or GS1)
- Legal copy font < 6pt
- Bleed < 0.125"
- Safe zone < 0.125"

**Warnings (flagged at reviewed → approved)**:
- Contrast ratio < 4.5:1 on body text
- > 3 type families
- Barcode quiet zone < 10x module width
- Color mode mismatch

---

## Output Roles

| Format | Role |
|--------|------|
| SVG | Canonical production asset |
| PDF | Print export (RGB with CMYK note; true CMYK in v2) |
| PNG | Client preview |
| PROMPT | AI mockup visualization only |
| PACKAGE | All outputs bundled |

---

---

## Command Handlers

### `/label-design`

**Usage:** `/label-design` (interactive wizard) or `/label-design product="X" brand="Y" size="Z" style="W"` (single-shot)

**Wizard mode (no arguments):**

Run as a 10-step conversational wizard. Ask one question at a time. Collect:

1. **Brand name** — Ask: "What is the brand or company name for this label?"
2. **Product name** — Ask: "What is the product name?"
3. **Label dimensions** — Ask: "What are the label dimensions? (e.g., 3x2 in, 60x40mm, 2\" diameter)" Suggest standard sizes if needed.
4. **Industry/product type** — Ask: "What industry or product category? (e.g., cosmetics, food beverage, health supplements, electronics, artisan crafts)"
5. **Style** — Ask: "Which style direction? (Modern Minimalist, Luxury Premium, Eco-Friendly Natural, Bold Commercial, Vintage Artisan, Tech Futuristic, Japanese Minimalism, Scandinavian, Mediterranean, Art Deco, Retro Diner, Boho Handcrafted, High-Tech Industrial, Farm-to-Table, Boutique Elegance, Street Urban, Nautical Maritime, Candy Pop, Dark Moody, Fresh Scandinavian, Rustic Farmhouse, Chic Urban, Tropical Paradise, Clean Medical, Custom)" Show 25 options; recommend based on industry if clear.
6. **Target region** — Ask: "What regulatory region? (US_FDA, EU_1169, CA_CFIA, AU_FSANZ, or multiple)"
7. **Color preferences** — Ask: "Any color preferences or constraints? (e.g., must use kraft brown, avoid blue, prefer monochromatic)"
8. **Key claim/certification** — Ask: "Any certifications or claims to display? (e.g., USDA Organic, Non-GMO, Vegan, Gluten-Free, Made in USA)" — warn if unverifiable
9. **Barcode requirement** — Ask: "Does this need a barcode? (Yes/No/Placeholder only)"
10. **Reference image** — Ask: "Do you have a reference image to analyze? (yes = path, no = skip)"

After collecting answers, call `scripts/spec_generator.py create` with all values. Present the generated spec ID. Ask if user wants to save, preview, or iterate.

**Single-shot mode (all arguments provided):**

Parse arguments: `product`, `brand`, `size`, `style`, `region` (optional), `template` (optional). Call `scripts/spec_generator.py create` directly with parsed values. Present spec and offer next steps.

**`--from-template=<name>` mode:**

Read `lib/label_templates/<name>.yaml`. Use its values as defaults. Ask any missing required fields (product name, brand, dimensions) interactively. Then call `scripts/spec_generator.py create`.

**Scripts to call:**
- `python3 ~/.claude/skills/label-design/scripts/spec_generator.py create "<brand>" "<product>" [--seed <seed>]`

**Response:** Generate spec → display summary → offer: save, refine, render, or iterate.

---

### `/label-spec`

**Usage:** `/label-spec [spec_id]`

If no `spec_id` provided, resolve alias `draft` or list available specs and ask user to pick.

Call `python3 ~/.claude/skills/label-design/scripts/spec_generator.py read <spec_id>` to fetch spec data.

Display the full spec in a readable structured format:
- Header: brand, product, spec_id, status, created_at
- Design tokens: colors, typography, spacing, border
- Layout structure
- Compliance notes
- Nutrition region requirements

If spec is `locked`, show read-only notice. If `approved`, note that edits will create a new version.

**Alias resolution:**
- `latest` → most recently created spec
- `draft` → most recently created spec with status=draft
- `approved` → most recently created spec with status=approved

---

### `/refine-label`

**Usage:** `/refine-label spec_id=<spec_id> change="<description>"`

Parse `spec_id` and `change` from arguments. Load the spec via `spec_generator.py read`. Apply the requested change to the appropriate field(s). If change is ambiguous, ask one clarifying question before applying.

Changes can target:
- `color_palette.primary` → new hex value
- `typography.brand_name.font_family` → font name
- `style` → different style (re-pull from `lib/styles.yaml`)
- `layout` → different zone arrangement

After applying, write updated spec (status remains unchanged). Present diff of what changed.

**Constraint:** Cannot refine a `locked` spec — return error asking user to duplicate instead.

---

### `/save-label-spec`

**Usage:** `/save-label-spec spec_id=<spec_id> status=draft|reviewed`

Write spec to disk at `specs/<spec_id>.yaml`. The spec generator handles this via `write_spec()`. If no status provided, default to `draft`.

Confirm: "Spec saved as `<spec_id>` with status `<status>`."

**QA check on save:** If `status=reviewed`, run `spec_validator.py` and surface warnings but do not block.

---

### `/approve-label-spec`

**Usage:** `/approve-label-spec spec_id=<spec_id>`

Load spec. Run `spec_validator.py` in warning-only mode (not blocking). Surface any warnings.

Move status from `reviewed` → `approved`. Update spec file.

Confirm: "Spec `<spec_id>` approved. Design direction locked. Future edits will create a new version."

---

### `/lock-label-spec`

**Usage:** `/lock-label-spec spec_id=<spec_id>`

Load spec. Run `spec_validator.py` in strict mode (hard failures block locking).

**Hard failures that block `locked`:**
- Fake certifications without confirmation
- Fake barcode numbers (non-placeholder, non-GS1)
- Legal copy font < 6pt
- Bleed < 0.125"
- Safe zone < 0.125"

If any hard failure: list failures, do not lock, ask user to fix before proceeding.

If clean: move status `approved` → `locked`. Update spec file. Confirm: "Spec `<spec_id>` locked. Final version for print. No further edits permitted (must duplicate to change)."

---

### `/duplicate-label-spec`

**Usage:** `/duplicate-label-spec spec_id=<spec_id> new_variant="<description>"`

Load source spec. Create new spec with modified `spec_id` (new hash). Apply `new_variant` changes to relevant fields. New spec gets status `draft`, original unchanged.

Confirm with new spec ID and summary of changes.

---

### `/delete-label-spec`

**Usage:** `/delete-label-spec spec_id=<spec_id>`

Call `python3 ~/.claude/skills/label-design/scripts/spec_generator.py delete <spec_id>`.

Confirm deletion. If spec was `locked`, warn that this is irreversible.

---

### `/list-label-specs`

**Usage:** `/list-label-specs`

Call `python3 ~/.claude/skills/label-design/scripts/spec_generator.py list`.

Display as a table: spec_id | brand | product | status | created_at | version

---

### `/analyze-reference-label`

**Usage:** `/analyze-reference-label path="<path_to_image>"`

Call `scripts/reference_analyzer.py` with the provided image path.

Extract and report:
- Dominant color palette (3-5 colors with hex)
- Typography mood (serif, sans, display, etc.)
- Layout style (center-weighted, grid, asymmetric, etc.)
- Micrographics present (borders, patterns, ornaments, etc.)
- Visual complexity level (minimal, standard, premium)
- Suggested style matches from `lib/styles.yaml`

Offer to create a spec based on extracted aesthetic DNA.

---

### `/create-template`

**Usage:** `/create-template style="<style>" aesthetic="<aesthetic>"`

Save current spec (referenced by brand/product in conversation) as a reusable template in `templates/<style>.yaml`. Only `approved` or `locked` specs can become templates.

Prompt for: template name, description, industry fit.

Write to `templates/<style>.yaml`. Confirm: "Template `<style>` saved. Available via `/label-design --from-template=<style>`."

---

### `/list-label-templates`

**Usage:** `/list-label-templates`

Read all files in `lib/label_templates/` and `templates/`. Display as table: name | description | industry | style

Built-in templates (6): luxury-minimalist, organic-artisan, bold-retail-snack, clinical-supplement, vintage-apothecary, futuristic-tech

---

## Phase 2 Rendering Commands

### `/render-label`

**Usage:** `/render-label spec_id=<spec_id> format=<SVG|PNG|JSON|PROMPT|PACKAGE> [--dry-run]`

Resolve `spec_id` (handles aliases). Load spec data.

Call appropriate renderer:
- `SVG` → `scripts/render_svg.py`
- `PNG` → `scripts/render_svg.py` then `scripts/svg_to_png.py`
- `JSON` → `scripts/render_svg.py --json`
- `PROMPT` → generate AI image prompt from spec design tokens
- `PACKAGE` → run all renderers and bundle outputs
- `--dry-run` → show what would be rendered without writing files

Output path: `renders/<spec_id>/<format>.<ext>`

**Scripts to call:**
- `python3 ~/.claude/skills/label-design/scripts/render_svg.py <spec_id> [--output-format SVG|JSON]`
- `python3 ~/.claude/skills/label-design/scripts/svg_to_png.py <spec_id>`

---

### `/generate-nutrition-panel`

**Usage:** `/generate-nutrition-panel spec_id=<spec_id> region=<US_FDA|EU_1169|CA_CFIA|AU_FSANZ>`

Load spec and `lib/nutrition_rules.yaml` + `lib/regions.yaml` for the region.

Generate nutrition panel SVG matching the spec's design tokens (same font, colors, spacing style).

Call: `python3 ~/.claude/skills/label-design/scripts/render_nutrition_panel.py <spec_id> <region>`

Output to: `renders/<spec_id>/nutrition-panel-<region>.svg`

**Constraint:** Never generate actual nutrition values. Only render panel layout. Values come from user or authoritative source.

---

*End of SKILL.md*