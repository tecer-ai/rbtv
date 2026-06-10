# DISPATCH — p1-harden (kimi executor) — harden `run.py` sanitize_path (Learning 3)

## You are a NON-REASONING bounded code executor
Apply the EXACT edit below — do not redesign. On any mismatch (the OLD block isn't found verbatim), STOP and return `status: DOUBT_ESCALATED` (do NOT guess at a different edit).

## Work-dir
rbtv repo root (via `--work-dir`). Path below is relative to it.

## Allowlist — your ENTIRE write universe
- ✎ MODIFY: `orchestration/models/_api/run.py` (ONLY the `sanitize_path` function — leave everything else byte-for-byte unchanged)
Create/modify NOTHING else. No stray files. No `git`. No subagents.

## The edit — replace this EXACT block (the current `sanitize_path`) ...
```python
def sanitize_path(p: str, output_folder: str) -> str:
    """Neutralise path-traversal attempts and return a safe relative path."""
    output_folder_real = os.path.realpath(output_folder)

    unsafe = ".." in p or os.path.isabs(p) or ":" in p

    if unsafe:
        safe = os.path.basename(p)
    else:
        safe = p

    joined = os.path.join(output_folder, safe)
    joined_real = os.path.realpath(joined)

    if not joined_real.startswith(output_folder_real):
        safe = os.path.basename(safe)

    return safe
```

## ... with this EXACT block (string-prefix guard → true path-boundary guard):
```python
def sanitize_path(p: str, output_folder: str) -> str:
    """Neutralise path-traversal attempts and return a safe relative path."""
    output_folder_real = os.path.realpath(output_folder)

    unsafe = ".." in p or os.path.isabs(p) or ":" in p

    if unsafe:
        safe = os.path.basename(p)
    else:
        safe = p

    joined_real = os.path.realpath(os.path.join(output_folder, safe))

    # True path-boundary check (NOT a string-prefix test): the resolved target
    # must live INSIDE the output folder. os.path.commonpath raises ValueError
    # on mixed drives / abs-vs-rel mixes — treat that as "outside".
    try:
        within = os.path.commonpath([output_folder_real, joined_real]) == output_folder_real
    except ValueError:
        within = False

    if not within:
        safe = os.path.basename(safe)

    return safe
```

That is the ONLY change. Do not touch imports (`os` is already imported), the dynamic-resolution code, or anything else.

## Validation (RUN before returning; capture command + EXIT in `validation`)
1. `python -c "import ast; ast.parse(open('orchestration/models/_api/run.py').read())"` → EXIT 0.
2. Regression battery — confirm the new guard preserves correct behavior. Run (from the repo root):
   ```
   python -c "import sys, os, tempfile; sys.path.insert(0,'orchestration/models/_api'); import run; d=tempfile.mkdtemp(); 
   assert run.sanitize_path('../escape.txt', d)=='escape.txt', 'traversal'; 
   assert run.sanitize_path('/etc/passwd', d)=='passwd', 'abs'; 
   assert run.sanitize_path('normal.txt', d)=='normal.txt', 'normal'; 
   assert run.sanitize_path('sub/inner.txt', d)=='sub/inner.txt', 'relsub'; 
   print('SANITIZE_BATTERY_OK')"
   ```
   → must print `SANITIZE_BATTERY_OK`, EXIT 0. (If `import run` triggers argparse/main, STOP and report — run.py should guard main under `if __name__ == "__main__"`; do NOT edit that to make the test pass, just report.)

## Return — EXACTLY these five fields:
- **status:** DONE | DONE_WITH_NOTES | BLOCKED | DOUBT_ESCALATED | NEEDS_CONTEXT
- **landed:** `run.py` modified (sanitize_path only) + one line (NO commit)
- **validation:** both commands + EXIT codes + the battery output; SKIPPED_COUNT
- **concerns / open_questions**
