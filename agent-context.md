# Video renderer

## Current baseline

- English narration, independent speech corroboration, phrase-to-frame timing, checked H.264/AAC export, and durable one-submit recovery. Production remains `deployed/v2`.
- The isolated rehearsal verified clean reference, exact cue cuts, same-art new voice, subtitle-only reuse, uploaded WAV, and wrong-transcript refusal.
- MP4 export does not prove learning quality. R6 prepared stories verified 48/50 with two incorrect returns; most gains over R5 were on rewritten requests.
- Resume from the `story-generator/agent-context.md` integration handoff. Keep renderer and authored-story comparisons separate, and preserve the first outcome on any scored request.

## Decisions, newest first

- **Contraction timing (staged):** author script `you’ll` previously failed forced binding at `youll`; independent ASR heard “you’ll”. `1d0664d` accepts only unambiguous single-word apostrophe drops, preserving the exact aligned span, and rejects `well` for “we’ll”. Same 829,200 PCM samples now reach frame review; separate “They’ll put” stacking control verifies frame 46. This is timing evidence, not a writer-quality or deployment change. Gallery: `v4/v4.7 - Communication storyteller/REVIEW.md`.

- **Consolidation:** take the reproducible runtime line once; keep adjudications on evidence refs and the gallery. The public CLI accepts an explicit archived legacy WAV while the rollback smoke retains its original fixture. Gallery: `Historical renderer examples/INDEX.md`.
- **Rehearsed install and ASR:** pinned the working environment and recovered the exact saved circuit/rectangle WAVs. Later tests also passed with old versions; the earlier speech fault was intermittent, not isolated to a package. `tested/fresh-install-2026-11-26`; gallery `v4/v4.5 - Saved rounds and rehearsal/REVIEW.md`.
- **V4 prepared-story checks:** matched encoded clue regions against unobscured art and refused literal early answers. The circuit/trail controls reject visibly broken paths; the R6 return-fare error shows a literal speech check cannot prevent all early visual disclosures.
- **Cue normalization:** accept real hyphen/number/dimension spelling variants without changing values or inventing a timing edge inside a fused word. The stiff-photo `8×10` failure and different-dimension negative distinguish this from relaxation (`f91d456`).
- **Receipts and scoring:** claim the idempotency key once, recover by GET, and keep first outcomes separately from independent judgments. Treat a lost receipt as unresolved, never permission to resubmit. The V3 holdout was consumed; the V4 holdout stays private.
- **V2 split:** Qwen CustomVoice Ryan and CPU Heart have rehearsal evidence; other voice profiles are optional. Uploaded speech, independent ASR, and same-art repeat renders established timing reuse, with legacy clients and frozen V1 rollback separate from current deployment.
