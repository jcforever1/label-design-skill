# Label Design Skill — Design Document

**Date**: 2026-05-15
**Author**: Brainstorming process (user + agent)
**Status**: Draft

---

## 1. Overview

**What it does**: A Claude Code skill that generates professional, print-ready product label designs across multiple sizes, industries, and formats.

**Target users**: Product designers, brand managers, packaging engineers, small brands, and creators who need label layout specs and production-ready assets without manual design software.

---

## 2. Interaction Model

**Primary architecture**: C) Two-phase

**User experience layers** (in priority order):

| Mode | Command | Description |
|------|---------|-------------|
| Conversational wizard | `/label-design` | Step-by-step guided intake, Phase 1 |
| Single-shot shortcut | `/label-design product="X" brand="Y" size="Z" style="W"` | Fast draft mode for advanced users |
| Open-ended | `/label-design [natural language description]` | Fallback for freeform input |
| Structured spec display | `/label-spec [spec_id]` | Show or update an existing spec |
| Rendering | `/render-label spec_id=X format=Y` | Phase 2 — multi-format output |
| Refinement | `/refine-label spec_id=X change="description"` | Modify an existing spec |
| Reference analysis | `/analyze-reference-label path="..."` | Extract aesthetic DNA from reference image |
| Template creation | `/create-template style="A" aesthetic="B"` | Save approved spec as reusable template |
| Spec management | `/save-label-spec`, `/approve-label-spec`, `/list-label-specs`, etc. | Lifecycle management |

**Design principle**: Phase 1 collects and resolves all inputs. Phase 2 renders approved specs to production assets. Phase 1 must complete before Phase 2 is meaningful.

---

## 3. Phase 1 — Label Strategy & Structured Spec

### 3.1 Wizard Flow (Default Experience)

When the user invokes `/label-design` with no arguments, the skill enters conversational intake mode:

```
Step 1: What product are you labeling? (e.g. bottled water, matcha powder, hand soap)
Step 2: What is the brand name? (e.g. Mountain Springs, Kiro)
Step 3: What size is the label? (e.g. 4x3, 2.5x2.5, custom WxH)
Step 4: Which industry/category? (Food, Cosmetics, Health, Household, Electronics, Artisan, General)
Step 5: Do you need a nutrition facts panel? (Yes/No — if yes, which region: US_FDA, EU, CA, AU)
Step 6: What design style? (see Style Library below)
Step 7: Do you want an advanced aesthetic approach? (see Aesthetic Library below)
Step 8: What micrographics level? (None, Minimal, Standard, Premium)
Step 9: Do you want to upload a reference label? (File path, URL, or skip)
Step 10: Review — confirm or adjust before spec is locked
```

### 3.2 Single-Shot Shortcut Mode

```
/label-design product="Bottled Water" brand="Mountain Springs" size="4x3" style="Minimalism" format="SVG"
```

- `fast_mode: true` — assumptions allowed, may be incomplete
- `commercial_ready: false_until_reviewed` — flag that draft mode is not print-ready
- Triggers same spec generation as wizard mode, but faster

### 3.3 Style Library (25 Styles)

