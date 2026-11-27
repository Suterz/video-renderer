import pytest

from video_renderer.timeline import TimingReview, bind, corroborate_cue, cue_sample, tokens


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
    script = [{"id": "a", "text": "Here—we’ll compare."}]
    fused = [{"word": "herewell", "start": 0, "end": .8},
             {"word": "compare", "start": .8, "end": 1.2}]
    speech = [{"word": "Here", "start": 0, "end": .35},
              {"word": "We'll", "start": .4, "end": .8},
              {"word": "compare", "start": .8, "end": 1.2}]
    assert bind(script, fused, speech)["a"][1][1]["internal_start"]
    with pytest.raises(TimingReview):
        bind(script, fused, [{**word, "word": "Well"} if i == 1 else word for i, word in enumerate(speech)])


def test_youd_binds_without_discarding_the_contraction():
    line = [{"id": "s", "text": "You’d need twenty dollars."}]
    assert bind(line, spans("Youd", "need", "twenty", "dollars"))["s"][0][0] == "you'd"
    with pytest.raises(TimingReview):
        bind(line, spans("You", "need", "twenty", "dollars"))


def test_spoken_model_name_matches_only_the_same_rendered_version():
    script = [{"id": "a", "text": "GPT-four citations."}]
    bound = bind(script, spans("GPT", "four", "citations"))
    cue = {"utterance_id": "a", "phrase": "GPT-four citations"}
    assert corroborate_cue(cue, bound, spans("GPT-4", "citations"))["forced_onset"] == 0
    with pytest.raises(TimingReview):
        corroborate_cue(cue, bound, spans("GPT-3.5", "citations"))
    late = bind(script, [
        {"word": "GPTfour", "start": .8, "end": 1.04},
        {"word": "citations", "start": 1.04, "end": 1.84},
    ])
    separate = [{"word": " GPT", "start": 0, "end": .74},
                {"word": "-4", "start": .74, "end": 1.02},
                {"word": " citations", "start": 1.02, "end": 1.56}]
    assert corroborate_cue(cue, late, separate)["forced_onset"] == .8
