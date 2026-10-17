# onnx-asr

`onnx-asr` transcribes a local audio file on CPU through the onnx-asr Python package. `onnx-asr -h` and `onnx-asr transcribe -h` own the command's flags, output and exit codes. It uses no external transcription API. The first supported configuration is Parakeet TDT 0.6B v3 with INT8 ONNX weights; another model requires compatible local weights and its own fidelity and latency checks.

Create `.rbtv/config/onnx-asr/config.json` in the installation:

```json
{
  "python": "python3",
  "model_path": "resources/models/parakeet-v3-int8",
  "threads": 8
}
```

`model_path` is required and relative to the installation, or absolute. `python` is an executable on PATH or a path relative to the installation; on Windows it may be `python` or the virtual environment's `Scripts/python.exe`. Install the component record's Python packages into that interpreter and place the model files in `model_path` before using it. No command downloads weights. `threads` is an integer from 1 to 64, default 8. Keep weights, environments and this machine's configuration out of Git.

The Node adapter at `lib/media.js` exports `media.transcribe({file, model, workspace})`, where `workspace` is the installation root and `model` defaults to `nemo-parakeet-tdt-0.6b-v3`. It returns `{text, model_id, source}`. The command calls that same operation. The adapter keeps one Python worker resident per model configuration and serializes concurrent calls through it. A worker error rejects the call; a later call can start a new worker. `close()` releases workers at shutdown. Files are decoded to 16 kHz mono; bundled Silero voice detection splits speech into chunks of at most 20 seconds. Empty speech is an error.

Use the [installation audio defaults](../../../../../core/rbtv/capabilities/glossary/install-json.md) to select this connector in Ignite. Select generation separately through a connector that provides `media.speak`.

Offline lifecycle checks: `node --test test_media.js`. A real inference check additionally needs installed weights and Python packages; a fixture worker does not prove transcription quality.
