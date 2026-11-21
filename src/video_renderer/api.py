from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import wave
from contextlib import asynccontextmanager
from difflib import SequenceMatcher
from pathlib import Path
from typing import Annotated, Literal

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .media import FFMPEG, FFPROBE, encode
from .timeline import TimingReview, bind, corroborate_cue, cue_sample, end_frame, sample, speech_terms, start_frame, tokens

ROOT = Path(os.environ.get("VIDEO_STORE", Path.home() / "Videos/video-renderer/jobs"))
LEGACY = Path.home() / "Videos/storyboard-renderer/jobs"
SPEECH = Path(os.environ.get("VIDEO_SPEECH_ROOT", Path.home() / "ai/storyboard-build/v2"))
FRAMES = os.environ.get("VIDEO_FRAME_URL", "http://127.0.0.1:8788")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
tasks = queue.Queue()


class Review(RuntimeError):
    pass


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Phrase(Strict):
    utterance_id: str
    phrase: str
    edge: Literal["start", "end"] = "start"
    occurrence: int | None = Field(default=None, ge=1)
    offset_ms: int = 0


class Milliseconds(Strict):
    ms: int = Field(ge=0, lt=45000)


class Utterance(Strict):
    id: str
    text: str = Field(min_length=1)
    caption: str | None = None
    pause_after_ms: int = Field(default=0, ge=0, le=3000)
    critical_spoken: list[list[str]] = Field(default_factory=list)


class Beat(Strict):
    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
    cue: Phrase | Milliseconds
    panel: dict
    parent: str | None = None


class Video(Strict):
    title: str
    visual: dict
    script: list[Utterance] = Field(min_length=1, max_length=40)
    beats: list[Beat] = Field(min_length=1, max_length=40)
    voice_profile: Literal["ryan", "heart", "chatter", "laura", "jasper"] | None = None
    fps: Literal[24, 25, 30] = 30
    max_ms: int = Field(default=29999, ge=1000, lt=45000)
    closing_hold_ms: int = Field(default=900, ge=0, le=5000)
    subtitle_font_size: int = Field(default=46, ge=24, le=78)
    reuse_visuals_from: str | None = None
    reuse_recording_from: str | None = None

    @model_validator(mode="after")
    def valid(self):
        ids = [u.id for u in self.script]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate utterance ID")
        seen = set()
        for b in self.beats:
            if b.id in seen or (b.parent is not None and b.parent not in seen):
                raise ValueError("duplicate beat or unavailable parent")
            if isinstance(b.cue, Phrase) and b.cue.utterance_id not in ids:
                raise ValueError("unknown utterance ID")
            seen.add(b.id)
        if self.beats[0].cue != Milliseconds(ms=0):
            raise ValueError("the first beat starts at ms=0")
        return self


def read(path):
    return json.loads(path.read_text())


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)


def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def job_folder(id_, allow_legacy=False):
    if re.fullmatch("[0-9a-f]{32}", id_):
        for base in (ROOT, LEGACY) if allow_legacy else (ROOT,):
            p = base / id_
            if (p / "status.json").is_file():
                return p
    raise HTTPException(404, "unknown job")


def state(p, **changes):
    f = p / "status.json"
    save(f, {**read(f), **changes, "updated": time.time()})


def speech(mode, wav, text):
    env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
           "PATH": f"{SPEECH}/espeak/usr/bin:{os.environ['PATH']}",
           "PHONEMIZER_ESPEAK_LIBRARY": "/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1"}
    command = [str(Path.home() / f"venvs/v2-{mode}/bin/python"), str(Path(__file__).with_name("speech_worker.py")),
               mode, str(SPEECH), str(wav)]
    process = subprocess.run(command, input=json.dumps({"text": text}), text=True, capture_output=True, env=env, timeout=400)
    if process.returncode:
        raise RuntimeError(f"{mode} worker: {process.stderr[-3600:]}")
    return json.loads(process.stdout.splitlines()[-1])


