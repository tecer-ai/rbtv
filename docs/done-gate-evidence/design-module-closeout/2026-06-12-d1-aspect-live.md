# D1 — Gemini `--aspect` live verification (2026-06-12)

Conductor-executed exit-probe (codex sandbox blocks process execution on Windows; the conductor runs the live call per Invariant-4 decide→resume; codex authored the gemini.py fix in Run D2).

## Fix applied (Run D2, codex)
`studio/capabilities/image-gen/adapters/gemini.py` — aspect config moved from the rejected `generationConfig.responseFormat.image.{aspectRatio,imageSize}` (proto `ImageResponseFormat` — HTTP 400 on the enum values) to the current `generationConfig.imageConfig.aspectRatio` with the plain ratio string; `imageSize` dropped.

## Live call (key REDACTED)
```
python studio/capabilities/image-gen/generate.py --prompt "a simple navy circle on a white background"   --out aspect-16x9.png --provider gemini --aspect 16:9 --env-file <.env>
```
- EXIT: 0
- Output PNG: 1376x768 px, 52649 bytes
- Aspect check: width>height = True (16:9 landscape confirmed)
- Result: real image generated; `--aspect` path now LIVE-WORKING on the paid key.

## Root-cause discovery
Conductor live probe of the buggy code returned HTTP 400 INVALID_ARGUMENT on `response_format.image.aspect_ratio`/`image_size` (proto enum values invalid). Web research + a confirming live probe established `generationConfig.imageConfig.aspectRatio="16:9"` → HTTP 200 with a real image. That confirmed structure was handed to codex as the fix spec.
