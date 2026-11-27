import pytest
from pydantic import ValidationError

from video_renderer.api import EpisodeVideo, OpeningVideo
from video_renderer.drama3 import profile


@pytest.mark.parametrize("narrator", "AEF")
def test_selected_reference_is_available_and_hash_checked(narrator):
    config = profile(narrator)
    assert config["label"] == narrator
    assert len(config["reference"]["sha256"]) == 64


def test_opening_limits_do_not_weaken_episode_limits():
    request = {"title": "Opening", "visual": {}, "opening_preview": True, "chapter_starts": ["a"],
               "voice_profile": "drama3-A", "script": [{"id": "a", "text": "Look here."},
                                                          {"id": "b", "text": "What changed?"}],
               "beats": [{"id": "left", "cue": {"ms": 0}, "panel": {}},
                         {"id": "right", "cue": {"utterance_id": "b", "phrase": "what changed"}, "panel": {}}]}
    opening = OpeningVideo.model_validate(request)
    assert (opening.min_ms, opening.max_ms) == (10000, 20000)
    with pytest.raises(ValidationError):
        EpisodeVideo.model_validate(request)
