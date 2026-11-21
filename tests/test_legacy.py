import json
from pathlib import Path

import pytest

from video_renderer.api import translate_legacy
from video_renderer.media import encode

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def load(name):
    p = EXAMPLES / name
    d = json.loads((p / "story.json").read_text())
    d["signature"] = (p / "signature.md").read_text()
    return d


@pytest.mark.parametrize("name", ["unit-price", "signal-flow", "fruit-route", "smoke"])
def test_legacy_examples_convert(name):
    story = load(name)
    request = translate_legacy(story)
    assert request.visual["legacy_input"]
    assert [b.id for b in request.beats] == [p["id"] for p in story["panels"]]


def test_legacy_duration_and_references():
    story = load("unit-price")
    for invalid in (44999, 45000):
        with pytest.raises(ValueError):
            translate_legacy({**story, "end_ms": invalid})
    story["panels"][1]["refs"] = ["unknown"]
    with pytest.raises(ValueError, match="previous panel"):
        translate_legacy(story)


def test_real_near_45_second_mux(tmp_path):
    import wave
    from PIL import Image
    art = tmp_path / "test.png"
    Image.new("RGB", (360, 640), "ivory").save(art)
    audio = tmp_path / "test.wav"
    with wave.open(str(audio), "wb") as f:
        f.setparams((1,2,48000,0,"NONE","not compressed"))
        f.writeframes(bytes(96000))
    with pytest.raises(ValueError, match="45"):
        encode([art], [(0,1350,0)], (360,640), 30,1350,audio,tmp_path/"reject.mp4")
    meta = encode([art], [(0,1349,0)], (360,640),30,1349,audio,tmp_path/"pass.mp4")
    assert meta["expected_video_frames"] == 1349
    assert float(meta["ffprobe"]["format"]["duration"]) < 45


def test_failure_after_first_frame_keeps_partial_evidence(tmp_path, monkeypatch):
    import hashlib
    import httpx
    from video_renderer import api
    png = b"fixture bytes"
    calls = 0

    def server(r):
        nonlocal calls
        if r.url.path.endswith("/sessions"):
            return httpx.Response(201, json={"session_id": "s"})
        if r.url.path.endswith("/panels"):
            calls += 1
            if calls == 2:
                return httpx.Response(202, json={"state": "failed", "error": "Comfy disconnected"})
            return httpx.Response(202, json={"state": "accepted", "panel_id": "p", "status_url": "/p",
                "artifacts": {"composed.png": "/accepted.png"}, "summary": {"composed_sha256": hashlib.sha256(png).hexdigest()}})
        return httpx.Response(200, content=png)

    client = httpx.Client
    monkeypatch.setattr(api.httpx, "Client", lambda **kwargs: client(transport=httpx.MockTransport(server), **kwargs))
    p = tmp_path / "status.json"
    p.write_text("{}")
    with pytest.raises(RuntimeError, match="Comfy disconnected"):
        api.frames(tmp_path, translate_legacy(load("signal-flow")))
    assert (tmp_path / "frame-0.png").read_bytes() == png
    assert (tmp_path / "panels.partial.json").is_file()
    assert not (tmp_path / "video.mp4").exists()
