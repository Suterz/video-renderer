import pytest

from video_renderer.timeline import TimingReview, bind, corroborate_cue


def test_energy_cue_accepts_equivalent_notation_at_same_onset():
    text = "Example A receives 100 kWh"
    cue = {"utterance_id": "a", "phrase": text}
    measured = [{"word": word, "start": i*.30, "end": i*.30+.27}
                for i, word in enumerate(text.split())]
    bound = bind([{"id": "a", "text": text}], measured)
    first = measured[:3]
    for words in (["100kWh"], ["100", "kWh"], ["one", "hundred", "kilowatt", "hours"]):
        observed = first + [{"word": word, "start": .9+i*.2, "end": 1.0+i*.2}
                            for i, word in enumerate(words)]
        assert corroborate_cue(cue, bound, observed)["forced_onset"] == 0
    for spelling in ("10kWh", "100kW", "100.5kWh"):
        with pytest.raises(TimingReview):
            corroborate_cue(cue, bound, first + [{"word": spelling, "start": .9, "end": 1.2}])
    distant = [{**word, "start": word["start"]+2, "end": word["end"]+2} for word in measured]
    with pytest.raises(TimingReview):
        corroborate_cue(cue, bound, distant)
