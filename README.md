# LABEL-DESIGN SKILL

A [Claude Code](https://claude.com/claude-code) skill for generating professional, print-ready product label designs in two phases.

## Overview

The skill takes a label concept from specification through to production-ready assets:

```
Phase 1 — Spec Lifecycle      Phase 2 — Rendering Pipeline
─────────────────────         ────────────────────────────
draft → reviewed          →   SVG (canonical)
         → approved            PNG (300 DPI)
              → locked          JSON (structured data)
```

**Phase 1** collects brand, product, dimensions, style, and content via a guided 10-step wizard. A YAML spec is the source of truth and passes a QA gate before locking.

**Phase 2** renders an approved/locked spec into multi-format outputs: SVG with named layer groups, PNG at 300 DPI, and JSON for downstream systems.

## Installation

```bash
git clone https://github.com/jcforever1/label-design-skill.git \
  ~/.claude/skills/label-design
```

Or copy the `SKILL.md` and `scripts/` directory into an existing skill directory manually.

## Usage

### Guided wizard (Mode B)

```text
/label-design
```

Starts a 10-step conversational wizard collecting brand, product, dimensions, style, and content. Ends with spec saved to `specs/{spec_id}.yaml` in `draft` status.

### Single-shot (Mode A)

```text
/render-label acme-waters-sparkling-mineral-water-06305f
```

One command: approve → lock → render all outputs.

### Spec management

```text
/approve-label-spec {spec_id}   # Mark spec approved
/label-specs                      # List all saved specs
/label-design --resume            # Resume an incomplete wizard
```

### Browse styles

```text
/label-styles
```

Lists all 25 predefined styles with descriptions. Each style maps to a visual system (typography, color strategy, layout principles).

### Iterative refinement

```text
/refine-label {spec_id}
```

Pick an aspect (color, typography, layout, content) and iterate interactively.

### Reference image analysis

```text
/analyze-reference-label references/my-label.jpg
```

Extracts dominant colors, infers style classification, and produces a style recommendation for use with `/label-design`.

---

## Spec Lifecycle

| Status | Who sets | Effect |
|--------|----------|--------|
| `draft` | Wizard / `spec_generator.py` | Can be freely edited |
| `reviewed` | After first validation | — |
| `approved` | `/approve-label-spec` | Render pipeline unlocked |
| `locked` | After strict QA gate | Edits rejected by validator |

QA gate blocks `locked` status on hard failures (missing required fields, invalid dimensions, out-of-range bleed/safe-zone, missing content). Strict mode is also available via `spec_validator.py --strict`.

## Command Reference

| Command | Mode | Description |
|---------|------|-------------|
| `/label-design` | B | Start 10-step wizard |
| `/render-label` | A | Single-shot: approve → lock → render |
| `/approve-label-spec` | B | Mark spec approved |
| `/refine-label` | A | Iterative refinement |
| `/analyze-reference-label` | B | Ingest reference image |
| `/label-styles` | A | Browse style library |
| `/label-specs` | A | List saved specs |
| `/label-wizard-resume` | B | Resume incomplete wizard |

## Output Structure

Each rendered spec produces:

```
renders/
└── {spec_id}/
    ├── label.svg       # Primary: named layer groups
    ├── label.png       # 300 DPI, CMYK simulation
    └── label.json      # Structured data
```

SVG layers: `background`, `artwork`, `text`, `barcode`, `bleed-marks`

## Style Library

25 predefined styles across 6 aesthetic families:

| Family | Styles |
|--------|--------|
| Minimal | clean-minimalist, modern-minimal, architectural |
| Vintage | vintage-artisan, craft-premium, whiskey-classic |
| Premium | luxury-premium, dark-luxury, platinum-elite |
| Natural | eco-friendly-natural, organic-earth, market-fresh |
| Commercial | bold-commercial, bright-energetic, clearance-sale |
| Functional | clinical-scientific, regulatory-warning, shipping-tag |

Use `/label-styles` to browse with descriptions.

## Testing

```bash
# Run the full E2E pipeline (Python 3 required)
python3 scripts/test_e2e.py

# Or run individual scripts
python3 scripts/spec_generator.py create "Brand" "Product" --seed demo
python3 scripts/spec_validator.py {spec_id}
python3 scripts/render_svg.py {spec_id}
```

Expected output: All Phase 1 (spec lifecycle) and Phase 2 (render pipeline) steps pass.

## Requirements

- Python 3.8+
- PyYAML
- CairoSVG or Inkscape (for PNG rendering)
- Pillow (for reference image analysis)

Install: `pip3 install pyyaml cairosvg pillow`

## Repository Structure

```
label-design/
├── SKILL.md              # Skill manifest + all documentation
├── lib/
│   ├── styles.yaml       # 25 predefined styles
│   ├── aesthetics.yaml   # Extended aesthetic options
│   └── templates.yaml     # Reusable spec templates
├── scripts/
│   ├── spec_generator.py    # Create specs (Phase 1)
│   ├── spec_validator.py    # Validate + QA gate
│   ├── render_svg.py        # Render SVG (Phase 2)
│   ├── svg_to_png.py        # Rasterize to PNG
│   ├── render_nutrition_panel.py
│   ├── nutrition_labelifier.py
│   └── reference_analyzer.py
├── specs/                # YAML specs (source of truth)
├── renders/             # Phase 2 output
├── references/           # Reference images
├── .github/
│   └── workflows/
│       └── test.yml      # CI pipeline
├── test_e2e.py          # E2E test suite
├── .gitignore
├── LICENSE
└── README.md
```

## License

MIT — see [LICENSE](LICENSE).