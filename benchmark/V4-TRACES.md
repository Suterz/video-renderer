# Zero-repair trace and staged results

V3 frozen reference: frame `420876c`, video `3054572`, final evidence
`47f2882`. V4 starts from opt-in cutout work `a116950` and conservative
alignment work `c57ad89`, on separate worktrees. Fresh inputs were sealed
before runtime tuning at `6f81401960c11c54ca729c872bf8aa0cb98dc2f8`.

| V3 case | Terminal behavior and reason | New test |
|---|---|---|
| H05, `02f8e4a106d9477eb80709fb0a39496d` | Accepted. The initial grounding was sufficient for old generic geometry but neither composed panel asked whether the tip hit the slider. The retained contact sheet shows it on the adjoining pull assembly. | Check isolated actual arrow ink against a controlled target, or inspect the composed crop and phone view for a semantic part. |
| H09, `45a7aa1dd6b9473fa8761fc1457ee131` | Accepted. Both later beats were overlay-only. The measure shortened but the clean characters did not move. | An action claim cannot be submitted on an overlay-only beat; generated action checks compare actual clean before/after pixels and images. |
| D11, `e2ed1330de834c68a11921814e874a25` | Accepted. At decoded frames 0–282 the ticks were absent while the viewer was asked for the marked distance. A correct conclusion did not repair the missing setup. | Verify named raster marks covering the question interval and their regions on decoded MP4 boundaries. |
| H03/H04/H07/H10 | Safely refused in speech binding, before any frame request. Fused hyphenated words, dropped possessive apostrophes, and fused clock-number compounds exposed exact-token assumptions. H07 also had an authored cue that omitted the possessive suffix. | Reconcile only verified lexical forms and reject interior boundaries of fused spans. Replay the four actual archived alignment/ASR traces. |

All 139 persisted V3 development frame reviews recorded exactly one candidate.
Those defects did not trigger a repair; this was not 139 successful repairs
omitted from the summary. The old tally also missed stages that never completed
or wrote a review before an exception. V4 records each attempted candidate as
soon as the directory is created, and distinguishes accepted/rejected/failed
records. Operational retries do not become visual repairs.

The paired public controls cover wrong-but-same-color target, correct target,
explicit same-art alternate, and correct-versus-late setup geometry. The cutout
and alignment branches remain regression evidence, not prior fresh-case wins.