| # | Style Name | Description |
|---|------------|-------------|
| 1 | Modern Minimalist | Clean lines, generous whitespace, simple hierarchy |
| 2 | Luxury Premium | Gold accents, serif fonts, high-contrast elegance |
| 3 | Eco-Friendly Natural | Earth tones, kraft textures, organic motifs |
| 4 | Bold Commercial | Strong colors, impactful typography, retail punch |
| 5 | Vintage Artisan | Hand-drawn, distressed textures, nostalgic warmth |
| 6 | Tech Futuristic | Dark backgrounds, neon accents, sci-fi typography |
| 7 | Japanese Minimalism | Asymmetric balance, restrained palette, wabi-sabi |
| 8 | Scandinavian | Pale wood tones, muted pastels, functional clarity |
| 9 | Mediterranean | Terracotta, olive, sun-washed warmth |
| 10 | Art Deco | Geometric patterns, gold lines, glamour typography |
| 11 | Retro Diner | Chrome accents, checkered patterns, nostalgic Americana |
| 12 | Boho Handcrafted | Textured paper, stamps, hand-lettered feel |
| 13 | High-Tech Industrial | Metal textures, stencil type, precision aesthetic |
| 14 | Farm-to-Table | Warm earth, hand illustrations, honest materials |
| 15 | Boutique Elegance | Soft blush, gold foil, refined femininity |
| 16 | Street Urban | Bold sans-serif, graffiti textures, raw energy |
| 17 | Nautical Maritime | Navy, rope textures, anchor motifs, coastal charm |
| 18 | Candy Pop | Bright colors, playful fonts, bouncy energy |
| 19 | Dark Moody | Deep tones, moody photography, premium mystery |
| 20 | Fresh Scandinavian | Light, airy, mint and white, clean freshness |
| 21 | Rustic Farmhouse | Weathered wood, serif fonts, country warmth |
| 22 | Chic Urban | Concrete textures, monospace type, loft aesthetic |
| 23 | Tropical Paradise | Palm motifs, vibrant hues, vacation warmth |
| 24 | Clean Medical | White and teal, precise layout, clinical trust |
| 25 | Custom | User describes their own style direction |

### 3.4 Aesthetic Library (Advanced)

| Category | Options |
|----------|---------|
| Typography mood | Refined Serif, Clean Sans, Monospace Technical, Hand-Lettered, Bold Display |
| Color strategy | Monochromatic, Complementary, Analogous, Neutral + One Pop, Full Spectrum |
| Material cue | Matte Paper, Glossy Plastic, Kraft Natural, Metallic Foil, Glass, Fabric |
| Layout principle | Center-Weighted, Asymmetric Calm, Grid-Strict, Editorial Asymmetric, Dense Information |
| Micrographics | None, Subtle Grain, Fine Lines, Geometric, Botanical, Wave Patterns |

### 3.5 Structured Spec Output

After intake, Phase 1 produces a YAML spec saved to `labels/specs/{spec_id}.yaml`:

```yaml
label_spec:
  spec_id: "mountain-springs-bottled-water-a7f3"
  status: "draft"
  created_at: "2026-05-15T21:00:00Z"

  product:
    name: "Bottled Water"
    variant: "Still / Sparkling"  # optional

  brand:
    name: "Mountain Springs"
    tagline: ""  # optional
    logo_placement: "top-center"

  label_size:
    trim_width: "4"
    trim_height: "3"
    unit: "inches"
    bleed: "0.125"
    safe_zone: "0.25"

  target_market: "Food & Beverage"
  design_style: "Modern Minimalist"
  aesthetic_strategy:
    typography_mood: "Clean Sans"
    color_strategy: "Monochromatic with blue accent"
    material_cue: "Matte Paper"
    layout_principle: "Center-Weighted"
    micrographics_level: "Subtle"

  nutrition_panel:
    required: true
    region: "US_FDA"
    placement: "back"

  front_label_layout:
    brand_zone: "top-center"
    product_name: "center"
    net_volume: "bottom-left"
    barcode_zone: "bottom-right"
    micrographics: "subtle watermark"

  back_label_layout:
    nutrition_panel: "full-width"
    ingredients: "below nutrition"
    allergen_statement: "below ingredients"
    manufacturer_details: "bottom"
    barcode: "bottom-right"

  color_palette:
    primary: "#1E3A5F"   # Deep navy
    secondary: "#7FB3D3" # Sky blue
    accent: "#E8F4F8"    # Pale ice
    text_dark: "#1A1A1A"
    text_light: "#FFFFFF"

  typography:
    primary_font: "Helvetica Neue Bold"  # product name
    secondary_font: "Helvetica Neue Regular"  # details
    accent_font: ""  # optional decorative

  print_specs:
    dpi: 300
    color_mode: "CMYK"
    bleed_extension: "0.125"
    safe_zone_from_edge: "0.25"
    font_handling: "embed or outline"

  ai_generation_prompt: |
    Create a premium minimalist label design for Mountain Springs bottled water.
    Clean white background with deep navy product name typography.
    Subtle water-inspired micrographics as a watermark.
    Generous whitespace, refined modern aesthetic.
    4" x 3" front layout with reserved zones for brand, product name, net volume, and barcode.

  negative_prompt: |
    Cluttered, low-resolution, fake barcode text, distorted typography,
    copied brand design, fake certifications, unreadable small text.

  quality_checklist:
    - product_name_legible: true
    - brand_name_visible: true
    - net_weight_declared: true
    - nutrition_panel_present: true
    - barcode_zone_reserved: true
    - safe_zone_respected: true
    - minimum_font_size_checked: true
    - allergen_statement_if_required: true

  reference_analysis: null  # or path to reference_analysis.yaml
```

