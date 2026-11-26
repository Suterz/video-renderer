# Fresh renderer rehearsal

On Ubuntu 24.04, provision Python 3.12.3, `uv`, an `hf` CLI, `micromamba`,
Ubuntu's `libespeak-ng1` and DejaVu Sans Bold. Keep all downloads outside Git.
From the video repo, after installing the companion frame environment:

```sh
./bin/install-locked "$ROOT"
micromamba create --yes --prefix "$ROOT/media" --file locks/media-linux-64.txt
python3 -B bin/model-assets.py locks/models.json "$ROOT/speech/models" --download --hf "$HF_BIN"
python3 -B bin/model-assets.py locks/models.json "$ROOT/speech/models"
./bin/run-rehearsal "$ROOT" "$FRAMES_REPO"
curl -fsS http://127.0.0.1:8893/ready
```

The launcher binds ComfyUI 8193, frames 8892, video 8893 to loopback. It
uses only the rehearsal model tree and environments and shares the physical GPU
lease. Stop if one of those ports belongs to another setup. Readiness is a
dependency check; look under `rehearsal-results/` for actual results.

The supported selected setup is Qwen3-TTS CustomVoice Ryan in BF16/SDPA and
Kokoro af_heart on CPU. Chatterbox, Parler Laura, and Kitten Jasper remain
optional implementations covered by the original audition setup. This lock only
installs Ryan and Heart. The blind audition key is not needed.

JSON synthesis uses `/v2/renders`. WAV upload uses `/v2/renders/upload` with
multipart request/audio and the pauses already in the recording. An authored
utterance ID and phrase choose a beat; the forced aligner finds its real
sample/time boundary, and unprompted faster-whisper corroborates the cue
and critical speech. FFmpeg canonicalizes mono speech at 48 kHz. The video
service composes captions, encodes H.264/AAC, probes the mux and decodes it.
An encoded or muxed duration of 45 seconds or more is refused.

Keep audio evidence separate from art reuse. On voice changes
`reuse_visuals_from` verifies accepted frame hashes before copying them; cue
times are remeasured. On subtitle-only changes `reuse_recording_from` requires
the same voice and script and verifies the canonical WAV hash. Instructions
and the statuses and manifest endpoints are described by the staged OpenAPI.