def canonical(p, req):
    wav = p / "narration.wav"
    def convert(source, destination):
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(source), "-ac", "1", "-ar", "48000",
                        "-c:a", "pcm_s16le", str(destination)], check=True, timeout=100)
    if req.reuse_recording_from:
        original = job_folder(req.reuse_recording_from)
        old = Video.model_validate(read(original / "request.json"))
        spoken = lambda r: [(u.id, u.text, u.pause_after_ms) for u in r.script]
        previous = read(original / "manifest.json")
        if not req.voice_profile or req.voice_profile != old.voice_profile or spoken(req) != spoken(old):
            raise Review("recording reuse requires the same voice profile and spoken script")
        source = original / "narration.wav"
        if hash_bytes(source.read_bytes()) != previous["wav_sha256"]:
            raise RuntimeError("stored recording hash mismatch")
        shutil.copyfile(source, wav)
        shutil.copyfile(original / "audio-evidence.json", p / "audio-evidence.json")
    elif (p / "upload.wav").is_file():
        if any(u.pause_after_ms for u in req.script):
            raise Review("uploaded WAV must already contain intentional pauses")
        convert(p / "upload.wav", wav)
    else:
        chunks, group = [], []
        for u in req.script:
            group.append(u.text)
            if u.pause_after_ms or u is req.script[-1]:
                raw = p / f"raw-{len(chunks)}.wav"
                speech(req.voice_profile, raw, " ".join(group))
                chunk = raw.with_name(f"pcm-{len(chunks)}.wav")
                convert(raw, chunk)
                chunks.append((chunk, u.pause_after_ms))
                group = []
        with wave.open(str(wav), "wb") as out:
            out.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
            for chunk, pause in chunks:
                with wave.open(str(chunk), "rb") as inp:
                    out.writeframes(inp.readframes(inp.getnframes()))
                if pause:
                    out.writeframes(b"\0\0" * (48 * pause))
    with wave.open(str(wav), "rb") as f:
        return wav, f.getnframes()


def frames(p, req):
    spec = {"visual": req.visual, "panels": [(b.id, b.parent, b.panel) for b in req.beats]}
    fingerprint = hash_bytes(json.dumps(spec, sort_keys=True).encode())
    if req.reuse_visuals_from:
        old = job_folder(req.reuse_visuals_from)
        manifest = read(old / "panels.json")
        if manifest["fingerprint"] != fingerprint:
            raise Review("visual request changed; no reuse allowed")
        for entry in manifest["panels"]:
            source = old / entry["filename"]
            if hash_bytes(source.read_bytes()) != entry["sha256"]:
                raise RuntimeError("accepted frame cache hash mismatch")
            shutil.copyfile(source, p / entry["filename"])
        return {**manifest, "reused": True}
    result, by_key = [], {}
    with httpx.Client(base_url=FRAMES, timeout=30) as client:
        r = client.post("/v2/sessions", json=req.visual)
        if r.is_error:
            raise Review(f"frame session rejected: {r.text}")
        sid = r.json()["session_id"]
        for b in req.beats:
            state(p, phase=f"frame:{b.id}")
            payload = {**b.panel, "key": b.id, "parent_panel_id": by_key.get(b.parent)}
            r = client.post(f"/v2/sessions/{sid}/panels", json=payload)
            if r.is_error:
                raise Review(f"frame beat {b.id}: {r.text}")
            panel = r.json()
            deadline = time.monotonic() + 900
            while panel["state"] in ("queued", "running") and time.monotonic() < deadline:
                time.sleep(1)
                r = client.get(panel["status_url"])
                r.raise_for_status()
                panel = r.json()
            if panel["state"] == "needs_review":
                raise Review(f"frame beat {b.id}: {panel}")
            if panel["state"] != "accepted":
                raise RuntimeError(f"frame beat {b.id}: {panel}")
            r = client.get(panel["artifacts"]["composed.png"])
            r.raise_for_status()
            data = r.content
            digest = hash_bytes(data)
            if digest != panel["summary"]["composed_sha256"]:
                raise RuntimeError("frame artifact hash mismatch")
            name = f"frame-{len(result)}.png"
            (p / name).write_bytes(data)
            by_key[b.id] = panel["panel_id"]
            result.append({"id": b.id, "panel_id": panel["panel_id"], "sha256": digest,
                           "filename": name, "status_url": panel["status_url"]})
            save(p / "panels.partial.json", {"fingerprint": fingerprint, "session_id": sid, "panels": result})
    return {"fingerprint": fingerprint, "session_id": sid, "panels": result, "reused": False}


