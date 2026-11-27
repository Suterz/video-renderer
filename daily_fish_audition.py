"""Submit the matching audition passages to a dedicated loopback Drama 3 worker."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from daily_audition import EXPLANATION, HOOK

NARRATORS = Path(__file__).resolve().parent / "voices" / "drama3"


def request(base, path, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    with urlopen(Request(base + path, data=payload, headers={"Content-Type": "application/json"}), timeout=30) as response:
        body = response.read()
        return json.loads(body) if body else None


def graph(name, text):
    return {
        "1": {"class_type": "Drama3Loader", "inputs": {
            "model_name": "drama3_fp8experts_bf16.safetensors", "experts": "in RAM",
            "expert_cache_gb": 8, "second_gpu": "none", "split_layer": 0, "pin_experts": False}},
        "2": {"class_type": "Drama3CodecLoader", "inputs": {"codec_name": "drama3_codec.safetensors"}},
        "3": {"class_type": "Drama3Generate", "inputs": {
            "model": ["1", 0], "text": text, "seed": 437, "temperature": 1.0, "top_p": .9,
            "top_k": 0, "max_frames": 0, "split_long_text": False,
            "speakers": "one take per line", "voice_guidance": 0.0}},
        "4": {"class_type": "Drama3Decode", "inputs": {
            "codec": ["2", 0], "codes": ["3", 0], "shorten_long_pauses": False}},
        "5": {"class_type": "SaveAudio", "inputs": {"audio": ["4", 0], "filename_prefix": name}},
    }


def narrator_graph(name, text, label, comfy_output):
    registry = json.loads((NARRATORS / "narrators.json").read_text())
    entry = registry["narrators"][label]
    saved = NARRATORS / entry["file"]
    data = saved.read_bytes()
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError(f"voice reference hash changed for {label}")
    voice_folder = comfy_output / "drama3_voices"
    voice_folder.mkdir(parents=True, exist_ok=True)
    installed = voice_folder / f"storyboard-{saved.name}"
    if not installed.exists():
        shutil.copyfile(saved, installed)
    if installed.read_bytes() != data:
        raise ValueError(f"worker already has different bytes for {installed.name}")
    config = graph(name, f'<|speaker:0|>[{entry["direction"]}] {text}')
    config["6"] = {"class_type": "Drama3LoadVoice", "inputs": {"voice": installed.name}}
    config["3"]["inputs"].update({"voices.voice0": ["6", 0], "seed": entry["seed"]})
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("comfy_output", type=Path)
    parser.add_argument("--port", type=int, default=8960)
    parser.add_argument("--narrator", choices=("A", "E", "F"), help="reuse a selected Drama 3 narrator")
    parser.add_argument("--passage", choices=("hook", "explanation", "both"), default="both")
    args = parser.parse_args()
    home = Path.home()
    base = f"http://127.0.0.1:{args.port}"
    target = args.output
    target.mkdir(parents=True, exist_ok=False)
    media = home / "ai/tools/media/bin"
    with (home / "ai/storyboard-build/v2/gpu.lock").open("a") as lease:
        fcntl.flock(lease, fcntl.LOCK_EX)
        try:
            for name, text in (("hook", HOOK), ("explanation", EXPLANATION)):
                if args.passage not in (name, "both"):
                    continue
                target.joinpath(f"{name}.txt").write_text(text)
                prefix = f"saved-{args.narrator}-{name}" if args.narrator else f"audition-{name}"
                workflow = (narrator_graph(prefix, text, args.narrator, args.comfy_output)
                            if args.narrator else graph(prefix, text))
                target.joinpath(f"{name}-workflow.json").write_text(json.dumps(workflow, indent=2))
                started = time.monotonic()
                try:
                    job = request(base, "/prompt", {"prompt": workflow})["prompt_id"]
                except HTTPError as error:
                    raise RuntimeError(error.read().decode(errors="replace")) from error
                while time.monotonic() - started < 900:
                    record = request(base, f"/history/{job}").get(job)
                    if record:
                        break
                    time.sleep(2)
                else:
                    raise TimeoutError(f"Drama 3 {name} still pending")
                target.joinpath(f"{name}-result.json").write_text(json.dumps(record, indent=2))
                saved = next(value[0] for value in record["outputs"]["5"].values() if isinstance(value, list))
                source = (args.comfy_output / saved["subfolder"] / saved["filename"]).resolve()
                if not source.is_relative_to(args.comfy_output.resolve()):
                    raise ValueError("worker output escaped the audition directory")
                output = target / f"{name}-raw.wav"
                subprocess.run([str(media / "ffmpeg"), "-v", "error", "-i", str(source),
                                "-c:a", "pcm_s24le", str(output)], check=True, timeout=120)
                print(name, "wall", time.monotonic() - started,
                      "sha256", hashlib.sha256(output.read_bytes()).hexdigest(), flush=True)
        finally:
            request(base, "/free", {"unload_models": True, "free_memory": True})


if __name__ == "__main__":
    main()
