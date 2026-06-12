# D3 settle-uncertain evidence

Date: 2026-06-12

## Pages Used

- Animated: `file:///C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/.codex-runs/runC-scratch/animated.html`
- Zero-motion: `file:///C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/.codex-runs/runC-scratch/static.html`

## Validation 1: Source marker

Command:

```powershell
grep -n "settle-uncertain" "studio/capabilities/extract-subtle-refs/extract.py"
```

Output:

```text
196:                "settle-uncertain",
259:    return any(obs.get("pattern") == "settle-uncertain" for obs in observations)
288:                print(f"WARN: settle-uncertain: {url} — zero motion; static OR settle missed it", file=sys.stderr)
EXIT=0
WALL_MS=35
SKIPPED_COUNT=0
```

## Validation 2: Zero-motion page

Command:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\pw-browsers"
uv --cache-dir "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\uv-cache" run --with playwright python "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\capabilities\extract-subtle-refs\extract.py" --url "file:///C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/.codex-runs/runC-scratch/static.html" --out "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\static-report.md" --json-out "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\static-report.json"
```

Output:

```text
EXIT=0
WALL_MS=3852
SKIPPED_COUNT=0
WARN: settle-uncertain: file:///C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/.codex-runs/runC-scratch/static.html — zero motion; static OR settle missed it
OK: file:///C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/.codex-runs/runC-scratch/static.html — 2 observation(s)
Report written to C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\static-report.md
JSON written to C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\static-report.json
```

Relevant report excerpt:

```markdown
### settle-uncertain

- **Anchor:** `page`
  - **Values:** `{}`
  - **Note:** Zero motion detected — the page may be genuinely STATIC, OR motion had not attached by the settle window (networkidle + 2s). Treat as uncertain; re-run headed / with a longer settle to disambiguate.
```

## Validation 3: Animated page

Command:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\pw-browsers"
uv --cache-dir "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\uv-cache" run --with playwright python "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\capabilities\extract-subtle-refs\extract.py" --url "file:///C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/.codex-runs/runC-scratch/animated.html" --out "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\animated-report.md" --json-out "C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\animated-report.json"
```

Output:

```text
EXIT=0
WALL_MS=3562
SKIPPED_COUNT=0
OK: file:///C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/.codex-runs/runC-scratch/animated.html — 3 observation(s)
Report written to C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\animated-report.md
JSON written to C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\.codex-runs\runC-scratch\animated-report.json
```

Relevant report excerpt:

```markdown
### css-animation

- **Anchor:** `div.badge`
  - **Values:** `{"name": "pulse", "duration": "0.8s", "easing": "ease-in-out", "delay": "0s", "iteration_count": "infinite"}`
  - **Note:** computed style

### keyframes-catalog

- **Anchor:** `document.stylesheets`
  - **Values:** `{"count": 1, "names": ["pulse"]}`
  - **Note:** CSS @keyframes definitions
```

## Validation 4: Diff scope

Command:

```powershell
git -C . diff --name-only HEAD
```

Output:

```text
studio/capabilities/extract-subtle-refs/extract-subtle-refs.md
studio/capabilities/extract-subtle-refs/extract.py
studio/capabilities/registry.md
studio/capabilities/screenshot-capture/capture.py
studio/capabilities/screenshot-capture/screenshot-capture.md
studio/commands/strategist.md
studio/critic/taxonomy.md
studio/hypresent/docs/plan/own-asset-colocation/decisions.md
studio/hypresent/docs/plan/own-asset-colocation/deliverables.md
studio/hypresent/docs/plan/own-asset-colocation/own-asset-colocation-plan.md
studio/hypresent/docs/plan/own-asset-colocation/phase-2/p2-2.task.md
studio/hypresent/docs/plan/own-asset-colocation/phase-2/p2-3-builder-save-asset-copy-bug.task.md
studio/hypresent/docs/plan/own-asset-colocation/phase-2/p2-checkpoint.task.md
studio/hypresent/docs/plan/own-asset-colocation/run-log.md
studio/hypresent/docs/plan/own-asset-colocation/state-capsule.md
studio/hypresent/tests/e2e/test_pb11_deck_save.py
studio/workflows/studio-loop/workflow.md
EXIT=0
WALL_MS=49
SKIPPED_COUNT=0
```

Scope note: the repo already had unrelated dirty tracked files before runC. The runC tracked edits are the two allowlisted extract-subtle-refs files; runC evidence and scratch files are under the allowlisted directories.
