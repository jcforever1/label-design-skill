# Label Design Skill — Architectural Decisions

## Spec Persistence

| Choice | Implementation |
|--------|----------------|
| **D) Hybrid** | File-based canonical storage + session memory convenience |

- **Canonical**: File-based project storage (specs/ YAML files) — durable, inspectable, versionable, renderer-friendly
- **Convenience**: Session memory/index — fast access within session
- **Fallback**: Stateless explicit spec passing — portability across sessions
- **Optional**: Long-term approved spec/template registry — reusable templates

## Reference Image Analysis

| Choice | Implementation |
|--------|----------------|
| **B + A + C** | Local file path (primary) + Public URL (secondary) + Base64 (fallback) |

- **Primary**: Local file path — best for local development workflows
- **Secondary**: Public image URL — convenient for quick intake
- **Fallback**: Base64 for small API payloads — useful for API clients
- **Text-only**: Supported only as fallback description mode, NOT as full reference analysis

## Rationale

- File-based specs are durable, inspectable, versionable, and renderer-friendly
- Session memory improves convenience but should not be the source of truth
- Stateless explicit spec passing preserves portability
- Reference image file paths are best for local workflows
- URLs are convenient for quick intake
- Base64 is useful for API clients but inefficient for large assets