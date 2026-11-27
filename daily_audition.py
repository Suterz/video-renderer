"""Produce lossless original and level-matched review audio for local voice auditions."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


HOOK = ("One battery gives you back 75 kilowatt-hours. This one gives you just 48. "
        "Which one made better use of the energy you put in?")
EXPLANATION = ("You can’t tell from the energy returned alone. Look at what went in. The first battery took in "
               "100 kilowatt-hours and gave back 75. That’s three out of every four. The second took in 60 and "
               "returned 48. That’s four out of every five. Each battery ended with the same charge it started "
               "with. So the first battery gave you more energy back, but the second made better use of its input: "
               "80 percent returned, compared with 75 percent.")


def take(profile, model, text, target):
    import soundfile
    from video_renderer.voice_profiles import synthesize

    audio, rate = synthesize(profile, model, [text])
    soundfile.write(target, audio[0], rate, subtype="FLOAT")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=("heart", "ryan"))
    parser.add_argument("target", type=Path)
    parser.add_argument("--reuse-hook", type=Path, help="preserve a previously captured native hook during packaging repair")
    args = parser.parse_args()
    home = Path.home()
    lease = home / "ai/storyboard-build/v2/gpu.lock"
    model = home / "ai/storyboard-rehearsal/fresh/speech/models" / args.profile
    media = home / "ai/tools/media/bin"
    target = args.target
    target.mkdir(parents=True, exist_ok=False)
    from video_renderer.voice_profiles import SETTINGS

    receipt = {"profile": args.profile, "settings": SETTINGS[args.profile], "passes": {}}
    for name, text in (("hook", HOOK), ("explanation", EXPLANATION)):
        target.joinpath(f"{name}.txt").write_text(text, encoding="utf-8")
        raw = target / f"{name}-raw.wav"
        started = time.monotonic()
        with lease.open("a") as lock:
            if args.profile == "ryan":
                fcntl.flock(lock, fcntl.LOCK_EX)
            acquired = time.monotonic()
            if name == "hook" and args.reuse_hook:
                shutil.copyfile(args.reuse_hook, raw)
            else:
                take(args.profile, model, text, raw)
        seconds = time.monotonic() - acquired
        command = [str(media / "ffmpeg"), "-nostats", "-i", str(raw)]
        # Measure before applying constant gain. Never stretch or gate silence.
        stats = subprocess.run([*command, "-af", "loudnorm=I=-19:TP=-2:LRA=11:print_format=json",
                                "-f", "null", "-"], text=True, capture_output=True, check=True, timeout=60)
        measured, _ = json.JSONDecoder().raw_decode(stats.stderr[stats.stderr.rfind("{"):])
        gain = min(-19 - float(measured["input_i"]), -2 - float(measured["input_tp"]))
        playback = target / f"{name}-playback.wav"
        subprocess.run([*command, "-v", "error", "-af", f"volume={gain:.5f}dB", "-c:a", "pcm_s24le", str(playback)],
                       check=True, timeout=60)
        duration = subprocess.check_output([str(media / "ffprobe"), "-v", "error", "-show_entries", "format=duration",
                                            "-of", "default=noprint_wrappers=1:nokey=1", str(raw)], text=True)
        reused = name == "hook" and args.reuse_hook is not None
        receipt["passes"][name] = {"seconds": None if reused else seconds, "reused_native_take": reused,
                                  "lease_wait_seconds": acquired-started,
                                  "audio_seconds": float(duration), "loudness": measured, "gain_db": gain,
                                  "written_input_sha256": hashlib.sha256(text.encode()).hexdigest(),
                                  "native_audio_sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}
        target.joinpath("receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
