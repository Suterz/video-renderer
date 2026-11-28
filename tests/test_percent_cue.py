import pytest

from video_renderer.timeline import TimingReview, corroborate_cue


def test_corroborate_percent_without_dropping_value_or_unit():
    cue = {"utterance_id": "answer", "phrase": "Eighty percent. Forty"}
    tokens = ["eighty", "percent", "forty", "divided"]
    bound = {"answer": (tokens, [{"start": n*.2, "end": n*.2+.18} for n in range(len(tokens))])}
    def asr(value):
        return [{"word": value, "start": 0, "end": .35}, {"word": "40", "start": .4, "end": .58}]
    assert corroborate_cue(cue, bound, asr("80%."))["forced_onset"] == 0
    split = [{"word": "80", "start": 0, "end": .18}, {"word": "%", "start": .18, "end": .35},
             {"word": "40", "start": .4, "end": .58}]
    assert corroborate_cue(cue, bound, split)["forced_onset"] == 0
    for value in ("80", "81%", "80.5%"):
        with pytest.raises(TimingReview):
            corroborate_cue(cue, bound, asr(value))
