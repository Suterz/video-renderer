# V3 frozen evaluation

No new production cutover. Development and held-out results preserve the first
public API submission and original service status. This document records the
independent outcome; an accepted MP4 can fail on meaning.

| Run | Submitted | Verified one-shot | Safely refused | Incorrect accepted | Operational / unjudged | Median/p95 seconds |
|---|---:|---:|---:|---:|---:|---:|
| V2 baseline | 50 | 2 | 16 | 32 | 0 / 0 | 52.1 / 118.1 |
| Frozen V3 development | 50 | 10 | 15 | 25 | 0 / 0 | 30.0 / 100.1 |
| Sealed V3 holdout | 10 | 1 | 5 | 4 | 0 / 0 | 37.0 / 64.1 |

All verified passes were first-candidate passes. This does not imply there were
no internal retries among refused jobs: missing failure telemetry is not zero.
The held-out release gate was not met.

- Baseline frames `ffc6013c517ce3c1a95bbbb7ae9e1e6d7a2e93fc`; video
  `e3de7f279d7446db537cf2920492ff2bfc68777a`.
- Frozen V3 frames `420876c7a6d8e533e35ae5dff4b0d6c4dacd0281`; video
  `3054572c76dc2d30beed4721316135c5b7639a66`.
- Sealed set `0e451e3ee542b1270833aad26463b44daf017d61`.
- Evidence in this branch is a snapshot only. Full media, first run records,
  decoded frames, inspection notes, and run configurations live under
  `~/Videos/storyboard-v3/` on the workstation.

## Preserve these failures as regressions

1. **H05, part safety:** the annotated tip lies on a neighboring gold pull
   assembly, not where the two rows of teeth meet. A correct object-class
   orientation and plausible color are not enough. Require a part-level
   relation check with a neighboring-part negative; do not use the frozen
   input as proof of a fresh holdout.
2. **H09, temporal evidence:** actual subject positions do not change while
   only the displayed measurement shrinks. The content request and decoded
   before/after frames must support consistent subject motion about a fixed
   mirror, not merely a new measurement overlay. H08 similarly relabels
   stationary silhouettes rather than moving three identifiable queue entries.
3. **H02, state readability:** decorative background hides the fold connections.
   Four bars read like separate sheets. Explicitly distinguish the invariant
   sheet and temporary cross-section.
4. **H03/H04/H07/H10, transcription binding:** fused tokens or omitted
   apostrophes safely refuse despite otherwise valid author text. The
   post-freeze compounds branch fixes only demonstrated development variants
   (D05, D29, D07, D46). Those results are not inserted into the original score.
5. **H06, layout safety:** the service refused a label outside the visual
   safe region. The next authoring preflight must handle long text next to
   a wide diagram without erasing the measurement rule.
6. **D08/D11, prediction setup:** moving a correct revelation earlier as a
   picture can fix missing givens, but predictions still need time and the
   conclusion must stay gated. The unscored post-freeze clips show the repair.

## Review boundaries

Grounding and review model judgments are distinct from measured raster geometry
and the decoded-picture inspection. No direct listening, real audience
comprehension, engagement or marketing claims. If this frozen evaluation is
used to tune again, all ten H cases belong to regression and a newly sealed
set is needed for an independent held-out claim.
