"""Run speech dependencies in their own process; emit JSON on the last line."""
import json
import sys
from pathlib import Path

mode, root, wav = sys.argv[1:4]
root = Path(root)
request = json.load(sys.stdin)
if mode == "align":
    import torch
    from qwen_asr import Qwen3ForcedAligner
    torch.set_num_threads(6)
    aligner = Qwen3ForcedAligner.from_pretrained(str(root / "models/align"), device_map="cpu", dtype=torch.float32)
    result = aligner.align(audio=wav, text=request["text"], language="English")[0]
    print(json.dumps([{"word": x.text, "start": x.start_time, "end": x.end_time} for x in result]))
elif mode == "asr":
    import numpy as np
    import subprocess
    from faster_whisper import WhisperModel
    model = WhisperModel(str(root / "models/asr"), device="cpu", compute_type="int8", cpu_threads=5)
    ff = Path.home() / "ai/tools/media/bin/ffmpeg"
    audio = subprocess.check_output([str(ff), "-v", "error", "-i", wav, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"])
    segments, _ = model.transcribe(np.frombuffer(audio, dtype="<f4"), language="en", beam_size=5,
                                   condition_on_previous_text=False, word_timestamps=True)
    print(json.dumps([{"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                      for segment in segments for w in segment.words]))
else:
    import fcntl
    import soundfile as sf
    from voice_profiles import synthesize
    with (root / "gpu.lock").open("a") as lock:
        if mode in ("ryan", "laura"):
            fcntl.flock(lock, fcntl.LOCK_EX)
        audio, rate = synthesize(mode, root / "models" / mode, [request["text"]])
        sf.write(wav, audio[0], rate, subtype="FLOAT")
    print("{}")
