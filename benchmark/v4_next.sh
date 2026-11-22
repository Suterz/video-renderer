#!/usr/bin/env bash
# Optional resume: v4_next.sh r4, with same frozen worktrees. Never merges scores.
set -euo pipefail
cd "$(dirname "$0")/.."
root="$HOME/Videos/storyboard-v4"
logs="$HOME/ai/storyboard-build/v4/logs"
frames="$HOME/git/frames-v4-insertion"
video="$PWD"
seal="$HOME/git/v4-holdout/benchmark/v4-sealed"
py="$HOME/venvs/video-renderer/bin/python"
f="$(git -C "$frames" rev-parse HEAD)"
v="$(git rev-parse HEAD)"
s="$(git -C "$seal" rev-parse HEAD)"
if [[ "$(find "$root/r3-dev-results" -name outcome.json 2>/dev/null |wc -l)" -lt 50 ]]; then
    tmux wait-for v4-r3-development-terminal
fi
test "$f" = "$(git -C "$frames" rev-parse HEAD)"
test "$v" = "$(git rev-parse HEAD)"
for tree in "$frames" "$video" "$seal"; do test -z "$(git -C "$tree" status --porcelain)"; done
pair="$root/frozen-r4.json"
if [[ -f "$pair" ]]; then
  jq -e --arg f "$f" --arg v "$v" --arg s "$s" '.frames==$f and .video==$v and .seal==$s' "$pair" >/dev/null
else
  jq -n --arg f "$f" --arg v "$v" --arg s "$s" --arg c "$(git -C "$HOME/ai/ComfyUI" rev-parse HEAD)" \
       --arg j "$(sha256sum benchmark/v4_evaluate.py|cut -d' ' -f1)" \
       '{frames:$f,video:$v,seal:$s,comfy_commit:$c,evaluator_sha256:$j,models:"same local pinned models as R1"}' >"$pair"
fi
start() {
    local tag="$1" fp="$2" vp="$3"
    tmux has-session -t "v4-$tag-frames" 2>/dev/null || tmux new-session -d -s "v4-$tag-frames" \
       "cd \"$frames\" && FRAME_PORT=$fp FRAME_STORE=\"$root/$tag/frames\" ./bin/start-frame-renderer >> \"$logs/$tag-frames.log\" 2>&1"
    tmux has-session -t "v4-$tag-video" 2>/dev/null || tmux new-session -d -s "v4-$tag-video" \
       "cd \"$video\" && VIDEO_PORT=$vp VIDEO_FRAME_URL=http://127.0.0.1:$fp VIDEO_STORE=\"$root/$tag/jobs\" ./bin/start-video-renderer >> \"$logs/$tag-video.log\" 2>&1"
    curl -fsS --retry 6 --retry-connrefused "http://127.0.0.1:$vp/ready" >/dev/null
}
sweep() {
    local tag="$1" vp="$2"
    shift 2
    "$py" -B benchmark/v4_sweep.py --url "http://127.0.0.1:$vp" --frames "$frames" --video "$video" \
      --jobs "$root/$tag/jobs" --frame-store "$root/$tag/frames" --out "$root/$tag-results" "$@"
    PYTHONPATH=src "$py" -B benchmark/v4_evaluate.py "$root/$tag-results"
}
start r4-dev 8860 8861
sweep r4-dev 8861
test "$(find "$root/r4-dev-results" -name outcome.json |wc -l)" -eq 50
tmux wait-for -S v4-r4-development-terminal
verified=$(find "$root/r4-dev-results" -name evaluation.json -exec jq -r '.judgment' '{}' \; | grep -c '^verified_pass$' || true)
if [[ "$verified" != 50 ]]; then
    printf 'Fresh holdout remains sealed: %s/50 independently verified.\n' "$verified"
    exit 0
fi
test "$s" = "$(git -C "$seal" rev-parse HEAD)"
test ! -d "$root/r1-holdout-results"
start r4-holdout 8862 8863
sweep r4-holdout 8863 --sealed "$seal"
tmux wait-for -S v4-r4-holdout-terminal
