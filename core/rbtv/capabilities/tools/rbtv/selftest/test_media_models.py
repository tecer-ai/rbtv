"""Audio model selections survive refresh and refuse malformed values."""
from discovery import Refuse
from lib import schema
from lib.state import read_state, write_state


def media_models(ctx):
    for agent in (False, True):
        target = ctx.tmp / ("media-agent" if agent else "media-installation")
        target.mkdir()
        if agent:
            (target / "prompt.md").write_text("Test agent.\n", encoding="utf-8")
            (target / "agent.json").write_text('{"name":"media-agent","description":"Test"}', encoding="utf-8")
        state = read_state(target)
        state["transcription_model"] = "onnx-asr/nemo-parakeet-tdt-0.6b-v3"
        state["generation_model"] = "elevenlabs/eleven_flash_v2_5"
        write_state(target, state)
        saved = read_state(target)
        ctx.check(f"media — {'agent' if agent else 'installation'} model selections survive state writes",
                  saved["transcription_model"] == "onnx-asr/nemo-parakeet-tdt-0.6b-v3"
                  and saved["generation_model"] == "elevenlabs/eleven_flash_v2_5")
        for value in (None, "", "   "):
            state["transcription_model"] = value
            write_state(target, state)
            ctx.check(f"media — blank inheritance {agent} {value!r}",
                      read_state(target)["transcription_model"] == value)
        before = (target / ("agent.json" if agent else ".rbtv/config/install.json")).read_bytes()
        for value in (42, {}, "../outside/model", "scribe_v2"):
            state["transcription_model"] = value
            try:
                write_state(target, state)
                refused = False
            except Refuse:
                refused = True
            ctx.check(f"media — malformed selection refused before write {agent} {value!r}", refused)
        ctx.check(f"media — refusal preserves record {agent}",
                  (target / ("agent.json" if agent else ".rbtv/config/install.json")).read_bytes() == before)
    for stem in ("agent-json", "install-json"):
        shape = schema.load(stem)["properties"]["transcription_model"]
        ctx.check(f"media — {stem} permits a blank selection", not schema.errors(None, shape))
        ctx.check(f"media — {stem} refuses an unqualified model", bool(schema.errors("scribe_v2", shape)))
