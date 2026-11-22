#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
video="$PWD"
frames="$HOME/git/frames-v4-repair"
root="$HOME/Videos/storyboard-v4"
log="$HOME/ai/storyboard-build/v4/logs"
env="$HOME/venvs/video-renderer/bin/python"
f="$(git -C "$frames" rev-parse HEAD)"
v="$(git rev-parse HEAD)"
if [[ "$(find "$root/r1-dev-results" -name outcome.json |wc -l)" -lt 50 ]]; then
    tmux wait-for v4-r1-development-terminal
fi
test -z "$(git -C "$frames" status --porcelain)"
test -z "$(git status --porcelain)"
pair="$root/frozen-r2.json"
if [[ -f "$pair" ]]; then
  jq -e --arg f "$f" --arg v "$v" '.frames==$f and .video==$v' "$pair" >/dev/null
else
  jq -n --arg f "$f" --arg v "$v" --arg c "$(git -C "$HOME/ai/ComfyUI" rev-parse HEAD)" \
     --arg evaluator "$(sha256sum benchmark/v4_evaluate.py|cut -d' ' -f1)" \
     --arg models "Same pinned local model inventory as frozen R1, offline" \
     '{frames:$f,video:$v,comfy_commit:$c,evaluator_sha256:$evaluator,models:$models}' > "$pair"
fi
tmux has-session -t v4-r2-frames 2>/dev/null || tmux new-session -d -s v4-r2-frames \
   "cd \"$frames\" && FRAME_PORT=8850 FRAME_STORE=\"$root/r2-dev/frames\" ./bin/start-frame-renderer >> \"$log/r2-frames.log\" 2>&1"
tmux has-session -t v4-r2-video 2>/dev/null || tmux new-session -d -s v4-r2-video \
   "cd \"$video\" && VIDEO_PORT=8851 VIDEO_FRAME_URL=http://127.0.0.1:8850 VIDEO_STORE=\"$root/r2-dev/jobs\" ./bin/start-video-renderer >> \"$log/r2-video.log\" 2>&1"
curl -fsS --retry 8 --retry-connrefused http://127.0.0.1:8851/ready >/dev/null
"$env" -B benchmark/v4_sweep.py --url http://127.0.0.1:8851 --frames "$frames" --video "$video" \
  --jobs "$root/r2-dev/jobs" --frame-store "$root/r2-dev/frames" --out "$root/r2-dev-results"
"$env" -B benchmark/v4_evaluate.py "$root/r2-dev-results"
test "$(find "$root/r2-dev-results" -name outcome.json | wc -l)" -eq 50
tmux wait-for -S v4-r2-development-terminal
