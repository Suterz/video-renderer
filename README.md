# video-renderer

Local English narration, speech-driven visual timing and checked H.264/AAC exports. Calls `frames-renderer` through HTTP. No image-model imports in this service.

```sh
./bin/start-video-renderer   # staged port 8789; VIDEO_FRAME_URL defaults to :8788
python3 examples/offers-v2.py ryan |
  curl -fsS -H 'Content-Type: application/json' --data-binary @- http://127.0.0.1:8789/v2/renders
curl -fsS http://127.0.0.1:8789/v2/renders/<job>/video -o lesson.mp4
```

`ryan`, `heart`, `chatter`, `laura`, `jasper` are separate local voice profiles. A second argument to the fixture is the prior visual job: the accepted PNG hashes stay unchanged. For subtitle-only revisions, also set `reuse_recording_from` to reuse the verified WAV and alignment. `POST /v2/renders/upload` accepts multipart `request` and `audio`. Original `/renders` continues as a migration route for supplied WAVs and authored milliseconds. Old jobs are read only.

For a legacy smoke example, set `VIDEO_URL` to the isolated service and run
`NARRATION_WAV=/path/to/smoke.wav ./bin/submit-example examples/smoke`.
The original audio is indexed under `Historical renderer examples/` in the
XPS gallery. The authored V2 example above synthesizes its own narration.

`bin/setup-audition` provisions isolated environments and pinned model snapshots outside Git. See its logs on failure; it needs Ubuntu user-space eSpeak support and the existing workstation tools. `bin/package-audition`, `bin/check-audition` and `bin/audition-reel` produce the blind pack, independent transcription, and the short reel. Voice naturalness and perceived sync are not machine-certified. Qwen forced alignment estimates timings; unprompted faster-whisper supplies a separate transcript, not ground truth.

Run `./bin/install-video-renderer` for the service environment. Use `GET /docs`
to inspect request fields. The server's default `VIDEO_STORE` is
`~/Videos/video-renderer/jobs`; existing `~/Videos/storyboard-renderer/jobs`
are read-only compatibility artifacts.

The local `bin/cutover-workstation` wrapper is an explicit port migration,
not part of installation. It checks both services, refuses while jobs are
queued/running and verifies the pinned v1 demo after routing `:8787` to v2.
Keep the `~/git/storyboard-renderer` detached v1 worktree for rollback.

For the pinned local installation and GPU rehearsal, see [Rehearsal](docs/REHEARSAL.md).
For the current status and next step, see [agent context](agent-context.md).
