---
description: "Use at the moment a picture must be MADE or CHANGED — a new image, or an edit of an existing one. NEVER for reading or describing an image, extracting a prompt from one, capturing a screenshot, or producing a chart or diagram."
inputs: "A text prompt describing the wanted image (required). Optionally one or more existing images to edit or use as input (PNG, JPG/JPEG, WEBP, or GIF). An output folder, chosen by the caller."
outcome: "The caller holds the generated or edited image file(s) in the chosen output folder — or, when the model returned text instead of an image, a clear DONE_WITH_NOTES signal that no image was produced."
outputs: "Image file(s) written to --output-folder, a prompt.md holding the exact prompt used, and a return.json whose status is DONE, DONE_WITH_NOTES, or BLOCKED and whose landed array lists every file written."
---

# generate-image

Generates a new image from a text prompt, or edits an existing image, through the first-party
`cast` CLI (on PATH as `cast`) — Google's image models answer it via `cast api`. Instruction-only:
this capability has no CLI of its own. It consumes the `sub-agents` component's `cast` CLI as
infrastructure — image generation is the job, `cast` is the means.

## Open this first when the picture belongs to a SET

| Open | At exactly this moment |
|---|---|
| `references/consistent-sets.md` | **BEFORE generating the second picture that has to look like it belongs with the first** — a set of icons, cards, illustrations, chapter headers, product shots; also before regenerating one member of an existing set. It carries the two-part prompt (one shared style text, one subject per picture), how to calibrate the model with reference images and grow that reference library, how to iterate without losing an approved picture, and how to judge a set at final size. A single one-off picture does not need it. |

## Reach for this when

The user asks to generate, create, draw, render, make, design, or illustrate a picture —
"generate an image", "create a picture", "make me an illustration / logo / icon / banner /
thumbnail / mockup" — or to change an existing one — "edit this image", "change the background of
this photo", "restyle this", "make a variation of this picture". The Portuguese equivalents apply
the same: "gera uma imagem", "cria uma imagem", "faz uma figura".

**NOT for this.** Reading or describing an existing picture is plain vision, not this capability.
Extracting a reconstructable prompt FROM an image is `vision-to-json` (same component). Capturing
a screenshot of a page is `screenshot-capture` (same component). Producing a chart or diagram is
NEVER an image-generation job.

## Procedure

1. **Resolve which model answers image requests.** NEVER hardcode a model name — the roster is
   owner data, not prose:
   ```
   cast route --caps image
   ```
   Read the `model` field of the returned JSON, e.g.
   `{"verdict":"route","harness":"api","model":"<model>","mode":"api","effort":1,...}`.
2. **Text to image:**
   ```
   cast api <model> 1 -p "<prompt>" --output-folder <DIR> --image
   ```
3. **Edit or use an existing picture as input** — repeat `--input-image` for more than one:
   ```
   cast api <model> 1 -p "<prompt>" --output-folder <DIR> --image --input-image <PATH>
   ```
   Accepted input types: png, jpg/jpeg, webp, gif.

## Hard rules

- `1` is the mandatory effort argument. An image model has no thinking dial — the value is inert;
  pass `1` always.
- `--output-folder` is REQUIRED. Images land there as real files, beside a `return.json` whose
  `status` is `DONE`, `DONE_WITH_NOTES`, or `BLOCKED`, and whose `landed` array lists every file
  written.
- `DONE_WITH_NOTES` with no image in `landed` means the model narrated instead of drawing — the
  text is in `raw-output.md`. That is the signal NO image came back; NEVER read it as success.
- `-p` writes the prompt to `prompt.md` beside the output — the run documents itself.
- `--image` and `--grounded` are mutually exclusive.
- This is a PAID API call against the workspace's Google key. ONE call per request. NEVER a
  speculative retry. NEVER a batch of variations unless the user asked for variations.
- The caller chooses `--output-folder` — put it where the work lives, and ASK the user when there
  is no obvious home. NEVER invent a workspace-specific default path.
