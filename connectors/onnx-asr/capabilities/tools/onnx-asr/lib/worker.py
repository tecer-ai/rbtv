"""Local, resident inference. One JSON request and response per line on stdio.

The Node adapter owns the process lifecycle and serializes requests. Nothing is
downloaded: model_path must hold a complete onnx-asr model and VAD is bundled
with faster-whisper. stdout carries only protocol responses.
"""
import contextlib
import json
import sys
from pathlib import Path


def main():
    # Some numerical libraries print while importing or loading weights.
    with contextlib.redirect_stdout(sys.stderr):
        import onnx_asr
        import onnxruntime as ort
        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import get_speech_timestamps, VadOptions
        config = json.loads(sys.argv[1])
        folder = Path(config["model_path"])
        if not folder.is_dir():
            raise ValueError(f"model_path is not a directory: {folder}")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = config["threads"]
        opts.inter_op_num_threads = 1
        model = onnx_asr.load_model(config["model"], path=folder,
                                   quantization="int8", sess_options=opts,
                                   providers=["CPUExecutionProvider"])
    for line in sys.stdin:
        try:
            request = json.loads(line)
            with contextlib.redirect_stdout(sys.stderr):
                audio = decode_audio(request["file"])
                chunks = get_speech_timestamps(audio, VadOptions(
                    max_speech_duration_s=20, speech_pad_ms=200), sampling_rate=16000)
                text = " ".join(model.recognize(audio[c["start"]:c["end"]],
                                                sample_rate=16000) for c in chunks).strip()
            if not text:
                raise ValueError("no speech recognized")
            response = {"text": text, "model_id": config["model"], "source": request["file"]}
        except Exception as exc:
            response = {"error": str(exc)}
        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), flush=True)
        raise SystemExit(1)
