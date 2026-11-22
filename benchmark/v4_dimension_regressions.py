"""Exercise a recovered dimension cue through the API, outside frozen rounds."""
import argparse
import json
from pathlib import Path

import httpx

from v4_controls import send


def main():
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("root", type=Path)
    p.add_argument("out", type=Path)
    a = p.parse_args()

    photo = json.loads((a.root / "r5-dev-results/D04/request.json").read_text())
    floor = json.loads((a.root / "r4-dev-results/D13/request.json").read_text())
    floor["script"][2]["text"] = "A three by four rectangle has a boundary and an inside."
    floor["beats"][1]["cue"] = {"utterance_id": floor["script"][2]["id"],
                               "phrase": "A three by four rectangle"}

    with httpx.Client(base_url=a.url, timeout=30) as client:
        for name, request in (("photo-original", photo), ("floor-transfer", floor)):
            folder = a.out / name
            status = send(client, "/v2/renders", request, folder)
            (folder / "status.json").write_text(json.dumps(status, indent=2) + "\n")
            if status["state"] == "succeeded":
                video = client.get(status["video_url"])
                video.raise_for_status()
                (folder / "video.mp4").write_bytes(video.content)
                manifest = client.get(status["status_url"] + "/manifest")
                manifest.raise_for_status()
                (folder / "manifest.json").write_bytes(manifest.content)
            print(name, status["state"], status.get("error"), flush=True)


if __name__ == "__main__":
    main()
