import pytest

from video_renderer.timeline import TimingReview, bind, corroborate_cue, cue_sample, end_frame, start_frame


def test_second_occurrence_and_internal_phrase():
    utterances = [{"id": "u", "text": "Per orange? Per orange, yes."}]
    spans = [{"word": word, "start": i / 10, "end": (i + 1) / 10}
             for i, word in enumerate(["per", "orange", "per", "orange", "yes"])]
    bound = bind(utterances, spans)
    cue = {"utterance_id": "u", "phrase": "per orange"}
    with pytest.raises(TimingReview, match="matched 2 times"):
        cue_sample(cue, bound)
    assert cue_sample({**cue, "occurrence": 2}, bound) == 9600
    assert cue_sample({**cue, "occurrence": 2, "edge": "end"}, bound) == 19200
    with pytest.raises(TimingReview, match="matched 0 times"):
        cue_sample({**cue, "phrase": "per pear"}, bound)


def test_final_hold_frame_rounding():
    assert start_frame(5813 * 48, 30) == 174
    assert end_frame(25849 * 48, 30) == 776
    assert end_frame(26349 * 48, 30) == 791
    assert end_frame(44999 * 48, 30) == 1350
    assert end_frame(44966 * 48, 30) == 1349


def test_nonspoken_token_is_rejected():
    with pytest.raises(TimingReview, match="token mismatch"):
        bind([{"id": "u", "text": "one dollar sixty"}],
             [{"word": "one", "start": 0, "end": .1}, {"word": "dollar", "start": .1, "end": .2}])


def test_independent_asr_corroborates_correct_units_but_not_wrong_ones():
    a = [{"word": "four", "start": 1.2, "end": 1.4}, {"word": "kilometers", "start": 1.4, "end": 1.9}]
    bound = bind([{"id": "u", "text": "four kilometers"}], a)
    cue = {"utterance_id": "u", "phrase": "four kilometers"}
    asr = [{"word": "4", "start": 1.3}, {"word": "km", "start": 1.5}]
    assert corroborate_cue(cue, bound, asr)["forced_onset"] == 1.2
    with pytest.raises(TimingReview, match="does not corroborate"):
        corroborate_cue(cue, bound, [asr[0], {"word": "meters", "start": 1.5}])
