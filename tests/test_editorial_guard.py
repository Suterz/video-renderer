"""Known regression: map distance in the subtitle before its visual reveal."""
import pytest

from video_renderer.api import Utterance, Review, guard_captions


def test_map_answer_cannot_leak_at_utterance_start():
    u=Utterance(id="answer",text="After the last tick, four kilometers",
                caption="4 km",caption_not_before_beat="reveal")
    with pytest.raises(Review,match="before beat reveal"):
        guard_captions([u],{"answer":([], [{"start":4.00}])},{"reveal":221},30)


def test_money_caption_can_start_at_its_beat():
    u=Utterance(id="answer",text="Forty cents less",caption="40¢ LESS",caption_not_before_beat="win")
    guard_captions([u],{"answer":([], [{"start":7.36}])},{"win":221},30)


def test_prior_unguarded_requests_keep_their_behavior():
    u=Utterance(id="answer",text="Old fixture",caption="Old fixture")
    guard_captions([u],{}, {},30)
