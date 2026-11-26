import pytest

from video_renderer.timeline import TimingReview, bind, corroborate_cue, cue_sample


@pytest.mark.parametrize(("speech", "forced"), [("you’ll", "youll"), ("they'll", "theyll"), ("it’ll", "itll")])
def test_contracted_word_keeps_its_actual_span_and_spoken_cue(speech, forced):
    script = [{"id": "u", "text": f"{speech} recognize it."}]
    timed = [{"word": forced, "start": .4, "end": .56},
             {"word": "recognize", "start": .57, "end": .8},
             {"word": "it", "start": .8, "end": .9}]
    cue = {"utterance_id": "u", "phrase": f"{speech} recognize"}
    bound = bind(script, timed)
    assert cue_sample(cue, bound) == 19200
    recognized = [{**timed[0], "word": speech}, *timed[1:]]
    assert corroborate_cue(cue, bound, recognized)["forced_onset"] == .4
    with pytest.raises(TimingReview, match="independent transcript"):
        corroborate_cue(cue, bound, [{**timed[0], "word": "you"}, *timed[1:]])


@pytest.mark.parametrize(("speech", "forced"), [("you’ll", "you"), ("we’ll", "well"), ("I’ll", "ill")])
def test_distinct_words_do_not_become_contractions(speech, forced):
    with pytest.raises(TimingReview, match="alignment token mismatch"):
        bind([{"id": "u", "text": speech}], [{"word": forced, "start": 0, "end": .2}])
