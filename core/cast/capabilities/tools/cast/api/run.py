"""The runner behind `cast api`: one image-generation call.

`cast api` invokes this. It resolves the provider's API key, sends the prompt
(and any input images) through a dynamically-resolved client, writes the image
files the model returns into --output-folder, and writes return.json.
"""

import argparse
import base64
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


_INSTALL_RECORD = pathlib.Path(".rbtv", "config", "install.json")
_ENV_FILE = pathlib.Path(".rbtv", "config", "env", ".env")


def _find_installation(start: pathlib.Path) -> Optional[pathlib.Path]:
    """Walk up from *start* to the first folder holding the installation record."""
    for parent in [start, *start.parents]:
        if (parent / _INSTALL_RECORD).is_file():
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


def _resolve_key(provider: str, launch_dir: pathlib.Path) -> str:
    """Resolve the API key for *provider* without ever exposing it.

    The OS environment first, then the environment file of the installation
    that holds *launch_dir*.
    """
    key_var = f"{provider.upper()}_API_KEY"
    key = os.environ.get(key_var)
    if key:
        return key

    installation = _find_installation(launch_dir.resolve())
    if installation:
        try:
            env_vars = _parse_dotenv(installation / _ENV_FILE)
        except OSError:
            env_vars = {}
        key = env_vars.get(key_var)
        if key:
            return key

    print(
        f"ERROR: missing API key {key_var} (not in OS env, not in the "
        f"installation's {_ENV_FILE.as_posix()})",
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


def _dedup_name(name: str, taken: set) -> str:
    """Return *name*, or *name* with a numeric suffix, so it is not in *taken*."""
    if name not in taken:
        return name
    stem, dot, ext = name.partition(".")
    suffix = f".{ext}" if dot else ""
    i = 1
    while True:
        candidate = f"{stem}-{i}{suffix}"
        if candidate not in taken:
            return candidate
        i += 1


def write_artifacts(
    response: Any,
    output_folder: str,
    landed: List[str],
    validation: Dict[str, Any],
    concerns: List[str],
) -> None:
    """Write a response's file artifacts and structured result to *output_folder*.

    Generic across providers. Artifact filenames are sanitised and de-duplicated
    against everything already in *landed* (which includes reserved names like
    return.json / raw-output.md), so an artifact never clobbers another file.
    Mutates *landed*, *validation*, and *concerns* in place.
    """
    artifacts = getattr(response, "artifacts", None) or []
    structured_result = getattr(response, "structured_result", None)

    os.makedirs(output_folder, exist_ok=True)

    # Reserve everything already written plus the runner's own return.json.
    taken = set(landed)
    taken.add("return.json")

    written = 0
    for artifact in artifacts:
        safe = sanitize_path(artifact.filename, output_folder)
        safe = _dedup_name(safe, taken)
        taken.add(safe)
        out_path = pathlib.Path(output_folder) / safe
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(artifact.content)
        landed.append(safe)
        written += 1

    validation["artifact_count"] = written

    if structured_result is not None:
        safe = _dedup_name("structured-output.json", taken)
        taken.add(safe)
        out_path = pathlib.Path(output_folder) / safe
        out_path.write_text(json.dumps(structured_result, indent=2), encoding="utf-8")
        landed.append(safe)

    # Surface any download failures the client recorded as concerns.
    raw = getattr(response, "raw_response", None) or {}
    for err in raw.get("artifact_errors", []) or []:
        concerns.append(
            f"artifact download failed: {err.get('filename')} "
            f"({err.get('url')}) — {err.get('error')}"
        )


# Extensions Gemini's inline-image input actually accepts. Refusing anything outside this set
# beats guessing a mime type from bytes — a wrong guess is a silent bad request at the provider,
# a refusal here is a clear one at the CLI.
_INPUT_IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _build_input_image_parts(paths: List[str]) -> List[Dict[str, Any]]:
    """Read each --input-image path and return it as a provider-neutral image part.

    Provider-neutral so run.py stays provider-agnostic (its stated design) — only
    clients/gemini.py knows how to translate {"type": "image", ...} onto Google's wire shape.
    """
    parts: List[Dict[str, Any]] = []
    for raw in paths:
        path = pathlib.Path(raw)
        mime = _INPUT_IMAGE_MIME.get(path.suffix.lower())
        if mime is None:
            print(
                f"ERROR: --input-image '{raw}' has an unsupported extension "
                f"'{path.suffix}' — accepted: {', '.join(sorted(_INPUT_IMAGE_MIME))}",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            data = path.read_bytes()
        except OSError as exc:
            print(f"ERROR: cannot read --input-image '{raw}': {exc}", file=sys.stderr)
            sys.exit(1)
        parts.append({"type": "image", "mime_type": mime, "data": base64.b64encode(data).decode("ascii")})
    return parts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Runner for one image-generation API call")
    parser.add_argument("--provider", required=True, help="Provider name (e.g. gemini)")
    parser.add_argument("--model", required=True, help="Model identifier")
    parser.add_argument("--prompt-file", required=True, help="Path to the prompt file")
    parser.add_argument("--output-folder", required=True, help="Directory to write outputs")
    parser.add_argument("--target-file", default=None, help="Optional target file to inline")
    parser.add_argument("--timeout", type=int, default=None,
        help="Per-call timeout in seconds passed to the client. Omit to use the client's own default.")
    parser.add_argument("--input-image", action="append", default=None,
        help="Path to an existing image file to send INTO the model alongside the prompt (repeatable, order preserved). Extension must be png/jpg/jpeg/webp/gif.")
    parser.add_argument("--extra-params", type=str, default=None,
        help="A JSON object sent to the provider as RequestOptions.extra_params (advanced pass-through).")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    extra_params: Optional[Dict[str, Any]] = None
    if args.extra_params:
        try:
            extra_params = json.loads(args.extra_params)
        except (json.JSONDecodeError, TypeError):
            print("ERROR: --extra-params must be a JSON object", file=sys.stderr)
            sys.exit(1)
        if not isinstance(extra_params, dict):
            print("ERROR: --extra-params must be a JSON object", file=sys.stderr)
            sys.exit(1)

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
    key = _resolve_key(args.provider, pathlib.Path.cwd())

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

    # --- build the message ---
    # One user message and no system message: an image model takes the prompt as the whole
    # instruction, and a systemInstruction is not universally accepted on that endpoint. An input
    # image turns the message into the provider-neutral part-list form (see clients/base.py
    # Message.content) instead of a plain string.
    if args.input_image:
        user_content: Any = [{"type": "text", "text": prompt_text}, *_build_input_image_parts(args.input_image)]
    else:
        user_content = prompt_text
    messages = [Message(role="user", content=user_content)]

    # --- call provider ---
    status = "BLOCKED"
    landed: List[str] = []
    validation: Dict[str, Any] = {"finish_reason": None, "file_count": 0}
    concerns: List[str] = []
    open_questions: List[str] = []

    try:
        client.initialize(ProviderConfig(api_key=key, timeout=args.timeout))
        response = client.chat(messages, RequestOptions(model=args.model, extra_params=extra_params))
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

    # The images ARE the return. write_artifacts sanitises and de-dups the filenames the client
    # derived from each inline part's mime type. Any accompanying text is kept only when the
    # model sent one — it is commentary, never the deliverable.
    write_artifacts(response, args.output_folder, landed, validation, concerns)
    if validation.get("artifact_count"):
        status = "DONE"
        if response.content:
            note_path = pathlib.Path(args.output_folder) / "raw-output.md"
            note_path.write_text(response.content, encoding="utf-8")
            landed.append("raw-output.md")
    else:
        raw_path = pathlib.Path(args.output_folder) / "raw-output.md"
        raw_path.write_text(response.content or "", encoding="utf-8")
        landed.append("raw-output.md")
        concerns.append(
            "image dispatch returned no inline image data — whatever the model did send "
            "is in raw-output.md"
        )
        status = "DONE_WITH_NOTES"

    # truncation check
    if finish_reason is not None and finish_reason != "stop":
        concerns.append(f"finish_reason was '{finish_reason}' — response may be truncated")
        status = "DONE_WITH_NOTES"

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
