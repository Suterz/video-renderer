import pytest
from PIL import Image,ImageDraw
from video_renderer.instructional import InstructionalReview,exposure,encoded_match


def test_late_ticks_do_not_count_as_setup():
    assert exposure("ticks",60,150,[{"ticks"},{"ticks"},set()],[0,85,150],30,1200)==[0,1]
    with pytest.raises(InstructionalReview,match="absent"):
        exposure("ticks",60,150,[set(),{"ticks"},set()],[0,85,150],30,1200)


def test_phone_region_not_averaged_with_blank_surroundings():
    after=Image.new("RGB",(360,640),"white")
    before=after.copy()
    ImageDraw.Draw(after).rectangle((130,210,170,231),fill="#482536")
    assert encoded_match(after,after,(.35,.325,.48,.37))==0
    with pytest.raises(InstructionalReview,match="encoded"):
        encoded_match(before,after,(.35,.325,.48,.37))


def test_alignment_punctuation_recovery_preserves_cue_boundaries():
    from video_renderer.timeline import bind,cue_sample,TimingReview
    words=["the","clocks","read","fiftynine","then","ohone"]
    spans=[{"word":w,"start":i,"end":i+.8} for i,w in enumerate(words)]
    script=[{"id":"u","text":"The clock's read fifty nine then oh one"}]
    result=bind(script,spans)
    assert cue_sample({"utterance_id":"u","phrase":"fifty nine"},result)==144000
    with pytest.raises(TimingReview,match="internal boundary"):
        cue_sample({"utterance_id":"u","phrase":"nine"},result)
    spans[3]["word"]="fiftyeight"
    with pytest.raises(TimingReview,match="mismatch"):
        bind(script,spans)
