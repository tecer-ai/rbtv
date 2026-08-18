#!/usr/bin/env python3
"""scaffold.py — generate dispatch task files from the dispatch-wrapper card + cast argv.

Composes dispatch boilerplate from the dispatch-wrapper card and the catalog
pair `cast route --catalog` names.

Usage (run from the rbtv repo root):
    python orchestration/skills/orchestrating/scripts/scaffold.py \\
        --model sonnet-5 --output-folder <dir> --filename <name>
    python ... --model sonnet-5 --harness claude --output-folder <dir> \\
        --filename <name> --instructions <file-or-inline>
    python ... --explain
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
_ORCH_DIR_FROM_SCRIPT = SCRIPT_PATH.parent.parent.parent.parent
RBTV_ROOT = _ORCH_DIR_FROM_SCRIPT.parent
ORCH_DIR = _ORCH_DIR_FROM_SCRIPT

DEFAULT_WRAPPER_PATH = (
    ORCH_DIR / "skills" / "orchestrating" / "cards" / "dispatch-wrapper.md"
)

_GENERIC_FM_KEYS = [
    "execution_kind", "executor", "allowed_workdir", "allowlist",
    "commit_policy", "test_command", "forbidden_ops", "doubt_policy",
    "reviewer",
]

_GENERIC_BODY_SECTIONS = [
    "Goal", "Context Snapshot", "Allowed Paths", "Forbidden Paths",
    "Implementation Requirements", "Validation", "Commit Rule",
    "Return Format",
]


def _placeholder_value(key: str) -> str:
    placeholders = {
        "execution_kind": "<code|research>",
        "executor": "<harness/model>",
        "allowed_workdir": "<repo-path>",
        "allowlist": "\n  - <file-or-folder-glob>",
        "commit_policy": "<local-only|none>",
        "test_command": "<command-or-NONE>",
        "forbidden_ops": "\n  - git push\n  - writes outside allowlist\n  - destructive git reset\n  - external production API calls",
        "doubt_policy": "halt",
        "reviewer": "<reviewer-harness/model>",
    }
    return placeholders.get(key, f"<{key}>")


def generate_frontmatter_skeleton(keys: list[str]) -> str:
    lines = ["---"]
    for key in keys:
        val = _placeholder_value(key)
        if "\n" in val:
            lines.append(f"{key}:{val}")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    return "\n".join(lines)


def _fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_catalog() -> list[dict]:
    result = subprocess.run(
        ["cast", "route", "--catalog", "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        _fail(f"pre-flight: cast route --catalog failed (exit {result.returncode}): {stderr}")
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        _fail(f"pre-flight: cast route --catalog did not emit JSON: {exc}")
    if not isinstance(rows, list):
        _fail("pre-flight: cast route --catalog JSON is not a list")
    return rows


def preflight_check_catalog(model: str, harness: str | None = None) -> dict:
    rows = load_catalog()
    matches = [r for r in rows if r.get("model") == model]
    if harness:
        matches = [r for r in matches if r.get("harness") == harness]
    if not matches:
        pair = f"harness={harness} model={model}" if harness else f"model={model}"
        _fail(f"pre-flight: catalog does not name pair {pair}")
    return matches[0]


def preflight_check_guidance(_model: str) -> None:
    pass


def preflight_check_output_folder(output_folder: Path) -> None:
    if not output_folder.is_dir():
        _fail(f"pre-flight: output folder does not exist: {output_folder}")


def compose_run_binding_header(wrapper_path: Path) -> str:
    if not wrapper_path.exists():
        _fail(f"wrapper card not found: {wrapper_path}")
    text = wrapper_path.read_text(encoding="utf-8")
    start = text.find("## 2. The binding addendum")
    end = text.find("## 4. Tripwires")
    if start == -1:
        start = text.find("## 2.")
    if end == -1:
        end = text.find("## 4.")
    if start == -1:
        return text
    if end == -1:
        return text[start:].strip() + "\n"
    return text[start:end].strip() + "\n"


def compose_invocation_note(row: dict) -> str:
    harness = row.get("harness", "<harness>")
    model = row.get("model", "<model>")
    carrier = row.get("carrier", "cli")
    if carrier == "agent-tool":
        return (
            "### Invocation note (Agent-tool dispatch)\n\n"
            "Agent-tool dispatch — no CLI invocation; the prompt is the Agent tool's prompt parameter.\n"
            "`cast` refuses to launch `carrier: agent-tool` rows.\n"
        )
    if carrier == "api":
        return (
            "### Invocation note (API dispatch)\n\n"
            f"`cast api {model} <effort> -f <task file> --output-folder <dir>`\n"
            "Use `--grounded` / `--extra-params` as the `[mode]` surface. "
            "`cast --dry-run` is the composition check.\n"
        )
    return (
        "### Invocation note (cast argv)\n\n"
        f"`cast {harness} {model} <effort> <launch-root> -f <task file>`\n"
        "Absolute paths. Binary-first (D17): the line begins with `cast`. "
        "`cast --dry-run` is the composition check.\n"
        "G1: launch-folder = orchestrator root; work-target via `--add-dir` "
        "(opencode exception: launch root IS the target).\n"
    )


def pre_dispatch_hook(model: str, work_dir: str, output_path: str) -> tuple[bool, str]:
    return True, ""


def build_skeleton_output(
    model: str,
    header: str,
    fm_keys: list[str],
    body_headers: list[str],
    launch_flags: str,
) -> str:
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
    parts.append("## Pre-Dispatch Hook")
    parts.append("")
    parts.append(
        "A named pre-dispatch hook slot exists (`pre_dispatch_hook` in scaffold.py) — "
        "default no-op, always passes. Review 5 supplies the verify-or-supply body.\n"
    )
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## Run-Binding Header (derived from dispatch-wrapper card + cast argv)")
    parts.append("")
    parts.append(header)
    return "\n".join(parts)


def _parse_instruction_headings(instructions: str) -> dict[str, str]:
    task_specific = {"Goal", "Context Snapshot", "Allowed Paths", "Forbidden Paths",
                     "Implementation Requirements", "Validation", "Commit Rule",
                     "Swarm Rule", "Return Format"}

    sections: dict[str, str] = {}
    current_heading: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if current_heading is None:
            return
        text = "\n".join(buf).strip()
        if not text:
            return
        if current_heading in sections:
            sections[current_heading] += "\n" + text
        else:
            sections[current_heading] = text

    in_fence = False
    for line in instructions.splitlines():
        stripped = line.lstrip()
        is_fence = stripped.startswith("```") or stripped.startswith("~~~")
        m = None if (in_fence or is_fence) else re.match(r'^#{1,3}\s+(.+)$', line)
        if is_fence:
            in_fence = not in_fence
        if m:
            heading_name = m.group(1).strip()
            if heading_name in task_specific:
                flush()
                current_heading = heading_name
                buf = []
            else:
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

    flush()
    return {k: v for k, v in sections.items() if v}


def build_complete_output(
    model: str,
    header: str,
    fm_keys: list[str],
    body_headers: list[str],
    instructions: str,
    launch_flags: str,
) -> str:
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

    if launch_flags:
        parts.append(launch_flags)
        parts.append("")

    parts.append("## Pre-Dispatch Hook")
    parts.append("")
    parts.append(
        "A named pre-dispatch hook slot exists (`pre_dispatch_hook` in scaffold.py) — "
        "default no-op, always passes. Review 5 supplies the verify-or-supply body.\n"
    )
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## Run-Binding Header (derived from dispatch-wrapper card + cast argv)")
    parts.append("")
    parts.append(header)
    return "\n".join(parts)


def _extract_frontmatter(text: str) -> tuple[str | None, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm_inner = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1:])
            return fm_inner, body
    return None, text


def _top_level_fm_keys(fm_inner: str) -> set[str]:
    keys: set[str] = set()
    for line in fm_inner.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):", line)
        if m:
            keys.add(m.group(1))
    return keys


def is_preauthored_brief(text: str) -> bool:
    fm_inner, _ = _extract_frontmatter(text)
    if fm_inner is not None:
        return True
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.match(r"^#\s+\S", line):
            return True
    return False


def build_preauthored_output(
    model: str,
    header: str,
    fm_keys: list[str],
    brief: str,
    launch_flags: str,
) -> str:
    fm_inner, body = _extract_frontmatter(brief)

    if fm_inner is not None:
        existing = _top_level_fm_keys(fm_inner)
        fm_lines = ["---"]
        if fm_inner:
            fm_lines.extend(fm_inner.splitlines())
        for key in fm_keys:
            if key in existing:
                continue
            val = _placeholder_value(key)
            if "\n" in val:
                fm_lines.append(f"{key}:{val}")
            else:
                fm_lines.append(f"{key}: {val}")
        fm_lines.append("---")
        parts = ["\n".join(fm_lines)]
        body_text = body
    else:
        parts = [generate_frontmatter_skeleton(fm_keys)]
        body_text = brief

    parts.append("")
    parts.append(body_text.strip("\n"))
    parts.append("")

    if launch_flags:
        parts.append(launch_flags)
        parts.append("")

    parts.append("## Pre-Dispatch Hook")
    parts.append("")
    parts.append(
        "A named pre-dispatch hook slot exists (`pre_dispatch_hook` in scaffold.py) — "
        "default no-op, always passes. Review 5 supplies the verify-or-supply body.\n"
    )
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## Run-Binding Header (derived from dispatch-wrapper card + cast argv)")
    parts.append("")
    parts.append(header)
    return "\n".join(parts)


def explain(model: str, wrapper_path: Path, row: dict) -> None:
    print("=== Scaffold Provenance ===")
    print(f"Model:            {model}")
    print(f"Harness:          {row.get('harness')}")
    print(f"Carrier:          {row.get('carrier')}")
    print(f"Wrapper card:     {wrapper_path}")
    print()
    print("=== Pre-flight Checks ===")
    print("  [PASS] Catalog names the pair")
    print("  [PASS] Guidance file (DEFERRED no-op)")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate dispatch task files from the dispatch-wrapper "
                    "card + cast argv. Boilerplate is DERIVED, never hardcoded.",
    )
    parser.add_argument("--model", required=True, help="Catalog short-name model.")
    parser.add_argument("--harness", default=None, help="Catalog harness (optional filter).")
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
    parser.add_argument("--wrapper", type=Path, default=None, help="Override wrapper card path.")

    args = parser.parse_args(argv)

    wrapper_path = args.wrapper or DEFAULT_WRAPPER_PATH
    output_path = Path(args.output_folder) / args.filename

    row = preflight_check_catalog(args.model, args.harness)
    preflight_check_guidance(args.model)
    preflight_check_output_folder(Path(args.output_folder))

    header = compose_run_binding_header(wrapper_path)
    launch_flags = compose_invocation_note(row)
    fm_keys = list(_GENERIC_FM_KEYS)
    body_headers = list(_GENERIC_BODY_SECTIONS)

    hook_pass, hook_msg = pre_dispatch_hook(
        args.model, str(Path(args.output_folder)), str(output_path),
    )
    if not hook_pass:
        _fail(f"pre-dispatch hook failed: {hook_msg}")

    if output_path.exists():
        _fail(
            f"output file already exists: {output_path} — "
            f"refusing to clobber. Use a different --filename or remove the existing file."
        )

    if args.explain:
        explain(args.model, wrapper_path, row)

    if args.instructions:
        instr_path = Path(args.instructions)
        if instr_path.is_file():
            instructions = instr_path.read_text(encoding="utf-8")
        else:
            instructions = args.instructions

        if is_preauthored_brief(instructions):
            content = build_preauthored_output(
                args.model, header, fm_keys, instructions, launch_flags,
            )
        else:
            content = build_complete_output(
                args.model, header, fm_keys, body_headers, instructions, launch_flags,
            )
    else:
        content = build_skeleton_output(
            args.model, header, fm_keys, body_headers, launch_flags,
        )

    try:
        output_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        _fail(f"write failed: {output_path}: {exc}")

    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
