"""Integration test: the runner's main() actually invokes write_artifacts.

Drives run.main() end-to-end with a FAKE client injected (no provider call, no
network, no spend). Proves the wiring: a Manus-shaped Response (narration +
attachments + structured result) lands raw-output.md, the artifact files, and
structured-output.json together, with return.json un-clobbered.
"""
import json
import sys
import types

import pytest

import run
from clients.base import Artifact, ProviderClient, ProviderName, Response


class FakeManusClient(ProviderClient):
    """A real ProviderClient subclass so run.main()'s discovery loop selects it.

    structured_output=False routes through the raw-dump path (as Manus does).
    """
    structured_output = False

    @property
    def name(self) -> ProviderName:
        return ProviderName.MANUS

    def initialize(self, config) -> None:
        self._config = config

    def chat(self, messages, options=None) -> Response:
        return Response(
            content="Here is your deck.",
            artifacts=[
                Artifact(filename="deck.pdf", content=b"DECKBYTES",
                         content_type="application/pdf", source_url="u1"),
            ],
            structured_result={"success": True, "value": {"k": "v"}, "error": None},
            raw_response={"task_id": "t", "artifact_errors": []},
        )


def test_main_writes_artifacts_end_to_end(tmp_path, monkeypatch):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("build a deck", encoding="utf-8")
    out_dir = tmp_path / "out"

    # Inject a fake clients.<provider> module exposing FakeManusClient.
    fake_mod = types.ModuleType("clients.manus")
    fake_mod.FakeManusClient = FakeManusClient
    monkeypatch.setattr(run.importlib, "import_module", lambda name: fake_mod)
    # Skip real key resolution (no env, no .env needed).
    monkeypatch.setattr(run, "_resolve_key", lambda provider, api_dir: "fake-key")

    argv = [
        "run.py",
        "--provider", "manus",
        "--model", "manus-default",
        "--prompt-file", str(prompt_file),
        "--output-folder", str(out_dir),
    ]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc:
        run.main()
    assert exc.value.code == 0

    # narration dumped (Manus has structured_output=False -> raw-dump path)
    assert (out_dir / "raw-output.md").read_text(encoding="utf-8") == "Here is your deck."
    # artifact written with bytes intact
    assert (out_dir / "deck.pdf").read_bytes() == b"DECKBYTES"
    # structured result written
    assert json.loads((out_dir / "structured-output.json").read_text(encoding="utf-8")) == {
        "success": True, "value": {"k": "v"}, "error": None,
    }
    # return.json present; landed lists all three deliverables
    return_data = json.loads((out_dir / "return.json").read_text(encoding="utf-8"))
    assert "raw-output.md" in return_data["landed"]
    assert "deck.pdf" in return_data["landed"]
    assert "structured-output.json" in return_data["landed"]
    assert return_data["validation"]["artifact_count"] == 1
