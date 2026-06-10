# image-gen capability

> Source-pluggable image generation CLI. Provider swappable by flag; new providers addable without touching the interface or callers.

## Entry point

```bash
python studio/capabilities/image-gen/generate.py --prompt "..." --out path/to/image.png [--provider gemini] [--aspect 16:9] [--env-file path/to/.env]
```

## Required arguments

| Flag | Description |
|------|-------------|
| `--prompt` | Text prompt for image generation. |
| `--out` | Output file path. Extension implies format (`png` or `jpg`). |

## Optional arguments

| Flag | Description |
|------|-------------|
| `--provider` | Adapter name. Default: `gemini`. Registered adapters are auto-discovered from `adapters/`. |
| `--aspect` | Desired aspect ratio (e.g. `1:1`, `16:9`, `4:3`). Passed to the adapter; the adapter decides dimensions. |
| `--env-file` | Path to a `KEY=value` env file. Used for credential fallback (see Credentials). |

## Credentials

Resolution order for `GEMINI_API_KEY`:
1. OS environment variable `GEMINI_API_KEY`.
2. The file supplied via `--env-file` (reads the line starting with `GEMINI_API_KEY=`).

The key is never printed, logged, or echoed.

## Adding a provider

1. Create a new module in `adapters/` (e.g. `adapters/openai.py`).
2. Implement `generate(prompt, out_path, fmt, aspect=None, api_key=None)` in that module.
3. Done. The module filename becomes the provider name — no registry edit required.

## Error behavior

| Condition | Exit code | Behavior |
|-----------|-----------|----------|
| Missing API key | 1 | Message names `GEMINI_API_KEY`; no file at `--out`. |
| Unknown provider | 1 | Lists registered providers. |
| Unwritable `--out` | 1 | Fails before any API call. |
| Provider error / rate limit | 1 | Provider reason on stderr; no partial file left. |

## Runtime dependencies

- Python 3.12+
- `requests` (for Gemini adapter)
- `Pillow` (for fixture adapter and image validation)

## Model

Gemini adapter uses `gemini-3.1-flash-image` via the `v1beta` Generative Language REST API.
