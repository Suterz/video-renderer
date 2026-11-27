import wave

import pytest
from pydantic import ValidationError

from video_renderer import api


def request():
    return {"title": "Episode", "visual": {}, "voice_profile": "heart",
            "script": [{"id": "a-line", "text": "Same words."}, {"id": "b-line", "text": "Same words."}],
            "beats": [{"id": "a-cut", "cue": {"ms": 0}, "panel": {}},
                      {"id": "b-cut", "cue": {"utterance_id": "b-line", "phrase": "same words"}, "panel": {}}]}


def test_long_form_requires_explicit_episode_entry_point():
    payload = {**request(), "chapter_starts": ["a-line", "b-line"], "max_ms": 300000}
    assert api.EpisodeVideo.model_validate(payload).max_ms == 300000
    with pytest.raises(ValidationError):
        api.Video.model_validate(payload)
    with pytest.raises(ValidationError):
        api.EpisodeVideo.model_validate({**payload, "chapter_starts": ["b-line", "a-line"]})


def test_rebase_repeated_phrase_and_resume_existing_pcm(monkeypatch, tmp_path):
    req = api.EpisodeVideo.model_validate({**request(), "chapter_starts": ["a-line", "b-line"]})
    monkeypatch.setattr(api, "state", lambda *args, **kwargs: None)
    def speech(mode, path, text):
        if mode == "heart":
            with wave.open(str(path), "wb") as writer:
                writer.setparams((1,2,48000,0,"NONE","not compressed"))
                writer.writeframes(bytes(96000))
        else:
            return [{"word": "Same", "start": .2, "end": .3}, {"word": "words", "start": .4, "end": .7}]
    monkeypatch.setattr(api, "speech", speech)
    _, count, measured, observed, parts = api.episode_speech(tmp_path, req)
    assert count == 96000
    assert [x["start_sample"] for x in parts] == [0, 48000]
    assert measured[2]["start"] == observed[2]["start"] == 1.2
    def unexpected_speech(*args):
        pytest.fail("verified checkpoint should bypass synthesis and alignment")
    monkeypatch.setattr(api, "speech", unexpected_speech)
    _, count2, measured2, observed2, parts2 = api.episode_speech(tmp_path, req)
    assert (count2, measured2, observed2, parts2) == (count, measured, observed, parts)
