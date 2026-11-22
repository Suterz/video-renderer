#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
video="$PWD"
frames="$HOME/git/frames-v4-counts"
root="$HOME/Videos/storyboard-v4"
logs="$HOME/ai/storyboard-build/v4/logs"
py="$HOME/venvs/video-renderer/bin/python"
f="$(git -C "$frames" rev-parse HEAD)"
v="$(git rev-parse HEAD)"
if [[ "$(find "$root/r2-dev-results" -name outcome.json 2>/dev/null | wc -l)" -lt 50 ]]; then
    tmux wait-for v4-r2-development-terminal
fi
test -z "$(git status --porcelain)"
test -z "$(git -C "$frames" status --porcelain)"
test "$f" = "$(git -C "$frames" rev-parse HEAD)"
test "$v" = "$(git rev-parse HEAD)"
pair="$root/frozen-r3.json"
if [[ -f "$pair" ]]; then
    jq -e --arg f "$f" --arg v "$v" '.frames==$f and .video==$v' "$pair" >/dev/null
else
    jq -n --arg f "$f" --arg v "$v" --arg c "$(git -C "$HOME/ai/ComfyUI" rev-parse HEAD)" \
       --arg j "$(sha256sum benchmark/v4_evaluate.py|cut -d' ' -f1)" \
       '{frames:$f,video:$v,comfy_commit:$c,evaluator_sha256:$j,models:"same installed offline models as R1"}' >"$pair"
fi
tmux has-session -t v4-r3-frames 2>/dev/null || tmux new-session -d -s v4-r3-frames \
    "cd \"$frames\" && FRAME_PORT=8852 FRAME_STORE=\"$root/r3-dev/frames\" ./bin/start-frame-renderer >> \"$logs/r3-frames.log\" 2>&1"
tmux has-session -t v4-r3-video 2>/dev/null || tmux new-session -d -s v4-r3-video \
    "cd \"$video\" && VIDEO_PORT=8853 VIDEO_FRAME_URL=http://127.0.0.1:8852 VIDEO_STORE=\"$root/r3-dev/jobs\" ./bin/start-video-renderer >> \"$logs/r3-video.log\" 2>&1"
curl -fsS --retry 6 --retry-connrefused http://127.0.0.1:8853/ready >/dev/null
"$py" -B benchmark/v4_sweep.py --url http://127.0.0.1:8853 --frames "$frames" --video "$video" \
    --jobs "$root/r3-dev/jobs" --frame-store "$root/r3-dev/frames" --out "$root/r3-dev-results"
PYTHONPATH=src "$py" -B benchmark/v4_evaluate.py "$root/r3-dev-results"
test "$(find "$root/r3-dev-results" -name outcome.json | wc -l)" -eq 50
tmux wait-for -S v4-r3-development-terminal
