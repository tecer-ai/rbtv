#!/usr/bin/env python3
"""scaffold.py — generate per-model dispatch task files from source.

The dispatch-scaffold generator (p2-6 of the token-efficiency refactor).
Composes dispatch boilerplate from the dispatch-wrapper card + a model delta,
never hardcoded. Reuses render-manuals.py primitives for parsing/composition.

Usage (run from the rbtv repo root):
    python orchestration/skills/orchestrating/scripts/scaffold.py \\
        --model kimi --output-folder <dir> --filename <name>
    # With task-specific instructions (complete mode):
    python ... --model kimi --output-folder <dir> --filename <name> \\
        --instructions <file-or-inline>
    # With provenance preview:
    python ... --explain

Spec: orchestration/token-efficiency/token-efficiency-refactor/specs/dispatch-scaffold-spec.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution — repo root is the rbtv repo (this script lives under
# orchestration/skills/orchestrating/scripts/, two levels below orchestration/).
# ---------------------------------------------------------------------------

SCRIPT_PATH = Path(__file__).resolve()
# scaffold.py → scripts/ → orchestrating/ → skills/ → orchestration/ → rbtv/
_ORCH_DIR_FROM_SCRIPT = SCRIPT_PATH.parent.parent.parent.parent  # orchestration/
RBTV_ROOT = _ORCH_DIR_FROM_SCRIPT.parent  # rbtv repo root
ORCH_DIR = _ORCH_DIR_FROM_SCRIPT

# Default source paths (overridable via --wrapper / --model-dir for testing).
DEFAULT_WRAPPER_PATH = (
    ORCH_DIR / "skills" / "orchestrating" / "cards" / "dispatch-wrapper.md"
)
DEFAULT_MODELS_DIR = ORCH_DIR / "models"

DELTA_FILENAME = "delta.md"

# Reuse render-manuals.py primitives — import from the canonical module.
RENDER_MANUALS = ORCH_DIR / "models" / "render-manuals.py"


def _import_render_primitives():
    """Import compose primitives from render-manuals.py without requiring it
    to be on sys.path or installed as a package."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("render_manuals", str(RENDER_MANUALS))
    if spec is None or spec.loader is None:
        _fail(f"cannot load render-manuals.py from {RENDER_MANUALS}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Per-model frontmatter skeleton and body-section header extraction from delta.
# The delta states required frontmatter keys and body section headers in prose
# under "The {model} task contract" heading. We parse them with a structured
# convention: lines between "Required frontmatter:" and the next heading give
# the skeleton keys; lines between "Required body sections:" and the next
# heading give the section headers.
# ---------------------------------------------------------------------------

# Known frontmatter keys we recognise from model deltas (skeleton keys only —
# values are left as placeholders for the conductor to fill).
_KNOWN_FM_KEYS = [
    "execution_kind", "executor", "allowed_workdir", "allowlist",
    "commit_policy", "test_command", "forbidden_ops", "doubt_policy",
    "reviewer", "swarm_policy", "max_kimi_subagents",
]

# Body-section header ordering (generic — models may add/remove; the delta
# declares the authoritative list).
_GENERIC_BODY_SECTIONS = [
    "Goal", "Context Snapshot", "Allowed Paths", "Forbidden Paths",
    "Implementation Requirements", "Validation", "Commit Rule",
    "Swarm Rule", "Return Format",
]


def parse_required_sections(delta_text: str, model: str) -> tuple[list[str], list[str]]:
    """Extract (frontmatter_keys, body_section_headers) from a delta's prose.

    Looks for the 'Required frontmatter:' YAML block and 'Required body
    sections:' prose within the model's task-contract section. Returns the
    frontmatter keys (as YAML key names) and body-section headers (as display
    names). If a structured block is not found, returns empty lists — the
    caller should fail loud (derive-or-fail).
    """
    fm_keys: list[str] = []
    body_headers: list[str] = []

    # --- Parse required frontmatter: look for a YAML code block after
    # "Required frontmatter:" marker. ---
    fm_match = re.search(
        r"\*\*Required frontmatter:\*\*\s*\n```yaml\s*\n(.*?)```",
        delta_text, re.DOTALL,
    )
    if fm_match:
        yaml_block = fm_match.group(1)
        for line in yaml_block.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("- "):
                continue
            # Strip value part (everything after the first colon for scalars).
            key = line.split(":")[0].strip()
            if key and not key.startswith("-"):
                fm_keys.append(key)

    # --- Parse required body sections: look for "Required body sections:"
    # followed by section names. They may be on the same line (kimi: inline
    # with · separators) or on subsequent lines (bullet list). ---
    bs_match = re.search(
        r"\*\*Required body sections:\*\*\s*\n?(.*?)(?:\n\n|\n```|\n###|\Z)",
        delta_text, re.DOTALL,
    )
    if bs_match:
        bs_text = bs_match.group(1).strip()
        # kimi style: "Goal · Context Snapshot · Allowed Paths · …" (inline, ·-separated)
        if "·" in bs_text:
            body_headers = [s.strip() for s in bs_text.split("·") if s.strip()]
            # Clean up: remove parenthetical descriptions from the header name
            cleaned = []
            for h in body_headers:
                # "Goal (one bounded deliverable)" → "Goal"
                name = h.split("(")[0].strip()
                if name:
                    cleaned.append(name)
            body_headers = cleaned
        else:
            # Bullet-list style: "- Goal" or "  - Goal"
            for line in bs_text.splitlines():
                m = re.match(r"\s*[-*]\s+(.+)", line)
                if m:
                    body_headers.append(m.group(1).strip())

    if not fm_keys or not body_headers:
        return fm_keys, body_headers  # Caller detects empty → fail loud

    return fm_keys, body_headers


# ---------------------------------------------------------------------------
# Frontmatter skeleton generation — keys from delta, values as placeholders.
# ---------------------------------------------------------------------------

def _placeholder_value(key: str) -> str:
    """Return a human-readable placeholder for a frontmatter key."""
    placeholders = {
        "execution_kind": "<code|research>",
        "executor": "<model-id>",
        "allowed_workdir": "<repo-path>",
        "allowlist": "\n  - <file-or-folder-glob>",
        "commit_policy": "<local-only|none>",
        "test_command": "<command-or-NONE>",
        "forbidden_ops": "\n  - git push\n  - writes outside allowlist\n  - destructive git reset\n  - external production API calls",
        "doubt_policy": "halt",
        "reviewer": "<reviewer-model>",
        "swarm_policy": "<disabled|allowed>",
        "max_kimi_subagents": "<N-or-0>",
    }
    return placeholders.get(key, f"<{key}>")


def generate_frontmatter_skeleton(keys: list[str]) -> str:
    """Generate a YAML frontmatter skeleton with placeholder values."""
    lines = ["---"]
    for key in keys:
        val = _placeholder_value(key)
        if "\n" in val:
            # Multi-line value — emit directly (already indented).
            lines.append(f"{key}:{val}")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Carrier detection — read the model manifest to determine Agent-tool vs CLI.
#
# Manifest-grounded discriminator (robust, not fragile):
#   - Agent-tool carrier: headless.flags == "" AND auth.method == "none"
#     AND auth.required == false.  This is the in-session Agent/Task tool
#     path — there is NO process invocation, the prompt reaches the sub-agent
#     as the Agent tool's `prompt` parameter (see claude manifest header).
#   - CLI carrier: headless.flags is non-empty (e.g. "--quiet", "-p …") OR
#     auth.method is something other than "none" (cli-login, api-key).  These
#     packages have a process surface (command, flags, stdin/stdout).
#
# The spec forbids fabricating CLI invocation notes for an Agent-tool target
# (Out-of-Scope: "fabricate CLI flags for an Agent-tool target").
# ---------------------------------------------------------------------------

def _is_agent_tool_carrier(model: str, models_dir: Path) -> bool:
    """Return True if the model package is an Agent-tool carrier (no CLI process).

    Reads the model's manifest.yaml and checks the carrier discriminator:
    headless.flags == "" AND auth.method == "none" AND auth.required == False.
    """
    try:
        import importlib.util
        yaml_path = models_dir / model / "manifest.yaml"
        if not yaml_path.exists():
            return False
        # Load yaml using stdlib-only approach (manifest is simple key-value).
        # Try importing pyyaml first; fall back to minimal parser.
        try:
            import yaml as _yaml
            with open(yaml_path, encoding="utf-8") as f:
                manifest = _yaml.safe_load(f)
        except ImportError:
            # Minimal YAML parser for the fields we need.
            manifest = _minimal_manifest_parse(yaml_path)

        if manifest is None:
            return False

        variants = manifest.get("variants", [])
        if not variants:
            return False
        v = variants[0]  # Check first variant as carrier discriminator
        headless = v.get("headless", {})
        auth = v.get("auth", {})

        flags = headless.get("flags", "")
        auth_method = auth.get("method", "")
        auth_required = auth.get("required", True)

        return flags == "" and auth_method == "none" and auth_required is False
    except Exception:
        # If manifest reading fails, default to CLI (safe: won't suppress flags
        # for a genuine CLI carrier).
        return False


def _minimal_manifest_parse(yaml_path: Path) -> dict | None:
    """Minimal stdlib YAML parser extracting only headless.flags, auth.method,
    auth.required, and variants list. Returns None on failure."""
    try:
        import yaml as _yaml
        with open(yaml_path, encoding="utf-8") as f:
            return _yaml.safe_load(f)
    except ImportError:
        pass

    # Fallback: regex-based extraction for the three fields we need.
    text = yaml_path.read_text(encoding="utf-8")

    # Extract headless.flags value.
    flags_m = re.search(r'^\s+flags:\s*["\']?(.*?)["\']?\s*$', text, re.MULTILINE)
    auth_method_m = re.search(r'^\s+method:\s*(\S+)\s*$', text, re.MULTILINE)
    auth_required_m = re.search(r'^\s+required:\s*(true|false)\s*$', text, re.MULTILINE | re.IGNORECASE)

    if not flags_m or not auth_method_m or not auth_required_m:
        return None

    return {
        "variants": [{
            "headless": {"flags": flags_m.group(1).strip().strip("'\"")},
            "auth": {
                "method": auth_method_m.group(1).strip(),
                "required": auth_required_m.group(1).lower() == "true",
            },
        }]
    }


# ---------------------------------------------------------------------------
# Launch-flag emission as DATA — read from the delta's invocation section.
# ---------------------------------------------------------------------------

def extract_launch_flags(delta_text: str, model: str, models_dir: Path) -> str:
    """Derive launch flags from the model delta's invocation section.

    FIX ADX-18 #1 (carrier-aware): before emitting any CLI flags, reads the
    target package's manifest to determine carrier nature.  Agent-tool carriers
    (headless.flags == "" AND auth.method == "none" AND auth.required == False)
    get an explicit Agent-tool note with NO scraped flags.  CLI carriers keep
    the derived-flag emission.

    Deterministically extracts flag tokens (`--name` and short `-x`) from
    the invocation section in first-appearance order, then emits them as
    DATA with a provenance note. Per spec S8: the scaffold EMITS the fields,
    never authors G1 policy text or fills root/target values.
    """
    # ADX-18 #1: carrier check — Agent-tool carriers must NOT get CLI flags.
    if _is_agent_tool_carrier(model, models_dir):
        return (
            "### Invocation note (Agent-tool dispatch)\n\n"
            "Agent-tool dispatch — no CLI invocation; the prompt is the Agent tool's prompt parameter.\n"
            "\n> This is an in-session sub-agent carrier. There is no process, no flags, no stdin/stdout surface.\n"
        )

    inv_match = re.search(
        r"<!--\s*RENDER:DELTA\s+invocation\s*-->\s*\n(.*?)<!--\s*RENDER:DELTA-END\s+invocation\s*-->",
        delta_text, re.DOTALL,
    )
    if not inv_match:
        return ""

    inv_text = inv_match.group(1)

    # Derive flag tokens: --long-form (and --kebab-case) first, then -x short forms.
    long_flags = re.findall(r'--([A-Za-z][A-Za-z0-9][A-Za-z0-9-]*)', inv_text)
    # Deduplicate preserving first-appearance order.
    seen: set[str] = set()
    ordered_long: list[str] = []
    for f in long_flags:
        if f not in seen:
            seen.add(f)
            ordered_long.append(f)

    # Short single-letter flags: -C, -p, -q, etc. (but not -- or markdown dashes).
    short_flags = re.findall(r'(?<![A-Za-z0-9])-([A-Za-z])(?![A-Za-z0-9-])', inv_text)
    ordered_short: list[str] = []
    for f in short_flags:
        if f not in seen:
            seen.add(f)
            ordered_short.append(f)

    # Build the derived invocation note.
    flags_text_parts: list[str] = []
    for f in ordered_long[:12]:  # cap at 12 for readability
        flags_text_parts.append(f"`--{f}`")
    for f in ordered_short[:6]:
        flags_text_parts.append(f"`-{f}`")

    flags_summary = ", ".join(flags_text_parts) if flags_text_parts else "(none derived)"

    return (
        f"### Invocation note (launch flags — DATA only; derived-from: delta invocation section)\n\n"
        f"Derived flags from delta: {flags_summary}\n\n"
        f"Confinement diff: `git diff --name-only HEAD` run in the work-target's git, not the launch-root.\n"
        f"\n> These fields are emitted as data; the conductor supplies orchestrator-root and work-target values at dispatch.\n"
    )


# ---------------------------------------------------------------------------
# G3 hook seam — named, no-op default.
# ---------------------------------------------------------------------------

def pre_dispatch_hook(model: str, work_dir: str, output_path: str) -> tuple[bool, str]:
    """Named pre-dispatch hook slot (Brief E G3 seam).

    Contract: receives the model + work-dir + output context, returns
    (pass: bool, gap_message: str). Default implementation is a no-op that
    always passes. Review 5 supplies the verify-or-supply body later.

    DO NOT implement rules-reach logic here — this is a seam, not the policy.
    """
    # No-op default — always passes.
    return True, ""


# ---------------------------------------------------------------------------
# Pre-flight checks (S6).
# ---------------------------------------------------------------------------

def _fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def preflight_check_package(model: str, models_dir: Path) -> None:
    """Check 1: model package folder + delta.md exist."""
    model_dir = models_dir / model
    if not model_dir.is_dir():
        _fail(f"pre-flight: model package '{model}' not found at {model_dir}")
    delta_path = model_dir / DELTA_FILENAME
    if not delta_path.exists():
        _fail(f"pre-flight: model '{model}' has no {DELTA_FILENAME} at {delta_path}")


def preflight_check_manual_fresh(model: str) -> None:
    """Check 2: render-manuals.py --check reports zero drift for this model."""
    import subprocess

    result = subprocess.run(
        [sys.executable, str(RENDER_MANUALS), "--check", "--model", model],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(RBTV_ROOT),
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        _fail(
            f"pre-flight: model '{model}' manual is stale — re-render needed. "
            f"Run: python {RENDER_MANUALS.relative_to(RBTV_ROOT)}\n"
            f"  {stderr}"
        )


def preflight_check_guidance(model: str, models_dir: Path) -> None:
    """Check 3: guidance file convention is satisfiable.

    This check is a documented stub — the actual verify-or-supply rules-reach
    logic (Brief E G3: check .agents/behavior-rules/ present+current, inject/mirror)
    is Review 5's track. The scaffold ships WITHOUT rules-reach logic; this slot
    always defers to Review 5/G3.
    """
    # DEFERRED no-op — the real guidance-file check is Review 5 / G3 track.
    # This stub documents that the check exists and will be supplied later.
    pass  # guidance check: DEFERRED (Review-5/G3 track) — no-op


def preflight_check_output_folder(output_folder: Path) -> None:
    """Check 4: --output-folder is an existing directory."""
    if not output_folder.is_dir():
        _fail(f"pre-flight: output folder does not exist: {output_folder}")


# ---------------------------------------------------------------------------
# Composed header generation — reuse render-manuals primitives.
# ---------------------------------------------------------------------------

def compose_run_binding_header(
    model: str,
    wrapper_path: Path,
    delta_path: Path,
    render_mod,
) -> str:
    """Compose the run-binding header from the card + model delta.

    Reuses render-manuals.py's parse_template, parse_delta, and
    compose_manual to produce the same composed header the rendered manual
    carries for the binding addendum + return schema sections. Returns the
    composed text (generic blocks with delta inserts).
    """
    blocks, insert_ids = render_mod.parse_template(wrapper_path)
    delta_sections = render_mod.parse_delta(delta_path)
    # Use compose_manual to get the full composed text, then extract just
    # the header portion (before the invocation section).
    full_manual = render_mod.compose_manual(
        model, blocks, insert_ids, delta_sections, delta_path,
    )
    # The run-binding header = everything before the invocation heading.
    inv_heading = render_mod.INVOCATION_HEADING
    parts = full_manual.split(inv_heading)
    header = parts[0].rstrip("\n") + "\n"
    return header


# ---------------------------------------------------------------------------
# Skeleton-mode output.
# ---------------------------------------------------------------------------

def build_skeleton_output(
    model: str,
    header: str,
    fm_keys: list[str],
    body_headers: list[str],
    launch_flags: str,
) -> str:
    """Build a skeleton task file: frontmatter at top, then body-section
    headers, then the composed header at the bottom."""
    # FIX 2: frontmatter must be FIRST in the file (task-file contract §1).
    parts = [generate_frontmatter_skeleton(fm_keys)]
    parts.append("")
    for section in body_headers:
        parts.append(f"## {section}")
        parts.append("")
        parts.append("<conductor fills this section>")
        parts.append("")
    if launch_flags:
        parts.append(launch_flags)
        parts.append("")
    # G3 hook mention.
    parts.append("## Pre-Dispatch Hook")
    parts.append("")
    parts.append(
        "A named pre-dispatch hook slot exists (`pre_dispatch_hook` in scaffold.py) — "
        "default no-op, always passes. Review 5 supplies the verify-or-supply body.\n"
    )
    # Composed run-binding header goes after the body (the header is the
    # wrapper-derived context — it follows the task-specific sections).
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## Run-Binding Header (derived from dispatch-wrapper card + model delta)")
    parts.append("")
    parts.append(header)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Complete-mode output (--instructions).
# ---------------------------------------------------------------------------

def _parse_instruction_headings(instructions: str) -> dict[str, str]:
    """Parse an instructions blob into {section_name: content} mapping.

    If the instructions contain markdown headings (## Name) whose names match
    known task-specific body sections, return the mapping. Otherwise return
    an empty dict (all content falls into Goal as the fallback).
    """
    # Task-specific section names that headings can match.
    task_specific = {"Goal", "Context Snapshot", "Allowed Paths", "Forbidden Paths",
                     "Implementation Requirements", "Validation", "Commit Rule",
                     "Swarm Rule", "Return Format"}

    sections: dict[str, str] = {}
    current_heading: str | None = None
    buf: list[str] = []

    def flush() -> None:
        """Append the current buffer to its section (append, so multiple
        unmatched segments accumulating into Goal are never overwritten)."""
        if current_heading is None:
            return
        text = "\n".join(buf).strip()
        if not text:
            return
        if current_heading in sections:
            sections[current_heading] += "\n" + text
        else:
            sections[current_heading] = text

    for line in instructions.splitlines():
        m = re.match(r'^#{1,3}\s+(.+)$', line)
        if m:
            heading_name = m.group(1).strip()
            if heading_name in task_specific:
                # Matched heading → flush the prior section, open this one.
                flush()
                current_heading = heading_name
                buf = []
            else:
                # Unmatched heading → its content (heading line included)
                # lands in Goal. If we were inside another section, flush it
                # first so the unmatched run does not bleed into that section.
                if current_heading != "Goal":
                    flush()
                    current_heading = "Goal"
                    buf = [line]
                else:
                    buf.append(line)
        else:
            if current_heading is None:
                current_heading = "Goal"
                buf = [line]
            else:
                buf.append(line)

    # Flush the final section.
    flush()

    # Only return non-empty mappings.
    return {k: v for k, v in sections.items() if v}


def build_complete_output(
    model: str,
    header: str,
    fm_keys: list[str],
    body_headers: list[str],
    instructions: str,
    launch_flags: str,
) -> str:
    """Build a complete dispatchable prompt: frontmatter at top, body sections
    with heading-aware instructions merge, then composed header."""
    # FIX 4: heading-aware merge — parse instructions for matching section headings.
    heading_map = _parse_instruction_headings(instructions)

    parts = [generate_frontmatter_skeleton(fm_keys)]
    parts.append("")

    for section in body_headers:
        parts.append(f"## {section}")
        parts.append("")
        if section in heading_map:
            parts.append(heading_map[section])
        else:
            parts.append("<conductor fills this section>")
        parts.append("")

    # Any instructions content that didn't match a heading goes into Goal.
    # (Already handled by _parse_instruction_headings → "Goal" fallback.)

    if launch_flags:
        parts.append(launch_flags)
        parts.append("")

    parts.append("## Pre-Dispatch Hook")
    parts.append("")
    parts.append(
        "A named pre-dispatch hook slot exists (`pre_dispatch_hook` in scaffold.py) — "
        "default no-op, always passes. Review 5 supplies the verify-or-supply body.\n"
    )
    # Composed run-binding header at the end.
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## Run-Binding Header (derived from dispatch-wrapper card + model delta)")
    parts.append("")
    parts.append(header)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Explain mode.
# ---------------------------------------------------------------------------

def explain(
    model: str,
    wrapper_path: Path,
    delta_path: Path,
    models_dir: Path,
) -> None:
    """Print provenance info: source file paths + pre-flight outcomes."""
    print(f"=== Scaffold Provenance ===")
    print(f"Model:            {model}")
    print(f"Wrapper card:     {wrapper_path}")
    print(f"Model delta:      {delta_path}")
    print(f"Models directory: {models_dir}")
    print()
    print("=== Pre-flight Checks ===")

    # Run checks in report-only mode (don't exit on failure).
    checks = [
        ("Package installed", lambda: _check_pkg(model, models_dir)),
        ("Manual fresh", lambda: _check_manual(model)),
        ("Guidance file", lambda: _check_guidance(model, models_dir)),
    ]
    for name, check_fn in checks:
        ok, msg = check_fn()
        status = "PASS" if ok else f"FAIL — {msg}"
        print(f"  [{status}] {name}")
    print()


def _check_pkg(model: str, models_dir: Path) -> tuple[bool, str]:
    model_dir = models_dir / model
    if not model_dir.is_dir():
        return False, f"model package '{model}' not found"
    if not (model_dir / DELTA_FILENAME).exists():
        return False, f"no {DELTA_FILENAME}"
    return True, ""


def _check_manual(model: str) -> tuple[bool, str]:
    import subprocess
    result = subprocess.run(
        [sys.executable, str(RENDER_MANUALS), "--check", "--model", model],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(RBTV_ROOT),
    )
    if result.returncode != 0:
        return False, "manual stale"
    return True, ""


def _check_guidance(model: str, models_dir: Path) -> tuple[bool, str]:
    # DEFERRED no-op — Review 5/G3 track.
    return True, "DEFERRED (Review-5/G3 track) — no-op"


# ---------------------------------------------------------------------------
# Main driver.
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate per-model dispatch task files from the dispatch-wrapper "
                    "card + model delta. Boilerplate is DERIVED, never hardcoded.",
    )
    parser.add_argument("--model", required=True, help="Worker model package id.")
    parser.add_argument("--output-folder", required=True, type=Path, help="Output directory.")
    parser.add_argument("--filename", required=True, help="Output filename.")
    parser.add_argument(
        "--instructions",
        help="Task-specific instructions (file path or inline string). Flips to complete mode.",
    )
    parser.add_argument(
        "--explain", action="store_true",
        help="Print composed source paths + pre-flight outcomes.",
    )
    # Overridable source paths (for testing / derive-test injection).
    parser.add_argument("--wrapper", type=Path, default=None, help="Override wrapper card path.")
    parser.add_argument("--model-dir", type=Path, default=None, help="Override models directory.")

    args = parser.parse_args(argv)

    # Resolve paths.
    wrapper_path = args.wrapper or DEFAULT_WRAPPER_PATH
    models_dir = args.model_dir or DEFAULT_MODELS_DIR
    delta_path = models_dir / args.model / DELTA_FILENAME
    output_path = Path(args.output_folder) / args.filename

    # Import render-manuals primitives.
    render_mod = _import_render_primitives()

    # --- Pre-flight checks (S6) ---
    preflight_check_package(args.model, models_dir)
    preflight_check_manual_fresh(args.model)
    preflight_check_guidance(args.model, models_dir)
    preflight_check_output_folder(Path(args.output_folder))

    # --- Parse sources ---
    if not wrapper_path.exists():
        _fail(f"wrapper card not found: {wrapper_path}")
    if not delta_path.exists():
        _fail(f"model delta not found: {delta_path}")

    delta_text = delta_path.read_text(encoding="utf-8")

    # Extract required sections from delta.
    fm_keys, body_headers = parse_required_sections(delta_text, args.model)
    if not fm_keys or not body_headers:
        _fail(
            f"model '{args.model}' delta lacks a machine-readable required-frontmatter / "
            f"required-body-sections block — the scaffold refuses to guess a skeleton from prose. "
            f"Structure the blocks in the delta or declare a parse convention."
        )

    # Compose run-binding header.
    header = compose_run_binding_header(args.model, wrapper_path, delta_path, render_mod)

    # Extract launch flags (carrier-aware — ADX-18 #1).
    launch_flags = extract_launch_flags(delta_text, args.model, models_dir)

    # --- G3 hook ---
    hook_pass, hook_msg = pre_dispatch_hook(
        args.model, str(Path(args.output_folder)), str(output_path),
    )
    if not hook_pass:
        _fail(f"pre-dispatch hook failed: {hook_msg}")

    # --- Check for file collision ---
    if output_path.exists():
        _fail(
            f"output file already exists: {output_path} — "
            f"refusing to clobber. Use a different --filename or remove the existing file."
        )

    # --- Explain mode (prints provenance + pre-flight; still writes) ---
    if args.explain:
        explain(args.model, wrapper_path, delta_path, models_dir)

    # --- Build output ---
    if args.instructions:
        # Complete mode: read instructions from file if it looks like a path.
        instr_path = Path(args.instructions)
        if instr_path.is_file():
            instructions = instr_path.read_text(encoding="utf-8")
        else:
            instructions = args.instructions

        content = build_complete_output(
            args.model, header, fm_keys, body_headers, instructions, launch_flags,
        )
    else:
        # Skeleton mode.
        content = build_skeleton_output(
            args.model, header, fm_keys, body_headers, launch_flags,
        )

    # --- Write ---
    try:
        output_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        _fail(f"write failed: {output_path}: {exc}")

    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
