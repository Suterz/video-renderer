# Fresh-install rehearsal — November 26, 2026

Host: `zelio-server`; Ubuntu 24.04.5 x86-64, Ryzen 7 7700, RTX 4090
(24564 MiB), NVIDIA driver 580.178.04, Python 3.12.3, FFmpeg 9.0.2.
The rehearsal cloned ComfyUI and fetched model snapshots into a new external
tree, installed new Python and media environments, and used empty job stores.
It still relied on the host's NVIDIA driver, Ubuntu fonts and eSpeak shared
library, and an existing `uv`, `hf`, and `micromamba` bootstrap. This was a
fresh user-space install on the same workstation, not a second-machine run.

| Component | Commit or SHA-256 from the running pair |
|---|---|
| frames-renderer | `7c37de68b90705fdf4c242802bd64cdef86761ce` |
| video-renderer | `6bf07566054096b6d46f55890b54e82317b898e2` |
| ComfyUI | `a277b5bf213e8a44fa34817b7770b54f86ef4cea` |
| Frame OpenAPI (advertises 2.0) | `0521c1fe14aff531335b3f65cd72044a9c00d79ff1a8b24bc11f0a0846adaa23` |
| Video OpenAPI (advertises 2.0) | `16ecda8a01a19382253cf84d2aeb2a2070eab725fe097f4aeaa5153a83a93d5c` |

- Original: 11.0-second MP4 with a red mug that changes to green while its shape
  and location persist. Frame 141 still shows red and the question; frame 142
  shows green. The exact label appears at frame 233. The accepted edit records
  a real Comfy reference upload and the opening clean image SHA-256 as its parent.
- Second voice: the three panel hashes match; audio hash differs; cuts are
  `[0,190,274]` instead of `[0,142,233]`.
- Caption revision: same panels, WAV, and cue frames. Uploading the original WAV
  from the first run with its baked pause also exports.
- Negative upload: replacing the authored opening with “Here is a blue truck”
  while keeping the red-mug audio is withheld for critical speech mismatch.

Workstation artifacts: `~/ai/storyboard-rehearsal/fresh/rehearsal-results/`.
The XPS gallery contains the decoded phone sequence. Production and rollback
were not used by this rehearsal.

## Speech diagnosis

The old environment failed new recognition of the saved circuit and short
rectangle recordings and of a previously accepted circuit WAV. The failures
persisted at one thread with INT8 and five threads with FP32. The isolated
reference environment transcribed the exact saved files using the same model
snapshot. The working lock includes `faster-whisper==1.2.1`,
`ctranslate2==4.6.0`, `av==16.0.1`, `tokenizers==0.22.2`, and `numpy==2.2.6`.
This isolates a compatibility problem to the recognition stack, not a single
package. The agreement and critical-speech thresholds are unchanged.
