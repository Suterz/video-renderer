#!/usr/bin/env bash
# Development only. Fresh holdouts require a separate, explicitly reviewed gate.
set -euo pipefail
cd "$(dirname "$0")/.."
video="$PWD"
frames="$HOME/git/frames-v4-parts"
root="$HOME/Videos/storyboard-v4"
logs="$HOME/ai/storyboard-build/v4/logs"
speech="$HOME/ai/storyboard-build/v2"
py="$HOME/venvs/video-renderer/bin/python"
test "$(git -C "$frames" rev-parse HEAD)" = "${1:?expected frame commit}"
test "$(git rev-parse HEAD)" = "${2:?expected video commit}"
if [[ "$(find "$root/r5-dev-results" -name outcome.json 2>/dev/null | wc -l)" -lt 50 ]] ||
   [[ ! -f "$root/r5-dev-results/INDEX.md" ]]; then
    tmux wait-for v4-r5-development-terminal
fi
test "$(git -C "$frames" rev-parse HEAD)" = "$1"
test "$(git rev-parse HEAD)" = "$2"
for tree in "$frames" "$video"; do test -z "$(git -C "$tree" status --porcelain)"; done

cfg="$root/frozen-r6.json"
# Recheck the same component configuration on resume; never overwrite a freeze.
make_config() {
  local vision_hash speech_hash
  vision_hash="$(sha256sum "$root/r1-base-components.json" | cut -d' ' -f1)"
  jq -r '.model_files | to_entries[] |
         select(.key | test("^(flux|qwen_vl|noto_|dejavu_)")) |
         "\(.value.sha256)  \(.value.path)"' "$root/r1-base-components.json" | sha256sum --check --status
  speech_hash="$(find -L "$speech/models" \( -name .git -o -name .cache \) -prune -o -type f -print0 |
      LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)"
  jq -n --arg f "$1" --arg v "$2" --arg c "$(git -C "$HOME/ai/ComfyUI" rev-parse HEAD)" \
     --arg j "$(sha256sum benchmark/v4_evaluate.py benchmark/v3/judge.py | sha256sum | cut -d' ' -f1)" \
     --arg vh "$vision_hash" --arg sh "$speech_hash" \
     '{frames:$f,video:$v,comfy_commit:$c,evaluator_bundle_sha256:$j,visual_component_record_sha256:$vh,
       speech_tree_sha256:$sh,controlled_parts:true,frame_port:8874,video_port:8875}'
}
candidate="$(make_config "$1" "$2")"
if [[ -f "$cfg" ]]; then
  test "$(<"$cfg")" = "$candidate"
else
  (set -o noclobber; printf '%s\n' "$candidate" >"$cfg")
fi
tmux has-session -t v4-r6-frames 2>/dev/null || tmux new-session -d -s v4-r6-frames \
   "cd \"$frames\" && FRAME_PORT=8874 FRAME_STORE=\"$root/r6-dev/frames\" ./bin/start-frame-renderer >> \"$logs/r6-frames.log\" 2>&1"
tmux has-session -t v4-r6-video 2>/dev/null || tmux new-session -d -s v4-r6-video \
   "cd \"$video\" && VIDEO_PORT=8875 VIDEO_FRAME_URL=http://127.0.0.1:8874 VIDEO_SPEECH_ROOT=\"$speech\" VIDEO_STORE=\"$root/r6-dev/jobs\" ./bin/start-video-renderer >> \"$logs/r6-video.log\" 2>&1"
curl -fsS --retry 6 --retry-connrefused http://127.0.0.1:8875/ready >/dev/null
"$py" -B benchmark/v4_sweep.py --controlled-parts --url http://127.0.0.1:8875 --frames "$frames" --video "$video" \
  --jobs "$root/r6-dev/jobs" --frame-store "$root/r6-dev/frames" --out "$root/r6-dev-results"
PYTHONPATH=src "$py" -B benchmark/v4_evaluate.py "$root/r6-dev-results"
test "$(find "$root/r6-dev-results" -name outcome.json | wc -l)" -eq 50
tmux wait-for -S v4-r6-development-terminal