### 3.6 Spec Lifecycle

| Status | Description | Render Allowed | Edit Allowed |
|--------|-------------|----------------|--------------|
| `draft` | Generated, not reviewed | Yes | Yes |
| `reviewed` | User reviewed concept | Yes | Yes |
| `approved` | Design direction locked | Yes | No (duplicate to edit) |
| `locked` | Final version for print | Yes | No (must duplicate) |

---

## 4. Phase 2 — Asset & Output Generation

### 4.1 Core Principle

> **One approved structured spec → many output formats**

The structured spec is the source of truth. All renderers read from the spec. This prevents layout drift between SVG, PDF, PNG, and prompt outputs.

### 4.2 Output Formats

| Format | Description | Production Use |
|--------|-------------|----------------|
| `SVG` | Vector label artwork with named layers | **Primary production asset** |
| `JSON` / `YAML` | Machine-readable layout spec | Developer/design handoff |
| `PDF` | Print-ready export package | Print shop delivery |
| `PNG` | Raster preview of SVG | Client preview, mockup |
| `PROMPT` | AI image prompt + negative prompt | Concept visualization only |
| `PACKAGE` | All outputs bundled | Full delivery bundle |

### 4.3 `/render-label` Command Behavior

**Canonical output (default)**:
```
/render-label spec_id=abc123
→ returns SVG path + JSON spec path + QA checklist
```

**Format variants**:
```
/render-label spec_id=abc123 format=SVG
→ labels/renders/abc123/label_front.svg

/render-label spec_id=abc123 format=PDF
→ labels/renders/abc123/label_print_package.pdf (or export instructions if rendering not available)

/render-label spec_id=abc123 format=JSON
→ labels/renders/abc123/label_layout.json

/render-label spec_id=abc123 format=PNG
→ labels/renders/abc123/label_preview.png

/render-label spec_id=abc123 format=PROMPT
→ AI image prompt + negative prompt (text output, clearly labeled as mockup only)

/render-label spec_id=abc123 format=PACKAGE
→ All available outputs bundled
```

**Spec resolution order** (when `spec_id` is provided):
1. Explicit spec argument (user passes full spec inline)
2. Project file: `labels/specs/{spec_id}.yaml` or `.json`
3. Session index: `~/.omc/` memory of known specs
4. Long-term approved template registry
5. Error with recovery options

### 4.4 SVG Output Requirements

The SVG must include named groups:

```xml
<svg viewBox="0 0 4.25in 3.25in">
  <g id="bleed-guide"><!-- 0.125in bleed outline --></g>
  <g id="trim-guide"><!-- trim edge --></g>
  <g id="safe-zone"><!-- 0.25in safe zone boundary --></g>
  <g id="background">
  <g id="brand-zone">
  <g id="product-name">
  <g id="hero-visual">
  <g id="nutrition-facts-panel">  <!-- vector text and rules -->
  <g id="ingredients-panel">
  <g id="allergen-statement">
  <g id="barcode-zone">
  <g id="micrographics">
  <g id="legal-copy">
  <g id="certification-badges">
</svg>
```

