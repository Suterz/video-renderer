"""Saved, reference-conditioned local Drama 3 through the ordinary speech worker path."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid
from urllib.request import Request, urlopen


def profile(label):
    registry_path = Path(os.environ.get("VIDEO_DRAMA3_REGISTRY",
                          Path(__file__).resolve().parents[2] / "voices/drama3/narrators.json"))
    registry = json.loads(registry_path.read_text())
    entry = registry["narrators"][label]
    source = registry_path.parent / entry["file"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
        raise ValueError(f"saved Drama 3 narrator {label} failed hash verification")
    return {"label": label, "reference": entry, "path": str(source),
            "artifacts": registry["artifact_sha256"], "runtime": registry["runtime"],
            "sampling": {"temperature": 1.0, "top_p": .9, "top_k": 0, "cache_gib": 8,
                         "split_long_text": True, "shorten_long_pauses": False}}


def checkpoint_profile(pin):
    """Only synthesis inputs bind a speech checkpoint; paths are locations."""
    return {key: value for key, value in pin.items() if key != "path"}


def request(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    with urlopen(Request(f"http://127.0.0.1:{int(os.getenv('VIDEO_DRAMA3_PORT', '8960'))}{path}",
                         data=data, headers=headers), timeout=25) as response:
        body = response.read()
        return json.loads(body) if body else None


def synthesize(label, wav, text, ffmpeg):
    pin = profile(label)
    reference = pin["reference"]
    output = Path(os.environ["VIDEO_DRAMA3_OUTPUT"]).resolve()
    lease = Path(os.environ.get("RENDER_GPU_LEASE", Path.home() / "ai/storyboard-build/v2/gpu.lock"))
    with lease.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        voices = output / "drama3_voices"
        voices.mkdir(parents=True, exist_ok=True)
        filename = f"storyboard-{label}-{reference['sha256'][:12]}.safetensors"
        shutil.copyfile(pin["path"], voices / filename)
        graph = {
            "1": {"class_type": "Drama3Loader", "inputs": {"model_name": "drama3_fp8experts_bf16.safetensors",
                  "experts": "in RAM", "expert_cache_gb": 8, "second_gpu": "none", "split_layer": 0, "pin_experts": False}},
            "2": {"class_type": "Drama3CodecLoader", "inputs": {"codec_name": "drama3_codec.safetensors"}},
            "3": {"class_type": "Drama3LoadVoice", "inputs": {"voice": filename}},
            "4": {"class_type": "Drama3Generate", "inputs": {"model": ["1", 0], "voices.voice0": ["3", 0],
                  "text": f'<|speaker:0|>[{reference["direction"]}] {text}', "seed": reference["seed"],
                  "temperature": 1.0, "top_p": .9, "top_k": 0, "max_frames": 0, "split_long_text": len(text.encode()) > 300,
                  "speakers": "one take per line", "voice_guidance": 0.0}},
            "5": {"class_type": "Drama3Decode", "inputs": {"codec": ["2", 0], "codes": ["4", 0], "shorten_long_pauses": False}},
            "6": {"class_type": "SaveAudio", "inputs": {"audio": ["5", 0], "filename_prefix": f"daily-tts/{uuid.uuid4().hex}"}},
        }
        wav.with_suffix(".graph.json").write_text(json.dumps(graph, indent=2))
        try:
            job = request("/prompt", {"prompt": graph})["prompt_id"]
            deadline = time.monotonic() + 660
            while time.monotonic() < deadline:
                history = request(f"/history/{job}").get(job)
                if history:
                    break
                time.sleep(2)
            else:
                raise TimeoutError("Drama 3 synthesis exceeded local deadline")
            wav.with_suffix(".history.json").write_text(json.dumps(history, indent=2))
            if "6" not in history.get("outputs", {}):
                detail = next((entry for kind, entry in history.get("status", {}).get("messages", [])
                               if kind == "execution_error"), {})
                message = " ".join(str(detail.get("exception_message", "")).split())
                stage = detail.get("node_type", "worker")
                raise RuntimeError(f"Drama 3 {stage} produced no audio" + (f": {message[:320]}" if message else ""))
            item = next(v[0] for v in history["outputs"]["6"].values() if isinstance(v, list))
            raw = (output / item["subfolder"] / item["filename"]).resolve()
            if not raw.is_relative_to(output):
                raise ValueError("invalid local speech result path")
            subprocess.run([ffmpeg, "-v", "error", "-xerror", "-y", "-i", str(raw),
                            "-c:a", "pcm_s24le", str(wav)], check=True, timeout=90)
        finally:
            request("/free", {"unload_models": True, "free_memory": True})
