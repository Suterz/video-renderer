#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
video="$PWD"
frames="$HOME/git/frames-v4-insertion"
root="$HOME/Videos/storyboard-v4"
logs="$HOME/ai/storyboard-build/v4/logs"
py="$HOME/venvs/video-renderer/bin/python"
f="$(git -C "$frames" rev-parse HEAD)"
v="$(git rev-parse HEAD)"
if [[ "$(find "$root/r4-dev-results" -name outcome.json 2>/dev/null | wc -l)" -lt 50 ]]; then
    tmux wait-for v4-r4-development-terminal
fi
test -z "$(git status --porcelain)"
test -z "$(git -C "$frames" status --porcelain)"
test "$f" = "$(git -C "$frames" rev-parse HEAD)"
test "$v" = "$(git rev-parse HEAD)"
cfg="$root/frozen-r5.json"
if [[ -f "$cfg" ]]; then
  jq -e --arg f "$f" --arg v "$v" '.frames==$f and .video==$v' "$cfg" >/dev/null
else
  jq -n --arg f "$f" --arg v "$v" --arg c "$(git -C "$HOME/ai/ComfyUI" rev-parse HEAD)" \
       --arg j "$(sha256sum benchmark/v4_evaluate.py|cut -d' ' -f1)" \
       '{frames:$f,video:$v,comfy_commit:$c,evaluator_sha256:$j,models:"same local pinned models as R1"}' >"$cfg"
fi
tmux has-session -t v4-r5-frames 2>/dev/null || tmux new-session -d -s v4-r5-frames \
   "cd \"$frames\" && FRAME_PORT=8866 FRAME_STORE=\"$root/r5-dev/frames\" ./bin/start-frame-renderer >> \"$logs/r5-frames.log\" 2>&1"
tmux has-session -t v4-r5-video 2>/dev/null || tmux new-session -d -s v4-r5-video \
   "cd \"$video\" && VIDEO_PORT=8867 VIDEO_FRAME_URL=http://127.0.0.1:8866 VIDEO_STORE=\"$root/r5-dev/jobs\" ./bin/start-video-renderer >> \"$logs/r5-video.log\" 2>&1"
curl -fsS --retry 6 --retry-connrefused http://127.0.0.1:8867/ready >/dev/null
"$py" -B benchmark/v4_sweep.py --url http://127.0.0.1:8867 --frames "$frames" --video "$video" \
  --jobs "$root/r5-dev/jobs" --frame-store "$root/r5-dev/frames" --out "$root/r5-dev-results"
PYTHONPATH=src "$py" -B benchmark/v4_evaluate.py "$root/r5-dev-results"
test "$(find "$root/r5-dev-results" -name outcome.json | wc -l)" -eq 50
tmux wait-for -S v4-r5-development-terminal
