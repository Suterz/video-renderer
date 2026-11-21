# V3 live evaluation handoff

Original baseline: frame `ffc6013c517ce3c1a95bbbb7ae9e1e6d7a2e93fc` and video
`e3de7f279d7446db537cf2920492ff2bfc68777a`.

Frozen candidate: frame `420876c7a6d8e533e35ae5dff4b0d6c4dacd0281` and video
`3054572c76dc2d30beed4721316135c5b7639a66`, evaluated by the latter commit's
`benchmark/v3/judge.py`. The ten sealed requests and oracles are at
`0e451e3ee542b1270833aad26463b44daf017d61` (combined stored JSON contents
SHA-256 `e05b84c3edcddf7df45f813f87bfed59a3a4b1d0617a7f0cf738a54378cffada`).
Schema preflight: all 50 development and 10 sealed payloads.

## Workstation and recovery

- Main v2 and v1 instances were not cut over. Baseline controls use 8810/8811.
- V3 development uses 8814/8815. The coordinator `v3-release` starts a separate
  holdout pair 8816/8817 only after all 50 development outcomes are durable.
- `~/Videos/storyboard-v3/{baseline,pilot-results,rc-dev-results,rc-holdout-results}`
  contains first service outcomes and the external evaluation. A job may be
  playable and still fail. `LIVE INDEX.md` includes unrun cases.
- Detached coordinator logs: `~/ai/storyboard-build/v3/logs`. To resume without a
  duplicate POST, run the cross-repository frozen pair from `~/git/video-v3` with
  `bash benchmark/v3/release-run.sh`. Never delete a submission record as a way
  to make a case green. Reconcile a lost acknowledgement conservatively.
- This evidence branch is not a scored runtime. Do not move the frozen worktrees.

## Verified examples and issues

- Ruler/tick mechanism on D11 and ordinary bar lengths on D31 improved as pixels,
  but the first two pilots were **not** teaching passes. The D11 map dropped its
  printed scale, D31 changed pixels per unit while changing the baseline. Their
  frozen fixtures address both and keep the initial evidence intact.
- D01 candidate: first frame shows both decisions inputs, then arithmetic, then
  the separately scoped 40-cent conclusion. Counts [3,5] in the rendered raster.
  The independent transcript preserved the meaning; actual voice quality was
  not heard. A repeated cutout shows minor texture fragments.
- D02 revised wording avoided the baseline transcription rejection, but the
  first accepted candidate still fails to draw the waiting segment distinctly.
- The exact-same-recording graphic/market opening comparison is unscored.
  Both show exact text; the market version hides some fruit at phone size.
- Four off-corpus negative controls behaved as expected: tiny ticks, wrong arrow
  topology, exactly 45 s, and a caption before the reveal.
- The post-freeze experiments are on `v3/alignment-compounds` (`7d2924e`): accepted
  D05 and D29 reached media production with strict hyphen-fusion handling. This
  does not count toward the frozen result, and is not a claim that their editorial
  checks all passed.

No push. Editorial inspection and user listening are not model scores.
