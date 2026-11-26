"""Exercise actual speech, clean reference editing, and MP4 reuse in staging."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

import httpx


def story():
    setup = {"op": "new_scene", "scene_id": "cup", "objective": "A red cup can be identified by its color.",
             "instruction": "One large red mug with a right-hand loop handle against flat ivory. No other objects.",
             "clean_checks": [{"question": "What color is the mug? Answer with one color word.", "expected": "red"}],
             "seed": 42, "retry_budget": 1}
    edit = {**setup, "op": "edit_scene", "objective": "Only the same mug color changes.",
            "instruction": "The same mug is now green.",
            "change": "Change the body and handle color from red to green.",
            "keep": "Same mug outline, handle, position, size, viewpoint, and flat ivory background.",
            "action_claim": "The red mug changes to green while its position and shape stay the same.",
            "clean_checks": [{"question": "What color is the mug? Answer with one color word.", "expected": "green"}]}
    label = {"type": "text", "text": "COLOR CHANGED", "at": [.5,.72], "role": "value"}
    overlay = {"op": "overlay_only", "scene_id": "cup", "objective": "Name the observed change.",
               "instruction": "Add the exact label below the unchanged green mug.", "overlays": [label]}
    return {"title": "What changed?", "voice_profile": "heart", "max_ms": 29000,
            "visual": {"story_context": "Only an item's color changes, not its identity.",
                       "visual_signature": "Simple editorial cartoon, thick plum outlines, flat ivory field.", "graphic_theme": "paper"},
            "script": [{"id": "intro", "text": "Here is a red mug."},
                       {"id": "question", "text": "What will change?", "caption": "What will change?", "pause_after_ms": 1750},
                       {"id": "change", "text": "Watch the color change. The mug turns green.", "caption": ""},
                       {"id": "result", "text": "The shape and position stay the same."}],
            "beats": [{"id": "opening", "cue": {"ms": 0}, "panel": setup},
                      {"id": "edit", "parent": "opening", "cue": {"utterance_id": "change", "phrase": "Watch the color"}, "panel": edit},
                      {"id": "label", "parent": "edit", "cue": {"utterance_id": "result", "phrase": "The shape and"}, "panel": overlay}]}


def save(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n")
    temp.replace(path)


def run(client, root, name, payload, audio=None):
    folder = root / name
    folder.mkdir(exist_ok=True)
    if (folder / "status.json").exists():
        return json.loads((folder / "status.json").read_text())
    receipt = folder / "receipt.json"
    key = "rehearsal-" + hashlib.sha256(str(folder.resolve()).encode()).hexdigest()
    if receipt.exists():
        result = client.get(f"/v2/submissions/{key}")
    else:
        save(folder / "request.json", payload)
        save(receipt, {"key": key})
        if audio is None:
            result = client.post("/v2/renders", json=payload, headers={"Idempotency-Key": key})
        else:
            result = client.post("/v2/renders/upload",
                                 data={"request": json.dumps(payload)},
                                 files={"audio": ("narration.wav", audio, "audio/wav")})
            result.raise_for_status()
            save(receipt, {"key": key, "uploaded_job": result.json()["status_url"]})
    if audio is not None and receipt.exists():
        known = json.loads(receipt.read_text()).get("uploaded_job")
        if known:
            result = client.get(known)
    result.raise_for_status()
    status = result.json()
    deadline = time.monotonic() + 1200
    while status["state"] in {"queued", "running"}:
        if time.monotonic() >= deadline:
            raise TimeoutError(status)
        time.sleep(2)
        current = client.get(status["status_url"])
        current.raise_for_status()
        status = current.json()
    if status["state"] == "succeeded":
        manifest = client.get(status["status_url"] + "/manifest")
        manifest.raise_for_status()
        save(folder / "manifest.json", manifest.json())
        video = client.get(status["video_url"])
        video.raise_for_status()
        (folder / "video.mp4").write_bytes(video.content)
    save(folder / "status.json", status)
    print(name, status["state"], status.get("error", ""), flush=True)
    return status


def main():
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("root", type=Path)
    p.add_argument("--jobs", type=Path, required=True)
    a = p.parse_args()
    a.root.mkdir(parents=True, exist_ok=True)
    req = story()
    with httpx.Client(base_url=a.url, timeout=45) as client:
        start = run(client, a.root, "original", req)
        if start["state"] != "succeeded":
            return
        other = {**req, "voice_profile": "ryan", "reuse_visuals_from": start["id"]}
        voice = run(client, a.root, "new-voice", other)
        caption = deepcopy(req)
        caption.update(reuse_visuals_from=start["id"], reuse_recording_from=start["id"])
        caption["script"][1]["caption"] = "Which property changes?"
        text = run(client, a.root, "new-caption", caption)
        uploaded = deepcopy(req)
        uploaded.pop("voice_profile")
        uploaded["reuse_visuals_from"] = start["id"]
        uploaded["script"][1].pop("pause_after_ms")
        wave = (a.jobs / start["id"] / "narration.wav").read_bytes()
        audio = run(client, a.root, "uploaded", uploaded, audio=wave)
        bad = deepcopy(uploaded)
        bad["script"][0].update(text="Here is a blue truck.", critical_spoken=[["blue truck"]])
        negative = run(client, a.root, "wrong-transcript", bad, audio=wave)
        assert [x["state"] for x in (voice, text, audio, negative)] == [
            "succeeded", "succeeded", "succeeded", "needs_review"]
        load = lambda name: json.loads((a.root / name / "manifest.json").read_text())
        m, n, t = map(load, ("original", "new-voice", "new-caption"))
        hashes = lambda data: [x["sha256"] for x in data["panels"]]
        assert hashes(m) == hashes(n) == hashes(t)
        assert m["wav_sha256"] != n["wav_sha256"] and m["wav_sha256"] == t["wav_sha256"]
        assert m["beats"] == t["beats"] and [x["frame"] for x in m["beats"]] != [x["frame"] for x in n["beats"]]
        save(a.root / "reuse-proof.json", {"hashes": hashes(m), "cuts": [m["beats"], n["beats"], t["beats"]]})


if __name__ == "__main__":
    main()
