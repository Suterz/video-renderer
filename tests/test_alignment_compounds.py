import pytest

from video_renderer.timeline import TimingReview,bind,cue_sample


def word(text,start,end):
    return {"word":text,"start":start,"end":end}


@pytest.mark.parametrize("span", [("half-minute","halfminute"),("twenty-five","twentyfive"),("straight-sided","straightsided")])
def test_fused_aligner_compound_does_not_drop_later_cues(span):
    authored,heard=span
    s=[{"id":"a","text":f"A {authored} example."}]
    aligned=[word("A",0,.1),word(heard,.1,.55),word("example",.55,1)]
    b=bind(s,aligned)
    assert cue_sample({"utterance_id":"a","phrase":"example"},b)==26400
    assert cue_sample({"utterance_id":"a","phrase":authored},b)==4800
    with pytest.raises(TimingReview,match="internal boundary"):
        cue_sample({"utterance_id":"a","phrase":authored.split("-")[1]},b)


def test_wrong_word_cannot_be_repaired_as_punctuation():
    with pytest.raises(TimingReview):
        bind([{"id":"a","text":"twenty-five pounds"}],
             [word("twentysix",0,.5),word("pounds",.5,1)])
