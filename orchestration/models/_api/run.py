"""Shared CLI runner for model API calls.

The conductor invokes this via Bash. It resolves the provider's API key,
calls the provider in JSON mode via a dynamically-resolved client, writes
model-emitted envelope files into --output-folder, and writes return.json.
"""

import argparse
import importlib
import json
import os
import pathlib
import sys
import traceback
from typing import Any, Dict, List, Optional

_API_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_API_DIR))

from clients.base import ProviderClient, ProviderConfig, RequestOptions, Message  # noqa: E402


def _find_rbtv_json_dir(start: pathlib.Path) -> Optional[pathlib.Path]:
    """Walk up from *start* looking for the first dir containing rbtv.json."""
    for parent in [start, *start.parents]:
        if (parent / "rbtv.json").is_file():
            return parent
    return None


def _parse_dotenv(env_path: pathlib.Path) -> Dict[str, str]:
    """Parse a simple KEY=VALUE .env file."""
    result: Dict[str, str] = {}
    with env_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'").strip("\"'")
            result[key] = value
    return result


def _resolve_key(provider: str, api_dir: pathlib.Path) -> str:
    """Resolve the API key for *provider* without ever exposing it."""
    key_var = f"{provider.upper()}_API_KEY"
    key = os.environ.get(key_var)
    if key:
        return key

    rbtv_dir = _find_rbtv_json_dir(api_dir)
    if rbtv_dir:
        rbtv_path = rbtv_dir / "rbtv.json"
        try:
            with rbtv_path.open("r", encoding="utf-8") as fh:
                rbtv_data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            rbtv_data = {}
        env_file = rbtv_data.get("env_file")
        if env_file:
            env_path = (rbtv_dir / env_file).resolve()
            try:
                env_vars = _parse_dotenv(env_path)
            except OSError:
                env_vars = {}
            key = env_vars.get(key_var)
            if key:
                return key

    print(
        f"ERROR: missing API key {key_var} (not in OS env, not in env_file)",
        file=sys.stderr,
    )
    sys.exit(1)


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Shared runner for model API calls")
    parser.add_argument("--provider", required=True, help="Provider name (e.g. deepseek)")
    parser.add_argument("--model", required=True, help="Model identifier")
    parser.add_argument("--prompt-file", required=True, help="Path to the prompt file")
    parser.add_argument("--output-folder", required=True, help="Directory to write outputs")
    parser.add_argument("--target-file", default=None, help="Optional target file to inline")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # --- dynamic client resolution ---
    try:
        mod = importlib.import_module(f"clients.{args.provider}")
    except Exception as exc:
        print(f"ERROR: failed to import clients.{args.provider}: {exc}", file=sys.stderr)
        sys.exit(1)

    client_cls = None
    for obj in vars(mod).values():
        if (
            isinstance(obj, type)
            and issubclass(obj, ProviderClient)
            and obj is not ProviderClient
        ):
            client_cls = obj
            break

    if client_cls is None:
        print(
            f"ERROR: no ProviderClient subclass found in clients.{args.provider}",
            file=sys.stderr,
        )
        sys.exit(1)

    client = client_cls()

    # --- key discovery ---
    key = _resolve_key(args.provider, _API_DIR)

    # --- read prompt (and optional target file) ---
    prompt_path = pathlib.Path(args.prompt_file)
    try:
        prompt_text = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read prompt-file: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.target_file:
        target_path = pathlib.Path(args.target_file)
        try:
            target_content = target_path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: cannot read target-file: {exc}", file=sys.stderr)
            sys.exit(1)
        prompt_text += f"\n\n--- TARGET FILE: {target_path} ---\n{target_content}"

    # --- build messages ---
    system_msg = Message(
        role="system",
        content=(
            'Respond ONLY with a single JSON object of the exact shape: '
            '{"files": [{"path": "<relative path>", "content": "<file text>"}], '
            '"concerns": [], "open_questions": []}. '
            'Each file you want written goes in "files". Use relative paths only. '
            'Do not wrap the JSON in markdown fences.'
        ),
    )
    user_msg = Message(role="user", content=prompt_text)
    messages = [system_msg, user_msg]

    # --- call provider ---
    status = "BLOCKED"
    landed: List[str] = []
    validation: Dict[str, Any] = {
        "envelope_valid": False,
        "json_parsed": False,
        "finish_reason": None,
        "file_count": 0,
        "rejected_paths": [],
    }
    concerns: List[str] = []
    open_questions: List[str] = []

    try:
        client.initialize(ProviderConfig(api_key=key))
        response = client.chat(messages, RequestOptions(model=args.model))
    except Exception as exc:
        # Never leak the key in error output
        open_questions = [str(exc)]
        status = "BLOCKED"
        os.makedirs(args.output_folder, exist_ok=True)
        return_path = pathlib.Path(args.output_folder) / "return.json"
        return_path.write_text(
            json.dumps(
                {
                    "status": status,
                    "landed": landed,
                    "validation": validation,
                    "concerns": concerns,
                    "open_questions": open_questions,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"{status} | 0 files", file=sys.stdout)
        sys.exit(1)

    finish_reason = None
    if response.raw_response:
        finish_reason = response.raw_response.get("choices", [{}])[0].get("finish_reason")
    validation["finish_reason"] = finish_reason

    os.makedirs(args.output_folder, exist_ok=True)

    envelope_valid = False
    if client.structured_output:
        try:
            env = json.loads(response.content)
            validation["json_parsed"] = True
        except (json.JSONDecodeError, TypeError):
            env = None

        if (
            isinstance(env, dict)
            and "files" in env
            and isinstance(env["files"], list)
        ):
            envelope_valid = True
            for f in env["files"]:
                raw_path = f.get("path", "")
                safe = sanitize_path(raw_path, args.output_folder)
                if safe != raw_path:
                    validation["rejected_paths"].append(raw_path)
                out_path = pathlib.Path(args.output_folder) / safe
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(f.get("content", ""), encoding="utf-8")
                landed.append(safe)
            concerns = env.get("concerns", [])
            open_questions = env.get("open_questions", [])
            status = "DONE"
        else:
            envelope_valid = False

    if not envelope_valid:
        raw_path = pathlib.Path(args.output_folder) / "raw-output.md"
        raw_path.write_text(response.content or "", encoding="utf-8")
        landed = ["raw-output.md"]
        concerns = concerns or []
        concerns.append(
            "model did not return the {files:...} envelope — "
            "raw response dumped to raw-output.md"
        )
        status = "DONE_WITH_NOTES"

    # truncation check
    if finish_reason is not None and finish_reason != "stop":
        concerns.append(f"finish_reason was '{finish_reason}' — response may be truncated")
        status = "DONE_WITH_NOTES"

    validation["envelope_valid"] = envelope_valid
    validation["file_count"] = len(landed)

    return_data = {
        "status": status,
        "landed": landed,
        "validation": validation,
        "concerns": concerns,
        "open_questions": open_questions,
    }
    return_path = pathlib.Path(args.output_folder) / "return.json"
    return_path.write_text(json.dumps(return_data, indent=2), encoding="utf-8")

    print(f"{status} | {len(landed)} file(s)", file=sys.stdout)

    if status == "BLOCKED":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