def caption(source, output, text, size):
    with Image.open(source) as f:
        image = f.convert("RGB")
    if text:
        draw = ImageDraw.Draw(image)
        w, h = image.size
        font = ImageFont.truetype(FONT, max(12, round(size * w / 1080)))
        lines = [""]
        for word in text.split():
            trial = (lines[-1] + " " + word).strip()
            if draw.textlength(trial, font=font) > w * .85 and lines[-1]:
                lines.append(word)
            else:
                lines[-1] = trial
        if len(lines) > 2 or max(draw.textlength(x, font=font) for x in lines) > w * .85:
            raise Review(f"caption exceeds safe region: {text!r}")
        line_height = round(size * w / 1080 * 1.27)
        bottom = round(h * .96)
        top = bottom - (len(lines) * line_height + round(h * .018))
        if top < h * .84:
            raise Review("subtitle would obscure instruction safe region")
        draw.rounded_rectangle((round(w * .055), top, round(w * .945), bottom), radius=14, fill="#302337")
        for i, line in enumerate(lines):
            draw.text((w // 2, top + round(h * .009) + i * line_height), line, anchor="mt", fill="#fff3db", font=font)
    image.save(output)


def run(p):
    req = Video.model_validate(read(p / "request.json"))
    legacy = read(p / "legacy.json") if (p / "legacy.json").is_file() else None
    started = time.monotonic()
    state(p, phase="speech")
    wav, n = canonical(p, req)
    total_samples = legacy["end_ms"] * 48 if legacy else n + req.closing_hold_ms * 48
    if n > total_samples:
        raise Review("uploaded audio runs past the authored video end")
    f = req.fps
    end = end_frame(total_samples, f)
    if end * 1000 > f * req.max_ms or end >= 45 * f:
        raise Review(f"speech plus closing hold exceeds budget: speech {n/48000:.3f}s, encoded {end/f:.3f}s, budget {req.max_ms/1000:.3f}s")
    script = [u.model_dump() for u in req.script]
    text = " ".join(u["text"] for u in script)
    if legacy:
        aligned, asr = [], []
        boundaries = [(c["ms"] * 48, c.get("caption") if c.get("caption") is not None else c.get("say", "")) for c in legacy["cues"]]
        bound = {}
    else:
        state(p, phase="alignment")
        if req.reuse_recording_from:
            evidence = read(p / "audio-evidence.json")
            aligned, asr = evidence["word_alignment"], evidence["independent_asr"]
        else:
            aligned = speech("align", wav, text)
            asr = speech("asr", wav, text)
            save(p / "audio-evidence.json", {"word_alignment": aligned, "independent_asr": asr, "wav_sha256": hash_bytes(wav.read_bytes())})
        if not aligned or any(not 0 <= a["start"] <= a["end"] <= n / 48000 + .05 for a in aligned):
            raise Review("aligner produced nonphysical word spans")
        bound = bind(script, aligned)
        observed = tokens(" ".join(w["word"] for w in asr))
        # ASR may write numeric phrases as digits. Preserve raw observations and
        # compare near each cue separately rather than treating them as ground truth.
        agreement = SequenceMatcher(None, speech_terms(tokens(text)), speech_terms(observed), autojunk=False).ratio()
        if agreement < .70:
            raise Review(f"independent ASR divergence ({agreement:.2f}): {' '.join(observed)}")
        boundaries = [(0, "")]
        for u in req.script:
            _, words = bound[u.id]
            if words and u.critical_spoken:
                nearby = tokens(" ".join(a["word"] for a in asr if
                    a["end"] >= words[0]["start"] - .30 and a["start"] <= words[-1]["end"] + .30))
                for alternatives in u.critical_spoken:
                    forms = [tokens(form) for form in alternatives]
                    if not any(form and any(nearby[i:i+len(form)] == form for i in range(len(nearby))) for form in forms):
                        raise Review(f"{u.id}: critical speech not corroborated: {alternatives!r}; heard {' '.join(nearby)!r}")
            if words and u.caption is not None:
                boundaries.append((sample(words[0]["start"]), u.caption))
    cues = [b.cue.model_dump(exclude_none=True) for b in req.beats]
    starts_samples = [cue_sample(c, bound) for c in cues]
    cue_evidence = [corroborate_cue(c, bound, asr) if "phrase" in c else {"method": "authored-ms"}
                    for c in cues]
    starts = [start_frame(i, f) for i in starts_samples]
    if starts != sorted(set(starts)) or starts[0] != 0 or starts[-1] >= end or min(starts_samples) < 0:
        raise Review(f"collapsed, reversed or out-of-range required cue: {starts_samples}")
    if not legacy and starts_samples[-1] > n:
        raise Review("cue fires after the spoken recording")
    manifest = frames(p, req)
    save(p / "panels.json", manifest)
    c = {start_frame(s, f): t for s, t in boundaries if 0 <= start_frame(s, f) < end}
    cuts = sorted({0, end, *starts, *c})
    paths, segments = [], []
    for j, (start, stop) in enumerate(zip(cuts, cuts[1:])):
        idx = max(i for i, s in enumerate(starts) if s <= start)
        subtitle = c[max((k for k in c if k <= start), default=0)] if c else ""
        out = p / f"segment-{j}.png"
        caption(p / manifest["panels"][idx]["filename"], out, subtitle, req.subtitle_font_size)
        paths.append(out)
        segments.append((start, stop, j))
    size = tuple(req.visual.get("canvas", (1080, 1920)))
    state(p, phase="encoding")
    candidate = p / "video.partial.mp4"
    verification = encode(paths, segments, size, f, end, wav, candidate)
    if verification["expected_video_frames"] != end:
        raise RuntimeError("encoder disagrees with exact timeline")
    save(p / "manifest.json", {**manifest, "wav_sha256": hash_bytes(wav.read_bytes()),
         "speech_samples": n, "voice_profile": req.voice_profile, "aligned": aligned, "asr": asr,
         "recording_reused": bool(req.reuse_recording_from),
         "beats": [{"id": b.id, "cue": b.cue.model_dump(), "sample": a, "frame": c, "validation": e}
                   for b, a, c, e in zip(req.beats, starts_samples, starts, cue_evidence)],
         "verification": verification, "seconds": time.monotonic() - started})
    candidate.replace(p / "video.mp4")


def work():
    while True:
        p = tasks.get()
        try:
            state(p, state="running")
            run(p)
            state(p, state="succeeded", phase="complete")
        except (Review, TimingReview) as exc:
            state(p, state="needs_review", error=str(exc))
        except Exception as exc:
            state(p, state="failed", error=f"{type(exc).__name__}: {exc}")
        finally:
            tasks.task_done()


@asynccontextmanager
async def lifespan(_):
    ROOT.mkdir(parents=True, exist_ok=True)
    for s in ROOT.glob("*/status.json"):
        if read(s)["state"] == "queued":
            tasks.put(s.parent)
        elif read(s)["state"] == "running":
            state(s.parent, state="interrupted", error="server restart")
    threading.Thread(target=work, daemon=True).start()
    yield


app = FastAPI(title="video-renderer", version="2.0", lifespan=lifespan)


def submit(req, audio=None, legacy=None):
    if bool(req.voice_profile) == bool(audio):
        raise HTTPException(422, "supply exactly one voice_profile or WAV")
    if audio and len(audio) > 20_000_000:
        raise HTTPException(413, "WAV exceeds 20 MB")
    p = ROOT / uuid.uuid4().hex
    p.mkdir()
    if audio:
        (p / "upload.wav").write_bytes(audio)
    if legacy:
        save(p / "legacy.json", legacy)
    save(p / "request.json", req.model_dump(mode="json"))
    d = {"id": p.name, "state": "queued", "status_url": f"/v2/renders/{p.name}",
         "video_url": f"/v2/renders/{p.name}/video"}
    save(p / "status.json", d)
    tasks.put(p)
    return d


@app.get("/health")
def health():
    return {"status": "alive"}


@app.get("/ready")
def ready():
    try:
        if not all(Path(x).is_file() for x in (FFMPEG, FFPROBE)):
            raise RuntimeError("missing media tools")
        httpx.get(FRAMES + "/ready", timeout=5).raise_for_status()
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"status": "ready"}


@app.post("/v2/renders", status_code=202)
def synth(req: Video):
    return submit(req)


@app.post("/v2/renders/upload", status_code=202)
def uploaded(request: str = Form(...), audio: UploadFile = File(...)):
    from io import BytesIO
    try:
        req = Video.model_validate_json(request)
        data = audio.file.read(20_000_001)
        if len(data) > 20_000_000:
            raise HTTPException(413, "WAV exceeds 20 MB")
        with wave.open(BytesIO(data), "rb") as stream:
            if not 0 < stream.getnframes() / stream.getframerate() < 45:
                raise ValueError("WAV duration must be positive and strictly less than 45 seconds")
    except (ValueError, wave.Error, EOFError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return submit(req, data)


def translate_legacy(story):
    end = story["end_ms"]
    fps = story["output"]["fps"]
    if type(end) is not int or not 0 < end < 45000 or end_frame(end * 48, fps) >= 45 * fps:
        raise ValueError("video must be strictly shorter than 45 seconds after rounding")
    cues = {c["id"]: c["ms"] for c in story["cues"]}
    cuts = [start_frame(c["ms"] * 48, fps) for c in story["cues"]]
    if not cuts or cuts[0] != 0 or cuts != sorted(set(cuts)) or len(cuts) != len(cues) or cuts[-1] >= end_frame(end * 48, fps):
        raise ValueError("invalid legacy cue sequence")
    visual = {"story_context": f"{story['premise']} {story.get('context', '')}", "visual_signature": story["signature"],
              "canvas": [story["output"]["width"], story["output"]["height"]], "legacy_input": True,
              "legacy_premise": story["premise"], "legacy_context": story.get("context", ""),
              **{k: story.get(k, d) for k, d in (("values", {}), ("checks", []), ("assets", {}))}}
    beats = []
    for panel in story["panels"]:
        refs = panel.get("refs", [])
        op = panel["op"]
        previous = beats[-1] if beats else None
        if op == "new_scene":
            if refs:
                raise ValueError("new scene cannot reference a panel")
        elif not previous or refs != [previous["id"]] or panel["scene"] != previous["panel"]["scene_id"]:
            raise ValueError("legacy continuation must refer to previous panel in its scene")
        beats.append({"id": panel["id"], "parent": refs[0] if refs else None, "cue": {"ms": cues[panel["cue"]]},
                      "panel": {"op": op, "scene_id": panel["scene"], "objective": story["premise"],
                                "instruction": panel["visual"], "clean_checks": panel.get("visual_checks", []),
                                **{k: panel[k] for k in ("change", "keep", "anchors", "overlays", "layout", "seed") if k in panel}}})
    return Video.model_validate({"title": story["title"], "visual": visual, "fps": fps, "max_ms": 44999,
                                 "script": [{"id": "legacy", "text": "Legacy authored cue timeline"}], "beats": beats})


@app.post("/renders", status_code=202)
def legacy_submit(story: str = Form(...), audio: UploadFile = File(...), reuse_from: str | None = Form(None)):
    from io import BytesIO
    data = audio.file.read(20_000_001)
    if len(data) > 20_000_000:
        raise HTTPException(413, "WAV exceeds 20 MB")
    try:
        legacy = json.loads(story)
        req = translate_legacy(legacy)
        with wave.open(BytesIO(data), "rb") as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 48000):
                raise ValueError("legacy WAV must be mono PCM16 at 48 kHz")
            if not 0 < wav.getnframes() <= legacy["end_ms"] * 48:
                raise ValueError("audio empty or runs past authored end")
        for check in req.visual["checks"]:
            vals = req.visual["values"]
            total, count, each = (vals[check[name]] for name in ("total_minor", "count", "each_minor"))
            if check["kind"] != "equal_groups" or not all(type(i) is int and i > 0 for i in (total, count, each)) or total != count * each:
                raise ValueError("invalid legacy arithmetic")
        if reuse_from:
            old = job_folder(reuse_from, allow_legacy=True)
            if (old / "panels.json").is_file():
                req.reuse_visuals_from = reuse_from
    except (ValueError, TypeError, KeyError, wave.Error, EOFError) as exc:
        raise HTTPException(422, str(exc)) from exc
    out = submit(req, data, legacy)
    return {**out, "status_url": f"/renders/{out['id']}", "video_url": f"/renders/{out['id']}/video"}


@app.get("/renders/{id_}")
@app.get("/v2/renders/{id_}")
def status(id_: str):
    return read(job_folder(id_, allow_legacy=True) / "status.json")


@app.get("/renders/{id_}/video")
@app.get("/v2/renders/{id_}/video")
def video(id_: str):
    p = job_folder(id_, allow_legacy=True)
    if read(p / "status.json")["state"] != "succeeded" or not (p / "video.mp4").is_file():
        raise HTTPException(409, read(p / "status.json"))
    return FileResponse(p / "video.mp4", media_type="video/mp4", filename=f"{id_}.mp4")


@app.get("/v2/renders/{id_}/manifest")
def manifest(id_: str):
    p = job_folder(id_)
    if not (p / "manifest.json").is_file():
        raise HTTPException(409, "manifest not complete")
    return read(p / "manifest.json")
