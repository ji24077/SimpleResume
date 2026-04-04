# Extensions (additive features)

Place **new, optional** functionality here so the main compile/generate paths stay stable.

**Note:** Core product pipeline code lives under **`api/features/`** (PDF, generation, gates). `extensions/` is for **extras** that core must not depend on.

## Dependency rule

- **`extensions/`** may import from `api/` modules (e.g. `compile_pdf` shim, `features.*`, types).
- **Core files** (especially those in `.github/core-protected-paths.txt`) must **not** import from `extensions/`.

Wire new behavior from **`api/main.py`** (or a thin router) **only** behind feature flags, e.g.:

```python
if settings.feature_pdf_annotations:
    from extensions.annotations import ...
```

## Layout (examples)

```
extensions/
  annotations/
  diagnostics/
```

Each subfolder should own its tests and README if non-trivial.
