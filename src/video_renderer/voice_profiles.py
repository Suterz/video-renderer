import fcntl
import json
import os
import random
import sys
import time
from pathlib import Path

import soundfile as sf

PASSAGES = (
    "Which bag is cheaper per orange? Three oranges cost six dollars. Five cost eight. At checkout, the first bag costs less. But per orange? The second wins: one dollar sixty, instead of two.",
    "When a temperature sensor, mounted beside the greenhouse door, reads twenty-eight degrees Celsius, the controller compares that reading with its threshold. If the threshold is twenty-six degrees Celsius, which output changes? The fan switches on; the indicator stays blue.",
)
PRESENTER = ("Explain this to one curious learner. Let questions sound like questions, take a natural brief pause before the contrast, "
             "emphasize the deciding number and finish warmly, not like an advertisement. Use a clear, measured conversational pace.")
LAURA = ("Laura speaks warmly and curiously at a measured conversational pace, "
         "with clear emphasis on the comparison, a close microphone and very clear audio.")
SETTINGS = {
    "ryan": {"speaker": "Ryan", "language": "English", "style": PRESENTER, "attention": "sdpa", "precision": "BF16"},
    "heart": {"speaker": "af_heart", "speed": 1.0, "device": "cpu"},
    "chatter": {"speaker": "Publisher built-in conds.pt", "exaggeration": .55, "cfg_weight": .4, "device": "cpu"},
    "laura": {"speaker": "Laura", "style": LAURA, "attention": "eager"},
    "jasper": {"speaker": "Jasper", "speed": 1.0, "device": "cpu"},
}


def synthesize(name, model_path, texts):
    import numpy as np
    root = str(model_path)
    if name == "jasper":
        from kittentts.onnx_model import KittenTTS_1_Onnx
        cfg = json.loads((model_path / "config.json").read_text())
        m = KittenTTS_1_Onnx(model_path=str(model_path / cfg["model_file"]),
                              voices_path=str(model_path / cfg["voices"]),
                              speed_priors=cfg.get("speed_priors", {}),
                              voice_aliases=cfg.get("voice_aliases", {}))
        return [m.generate(t, voice="Jasper") for t in texts], 24000
    if name == "heart":
        from kokoro import KModel, KPipeline
        m = KModel(repo_id="hexgrad/Kokoro-82M", config=str(model_path / "config.json"),
                   model=str(model_path / "kokoro-v1_0.pth")).to("cpu").eval()
        pipeline = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", model=m, device="cpu")
        return [np.concatenate([a.audio.numpy() for a in pipeline(t, voice=str(model_path / "voices/af_heart.pt"))]) for t in texts], 24000
    import torch
    torch.manual_seed(437)
    if name == "ryan":
        from qwen_tts import Qwen3TTSModel
        m = Qwen3TTSModel.from_pretrained(root, device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa", local_files_only=True)
        waves = []
        for t in texts:
            parts, sr = m.generate_custom_voice(text=t, language="English", speaker="Ryan", instruct=PRESENTER)
            waves.append(parts[0])
        return waves, sr
    if name == "chatter":
        from chatterbox.tts import ChatterboxTTS
        m = ChatterboxTTS.from_local(model_path, "cpu")
        torch.set_num_threads(6)
        return [m.generate(t, exaggeration=.55, cfg_weight=.4).squeeze().numpy() for t in texts], m.sr
    if name == "laura":
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer
        m = ParlerTTSForConditionalGeneration.from_pretrained(root, local_files_only=True, attn_implementation="eager").to("cuda:0").eval()
        tok = AutoTokenizer.from_pretrained(root, local_files_only=True)
        conditioning = tok(LAURA, return_tensors="pt").to("cuda:0")
        with torch.inference_mode():
            waves = [m.generate(input_ids=conditioning.input_ids, attention_mask=conditioning.attention_mask,
                                prompt_input_ids=(p := tok(t, return_tensors="pt").to("cuda:0")).input_ids,
                                prompt_attention_mask=p.attention_mask).cpu().numpy().squeeze() for t in texts]
        return waves, m.config.sampling_rate
    raise ValueError(name)


def main():
    name, directory, revision = sys.argv[1:]
    base = Path(directory)
    random.seed(437)
    started = time.monotonic()
    with (base / "gpu.lock").open("a") as lease:
        if name in ("ryan", "laura"):
            fcntl.flock(lease, fcntl.LOCK_EX)
        audio, rate = synthesize(name, base / "models" / name, PASSAGES)
        for i, wave in enumerate(audio, 1):
            sf.write(base / "raw" / f"{name}-{i}.wav", wave, rate, subtype="FLOAT")
    (base / "raw" / f"{name}.json").write_text(json.dumps({
        "candidate": name, "revision": revision, "rate": rate, "seed": 437,
        "settings": SETTINGS[name],
        "seconds": round(time.monotonic() - started, 3), "passages": PASSAGES,
        "presenter_instruction": PRESENTER if name == "ryan" else None,
        "duration_seconds": [len(w) / rate for w in audio],
    }, indent=2))


if __name__ == "__main__":
    main()
