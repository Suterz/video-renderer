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


def test_submission_acknowledgement_recovery_is_durable(tmp_path,monkeypatch):
    import queue
    from video_renderer import api
    monkeypatch.setattr(api,"ROOT",tmp_path)
    monkeypatch.setattr(api,"tasks",queue.Queue())
    q=api.Video(title="one lesson",visual={},voice_profile="heart",script=[{"id":"a","text":"A lesson."}],
                beats=[{"id":"open","cue":{"ms":0},"panel":{}}])
    first=api.submit(q,key="sealed-evaluation-1")
    assert api.submitted("sealed-evaluation-1")["id"]==first["id"]
    assert api.submit(q,key="sealed-evaluation-1")["id"]==first["id"]
    assert api.tasks.qsize()==1
    q.title="changed"
    with pytest.raises(api.HTTPException) as err:
        api.submit(q,key="sealed-evaluation-1")
    assert err.value.status_code==409


def test_corroboration_with_asr_assigning_the_leading_pause():
    from video_renderer.timeline import corroborate_cue,TimingReview
    desired={"utterance_id":"u","phrase":"The order is"}
    bound={"u":(["the","order","is"],[{"start":13.76}])}
    asr=[{"word":"The","start":13.08,"end":13.84},{"word":"order","start":13.84,"end":14.08},
         {"word":"is","start":14.08,"end":14.34}]
    assert corroborate_cue(desired,bound,asr)["forced_onset"]==13.76
    asr[1]["word"]="answer"
    with pytest.raises(TimingReview):
        corroborate_cue(desired,bound,asr)


def test_composed_tens_are_lexically_equal_without_accepting_wrong_units():
    from video_renderer.timeline import bind,corroborate_cue,TimingReview
    words=["Read","twenty","three","degrees"]
    b=bind([{"id":"u","text":"Read twenty-three degrees."}],
           [{"word":w,"start":i*.15,"end":i*.15+.12} for i,w in enumerate(words)])
    cue={"utterance_id":"u","phrase":"twenty-three degrees"}
    asr=[{"word":"23","start":.15},{"word":"degrees","start":.40}]
    assert corroborate_cue(cue,b,asr)["forced_onset"]==.15
    for word in ("twenty","24"):
        with pytest.raises(TimingReview):
            corroborate_cue(cue,b,[{"word":word,"start":.15},asr[1]])
    with pytest.raises(TimingReview):
        corroborate_cue(cue,b,[asr[0],{"word":"meters","start":.40}])