### 4.5 PDF Export Requirements

```yaml
pdf_export:
  trim_size: "4in x 3in"
  bleed: "0.125in"
  artboard: "4.25in x 3.25in"
  crop_marks: true
  registration_marks: optional
  color_profile: "CMYK recommended"
  font_handling: "embed or outline"
  barcode: "placeholder or verified placeholder"
  nutrition_panel: "vector text"
  resolution_note: "300 DPI minimum for raster elements"
```

### 4.6 AI Prompt Output

```
## AI Mockup Prompt

Create a premium product packaging mockup for Mountain Springs bottled water
using a minimalist transparent label design. Show a clear glass bottle in a
clean studio setting with soft natural light, subtle water condensation, refined
blue and white typography, generous whitespace, and a crisp modern brand presence.
The label should suggest a 4" × 3" front layout with reserved zones for product
name, brand name, net volume, barcode area, and compliance text, but do not
attempt to render small legal text or barcode details. Use the final SVG artwork
for actual print text.

## Negative Prompt

Unreadable small text, fake barcode, fake certification, distorted logo, random
nutrition facts, cluttered layout, low-resolution label, warped typography, copied
brand design.
```

> **Production rule**: SVG and PDF are production assets. AI prompts are visualization assets only.

---

## 5. Spec Persistence Architecture

### 5.1 File-Based Canonical Storage

```
labels/
  specs/
    mountain-springs-bottled-water-a7f3.yaml
    kiro-matcha-powder-b3c9.yaml
  renders/
    mountain-springs-bottled-water-a7f3/
      label_front.svg
      label_back.svg
      label_preview.png
      label_print.pdf
      label_layout.json
      quality_report.yaml
  references/
    kiro-matcha-powder-b3c9/
      reference_original.png
      reference_thumbnail.png
      reference_analysis.yaml
  nutrition/
    mountain-springs-bottled-water-a7f3/
      nutrition_sources.yaml
      nutrition_panel.svg
  templates/
    luxury-minimalist-matcha.yaml
    bold-commercial-beverage.yaml
  qa/
    mountain-springs-bottled-water-a7f3_quality_report.yaml
```

### 5.2 Spec ID Format

```
{brand_slug}-{product_slug}-{short_hash}
Example: mountain-springs-bottled-water-a7f3
```

Built-in aliases:
- `latest` — most recently created spec
- `approved` — most recently approved spec
- `draft` — current working draft

### 5.3 Spec Management Commands

```
/save-label-spec spec_id=abc123 status=draft
/approve-label-spec spec_id=abc123
/lock-label-spec spec_id=abc123
/duplicate-label-spec spec_id=abc123 new_variant="strawberry-flavor"
/list-label-specs
/delete-label-spec spec_id=abc123
/export-spec spec_id=abc123 format=YAML|JSON
```

---

## 6. Reference Image Analysis

### 6.1 Supported Input Methods

| Method | Best For | Command Example |
|--------|----------|-----------------|
| **B) File path** (primary) | Local workflows, reproducibility | `/analyze-reference-label path="labels/references/ref01.png"` |
| **A) URL** (secondary) | Quick intake from public images | `/analyze-reference-label url="https://..."` |
| **C) Base64** (fallback) | API clients, small images | `/analyze-reference-label image_base64="..."` |

### 6.2 Constraints

```yaml
allowed_formats: [png, jpg, jpeg, webp]
max_file_size: "10MB"
url_handling:
  https_public_only: true
  block_private_networks: true
  download_timeout: 20s
storage:
  preserve_original: true
  generate_thumbnail: true
```

### 6.3 Reference Analysis Output

Saved to `labels/references/{spec_id}/reference_analysis.yaml`:

