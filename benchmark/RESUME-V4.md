# V4 staged experiment: run and resume

V2 production and V1 rollback are not cut over. Score only first outcomes
under the run's own immutable frame/video/evaluator pair. Outcomes from the
different development rounds do not belong in the same denominator.

* Workstation artifacts: `~/Videos/storyboard-v4/`.
* R1 pair: `frames-v4` `0b539fc332c22bed2fcab29d204f92f80fb2771f` and
  `video-v4` `6da9c60a3338117aee9032207df866b0ae0c4d4d`.
  Ports 8834/8835, tmux `v4-round1`, from `~/git/video-v4`:
  `bash benchmark/v4_release.sh` only if the original coordinator is not running.
* R2: `frames-v4-repair` `eaa3cf0` plus `video-v4-repair` `bd8f7ef`,
  queued in `v4-round2`, port pair 8850/8851. Waits for R1 renders before
  using separate stores. Do not move the branch heads under that coordinator.
* Fresh seal `6f81401960c11c54ca729c872bf8aa0cb98dc2f8`.
  Never consume it during a development round. The R1 runner opens it
  only after independently verifying all 50 development outputs.
* Run `python -B benchmark/v4_evaluate.py ~/Videos/storyboard-v4/<run>-results`
  with `~/venvs/video-renderer/bin/python` for a benchmark index. A pending
  or unjudged render never passes. `inspection.json` contains independent
  visibility, association, disclosure, mechanism, phone-size, and speech
  evidence for adjudicated cases.

## No duplicate scored POST on resumption

`v4_sweep.py` durably writes the idempotency receipt before POST. The server
derives a stable job ID and rejects a body conflict under the same key.
If a client loses the POST acknowledgement, the resumed harness only uses
`GET /v2/submissions/{key}` to recover the terminal job. No second POST is made.
Record thrown transport failures as unknown/operational instead of silently
trying another seed or starting another job. Server-side idempotency also has
a test for conflict and queue length after repeated identical requests.

## Transfer evidence and known unresolved class

Controlled wrong-part, early-fact, and count failures have same-art bounded
repair controls. The wrong-part repair also produced a complete public-API
MP4. For a detected but incorrect/ambiguous generated endpoint the later
branch chooses at most one targeted re-grounding, then refuses if full and
phone/crop observations still do not support the claim. This remains a known
problem for an apparently valid basket opening.

Post-freeze local experiments are not benchmark wins: frame count and
typography safety `5668744`, and numeric cue spellings `6a4c604`. Four old
speech-alignment refusals reached video production after punctuation,
hyphen/clock-token and bounded ASR span fixes. The inserted pause shifted two
map cuts by 22 and 24 frames while preserving selected frame hashes; machine
precision is not a listening test.
