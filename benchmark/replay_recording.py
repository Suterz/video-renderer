"""Replay one captured recording through the upload API without retrying POST."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import httpx


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("request", type=Path)
    p.add_argument("recording", type=Path)
    p.add_argument("--url", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    packet = read(args.request)
    # The same prerecorded speech already contains the authored pauses.
    packet.pop("voice_profile", None)
    for line in packet["script"]:
        line.pop("pause_after_ms", None)
    wav = args.recording.read_bytes()
    receipt = args.out / "receipt.json"
    key = {"url": args.url, "wav_sha256": hashlib.sha256(wav).hexdigest(), "request": packet}
    ack = args.out / "ack.json"
    with httpx.Client(base_url=args.url, timeout=45) as client:
        if receipt.exists():
            if read(receipt) != key or not ack.exists():
                raise SystemExit("original POST acknowledgement is missing or the replay inputs changed")
            result = read(ack)
        else:
            with receipt.open("x") as f:
                json.dump(key, f, ensure_ascii=False)
            response = client.post("/v2/renders/upload", data={"request": json.dumps(packet)},
                                   files={"audio": ("captured.wav", wav, "audio/wav")})
            response.raise_for_status()
            result = response.json()
            save(ack, result)
        deadline = time.monotonic() + 1200
        while result["state"] in {"queued", "running"}:
            if time.monotonic() >= deadline:
                raise TimeoutError("render still active; resume from the existing acknowledgement")
            time.sleep(2)
            response = client.get(result["status_url"])
            response.raise_for_status()
            result = response.json()
        if result["state"] == "succeeded":
            video = client.get(result["video_url"])
            video.raise_for_status()
            (args.out / "video.mp4").write_bytes(video.content)
            manifest = client.get(result["status_url"] + "/manifest")
            manifest.raise_for_status()
            save(args.out / "manifest.json", manifest.json())
        save(args.out / "outcome.json", result)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