```yaml
reference_analysis:
  reference_id: "ref-matcha-001"
  source_type: "file_path"
  original_file: "labels/references/.../reference_original.png"
  analyzed_at: "2026-05-15"

  style_matches:
    primary: "Japanese Minimalism"
    secondary: "Material-Led"
    tertiary: "Eco-Friendly Natural"

  aesthetic_dna:
    layout_principle: "Calm asymmetrical hierarchy with generous whitespace"
    color_strategy: "Warm ivory, muted green, black ink accents"
    typography_principle: "Refined serif headline with clean sans-serif details"
    material_cue: "Matte paper, tactile natural texture"
    micrographics: "Subtle grain"

  originality_requirements:
    must_change:
      - logo
      - exact layout
      - illustration details
      - color proportions
      - badge placement
      - typography lockup

  reusable_template_created: true
```

---

## 7. Command Architecture Summary

| Command | Phase | Description |
|---------|-------|-------------|
| `/label-design` | 1 | Start conversational wizard |
| `/label-design product="X" brand="Y" size="Z"` | 1 | Single-shot shortcut |
| `/label-spec [spec_id]` | 1 | Display/update existing spec |
| `/refine-label spec_id=X change="description"` | 1 | Modify spec |
| `/save-label-spec spec_id=X status=Y` | 1 | Save/manage spec |
| `/approve-label-spec spec_id=X` | 1 | Approve for production |
| `/analyze-reference-label path="..."` | 1 | Extract from reference image |
| `/create-template style="A" aesthetic="B"` | 1 | Save as reusable template |
| `/render-label spec_id=X format=Y` | 2 | Generate output |
| `/generate-nutrition-panel spec_id=X region=Y` | 2 | Create nutrition panel |
| `/list-label-specs` | — | List all specs |

---

## 8. Implementation Roadmap

### MVP (Phase 1 focus)
- Conversational wizard for structured spec creation
- Style library and aesthetic library selection
- File-based spec storage (`labels/specs/*.yaml`)
- Reference image analysis (file path + URL)
- AI prompt generation
- QA checklist output

### Production V1
- SVG renderer (named groups, proper dimensions)
- PNG preview generator
- Nutrition panel SVG generator
- Barcode placeholder zone
- Spec lifecycle management (draft → approved → locked)
- Template system

### Production V2
- Print-ready PDF export (crop marks, bleed, CMYK intent)
- Font embedding/outlining notes
- Multi-SKU batch rendering
- Verified barcode integration
- Long-term spec/template registry
- PACKAGE output mode

---

## 9. Key Design Decisions

| Decision | Choice | Rationale |
|---------|--------|-----------|
| Interaction model | C) Two-phase (primary) + B/A/D (support) | Structured input requires review; renders are separate from decisions |
| Phase 2 canonical output | SVG | Editable, scalable, deterministically generated from spec |
| Spec persistence | D) Hybrid (file-based + session index) | Project files are durable source of truth; session index is convenient |
| AI prompt role | Visualization only | AI-generated images are unreliable for production text/regulatory copy |
| Spec resolution | Explicit → File → Session → Template → Error | Predictable priority order with clear recovery |
| Reference image handling | B + A + C | File path for local workflows; URL for quick intake; Base64 for API clients |
| Spec lifecycle | draft → reviewed → approved → locked | Prevents accidental overwrites of approved designs |
| Output formats | SVG (primary), PDF (print), PNG (preview), PROMPT (concept), PACKAGE (full) | Clear separation of production vs. exploration assets |

---

## 10. Quality Standards

Every generated label must:
- ✅ Include all legally required elements for the declared category and region
- ✅ Maintain readable text at actual print size (minimum 6pt)
- ✅ Respect bleed (0.125") and safe zone (0.25") margins
- ✅ Reserve barcode quiet zone
- ✅ Use consistent visual hierarchy (brand → product → details)
- ✅ Pass WCAG contrast check for any text-over-background combinations
- ✅ Be scalable without quality loss (vector preferred)
- ✅ Separate production assets (SVG/PDF) from exploration assets (AI prompts)

---

*End of design document*