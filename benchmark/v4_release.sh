#!/usr/bin/env bash
# Pair is pinned before opening the sealed inputs. Existing scored directories
# are never purged to obtain a fresh result.
set -euo pipefail
cd "$(dirname "$0")/.."
video="$PWD"
frames="$HOME/git/frames-v4"
seal="$HOME/git/v4-holdout/benchmark/v4-sealed"
py="$HOME/venvs/video-renderer/bin/python"
root="$HOME/Videos/storyboard-v4"
logs="$HOME/ai/storyboard-build/v4/logs"
pair="$root/frozen-r1.json"
f="$(git -C "$frames" rev-parse HEAD)"
v="$(git -C "$video" rev-parse HEAD)"
s="$(git -C "$seal" rev-parse HEAD)"
for repo in "$frames" "$video" "$seal"; do test -z "$(git -C "$repo" status --porcelain)"; done
if [[ -f "$pair" ]]; then
    jq -e --arg f "$f" --arg v "$v" --arg s "$s" '.frames==$f and .video==$v and .seal==$s' "$pair" >/dev/null
else
    jq -n --arg f "$f" --arg v "$v" --arg s "$s" --arg evaluator "$(sha256sum benchmark/v4_evaluate.py | cut -d' ' -f1)" \
      --arg c "$(git -C "$HOME/ai/ComfyUI" rev-parse HEAD)" --arg story "FLUX.2 klein 4B BF16 / Qwen3-VL-8B / Qwen3-ForcedAligner 0.6B / faster-whisper-small.en / Ryan + Kokoro" \
      '{frames:$f,video:$v,seal:$s,evaluator_sha256:$evaluator,comfy_commit:$c,models:$story,offline:true}' > "$pair"
    cp "$HOME/git/frames-v3/docs/COMPONENTS.json" "$root/r1-base-components.json"
fi

start() {
    local tag="$1" fp="$2" vp="$3"
    mkdir -p "$root/$tag"
    tmux has-session -t "v4-$tag-frames" 2>/dev/null ||
        tmux new-session -d -s "v4-$tag-frames" "cd \"$frames\" && FRAME_PORT=$fp FRAME_STORE=\"$root/$tag/frames\" ./bin/start-frame-renderer >> \"$logs/$tag-frames.log\" 2>&1"
    tmux has-session -t "v4-$tag-video" 2>/dev/null ||
        tmux new-session -d -s "v4-$tag-video" "cd \"$video\" && VIDEO_PORT=$vp VIDEO_FRAME_URL=http://127.0.0.1:$fp VIDEO_STORE=\"$root/$tag/jobs\" ./bin/start-video-renderer >> \"$logs/$tag-video.log\" 2>&1"
    curl -fsS --retry 6 --retry-connrefused "http://127.0.0.1:$vp/ready" >/dev/null
}

sweep() {
    local tag="$1" vp="$2"
    shift 2
    "$py" -B benchmark/v4_sweep.py --url "http://127.0.0.1:$vp" --frames "$frames" --video "$video" \
        --jobs "$root/$tag/jobs" --frame-store "$root/$tag/frames" --out "$root/$tag-results" "$@"
    "$py" -B benchmark/v4_evaluate.py "$root/$tag-results"
}

start r1-dev 8834 8835
sweep r1-dev 8835
test "$(find "$root/r1-dev-results" -name outcome.json | wc -l)" -eq 50
tmux wait-for -S v4-r1-development-terminal
# Development service completion is not educational verification. Do not
# consume the untouched holdout subjects merely because 50 jobs terminated.
verified=$(find "$root/r1-dev-results" -name evaluation.json -exec jq -r '.judgment' '{}' \; | grep -c '^verified_pass$' || true)
if [[ "$verified" -ne 50 ]]; then
    printf 'Holdout seal remains closed: only %s/50 independent development passes.\n' "$verified"
    exit 0
fi
test "$(git -C "$frames" rev-parse HEAD)" = "$f"
test "$(git -C "$video" rev-parse HEAD)" = "$v"
start r1-holdout 8836 8837
sweep r1-holdout 8837 --sealed "$seal"
test "$(find "$root/r1-holdout-results" -name outcome.json | wc -l)" -eq 10
tmux wait-for -S v4-r1-terminal
