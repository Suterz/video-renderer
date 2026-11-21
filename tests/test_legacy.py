import json
from pathlib import Path

import pytest

from video_renderer.api import translate_legacy

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def load(name):
    p = EXAMPLES / name
    d = json.loads((p / "story.json").read_text())
    d["signature"] = (p / "signature.md").read_text()
    return d


@pytest.mark.parametrize("name", ["unit-price", "signal-flow", "fruit-route", "smoke"])
def test_legacy_examples_convert(name):
    story = load(name)
    request = translate_legacy(story)
    assert request.visual["legacy_input"]
    assert [b.id for b in request.beats] == [p["id"] for p in story["panels"]]


def test_legacy_duration_and_references():
    story = load("unit-price")
    for invalid in (44999, 45000):
        with pytest.raises(ValueError):
            translate_legacy({**story, "end_ms": invalid})
    story["panels"][1]["refs"] = ["unknown"]
    with pytest.raises(ValueError, match="previous panel"):
        translate_legacy(story)
