#!/usr/bin/env bash
# Start after reviewed pilot fixes. Sealed holdout starts only after 50 D outcomes.
set -euo pipefail
cd "$(dirname "$0")/../.."
video="$PWD"
frames="$HOME/git/frames-v3"
seal="$HOME/git/v3-holdout"
logs="$HOME/ai/storyboard-build/v3/logs"
store="$HOME/Videos/storyboard-v3"
py="$HOME/venvs/video-renderer/bin/python"
pair_file="$store/frozen-release.json"
mkdir -p "$logs" "$store"
f_sha="$(git -C "$frames" rev-parse HEAD)"
v_sha="$(git -C "$video" rev-parse HEAD)"
h_sha="$(git -C "$seal" rev-parse HEAD)"
test -z "$(git -C "$frames" status --porcelain)"
test -z "$(git -C "$video" status --porcelain)"
test -z "$(git -C "$seal" status --porcelain)"
if [[ -e "$pair_file" ]]; then
  jq -e --arg f "$f_sha" --arg v "$v_sha" --arg h "$h_sha" '.frames==$f and .video==$v and .holdout==$h' "$pair_file" >/dev/null
else
  jq -n --arg f "$f_sha" --arg v "$v_sha" --arg h "$h_sha" \
    --arg when "$(date -Is)" '--arg' backend 'ComfyUI :8188 v0.46.0 / FLUX.2 Klein 4B BF16, Qwen3-VL 8B' \
    '{frames:$f,video:$v,holdout:$h,frozen_at:$when,backend:$backend,voice_profiles:["ryan","heart"],preserve_reviewer_thresholds:true}' > "$pair_file"
fi

start_pair() {
  local tag="$1" fp="$2" vp="$3"
  tmux has-session -t "v3-$tag-frames" 2>/dev/null ||
    tmux new-session -d -s "v3-$tag-frames" "cd \"$frames\" && FRAME_PORT=$fp FRAME_STORE=\"$store/$tag/frames\" ./bin/start-frame-renderer >> \"$logs/$tag-frames.log\" 2>&1"
  tmux has-session -t "v3-$tag-video" 2>/dev/null ||
    tmux new-session -d -s "v3-$tag-video" "cd \"$video\" && VIDEO_PORT=$vp VIDEO_FRAME_URL=http://127.0.0.1:$fp VIDEO_STORE=\"$store/$tag/jobs\" ./bin/start-video-renderer >> \"$logs/$tag-video.log\" 2>&1"
  curl -fsS --retry 8 --retry-connrefused "http://127.0.0.1:$vp/ready" >/dev/null
}

run_one() {
  local tag="$1" vp="$2"
  shift 2
  "$py" -B benchmark/v3/run.py --mode v3 --url "http://127.0.0.1:$vp" --frames "$frames" --video "$video" \
    --jobs "$store/$tag/jobs" --frames-store "$store/$tag/frames" --root "$store/$tag-results" "$@"
  "$py" -B benchmark/v3/judge.py "$store/$tag-results"
}

start_pair rc-dev 8814 8815
run_one rc-dev 8815
[[ $(find "$store/rc-dev-results" -mindepth 2 -maxdepth 2 -name outcome.json | wc -l) -eq 50 ]]
[[ "$(git -C "$frames" rev-parse HEAD)" == "$f_sha" && "$(git -C "$video" rev-parse HEAD)" == "$v_sha" ]]
start_pair rc-holdout 8816 8817
run_one rc-holdout 8817 --frozen "$seal/benchmark/v3/frozen"
[[ $(find "$store/rc-holdout-results" -mindepth 2 -maxdepth 2 -name outcome.json | wc -l) -eq 10 ]]
echo "Terminal service outcomes: 50 development, 10 holdout. Consult independent evaluations; unjudged is not pass."
