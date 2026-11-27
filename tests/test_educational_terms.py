import pytest

from video_renderer.timeline import TimingReview, bind, cue_sample, tokens


def spans(*terms):
    return [{"word": term, "start": i, "end": i + .5} for i, term in enumerate(terms)]


def test_written_amounts_and_named_model_versions_keep_exact_identity():
    text = "GPT-3.5 has $100,000."
    assert tokens(text) == ["gpt35", "has", "100000"]
    bound = bind([{"id": "s", "text": text}], spans("GPT35", "has", "100000"))
    assert cue_sample({"utterance_id": "s", "phrase": "$100,000"}, bound) == 96000
    for incorrect in (spans("GPT4", "has", "100000"), spans("GPT35", "has", "10000")):
        with pytest.raises(TimingReview):
            bind([{"id": "s", "text": text}], incorrect)


def test_fused_dash_does_not_expose_unknown_internal_timing():
    bound = bind([{"id": "s", "text": "The loan didn’t move—it’s still here."}],
                 spans("The", "loan", "didnt", "moveits", "still", "here"))
    assert cue_sample({"utterance_id": "s", "phrase": "The loan"}, bound) == 0
    with pytest.raises(TimingReview):
        cue_sample({"utterance_id": "s", "phrase": "it's still"}, bound)
    assert bind([{"id":"s","text":"Reserves—they've dropped."}],
                spans("reservestheyve", "dropped"))["s"][0] == ["reserves", "they've", "dropped"]


def test_ambiguous_contraction_requires_local_independent_corroboration():
    script = [{"id": "a", "text": "We’re looking."}]
    aligned = spans("Were", "looking")
    assert bind(script, aligned, spans("We’re", "looking"))["a"][0] == ["we're", "looking"]
    with pytest.raises(TimingReview):
        bind(script, aligned, spans("Were", "looking"))
