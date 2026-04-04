# API response schemas (contract hints)

## Policy

- Existing clients rely on current field names and shapes.
- **Allowed:** add new **optional** keys (clients ignore unknown fields).
- **Avoid without version bump + comms:** rename, remove, or change types of existing keys.

## Files

- `generate_response_v1.json` — loose JSON Schema describing the main generate-style payload; `additionalProperties` allows forward-compatible extensions.

When you make a **breaking** contract change, add `generate_response_v2.json` (or bump version in filename) and document migration.
