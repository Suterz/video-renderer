import pytest
from video_renderer.timeline import TimingReview,bind,corroborate_cue


@pytest.mark.parametrize("word,digit", [("twelve","12"),("fifteen","15"),("nineteen","19")])
def test_asr_numeric_spelling_matches_without_accepting_different_values(word,digit):
    expected=[{"id":"u","text":f"Count {word} tiles"}]
    aligned=[{"word":w,"start":i*.2,"end":i*.2+.1} for i,w in enumerate(["Count",word,"tiles"])]
    cue={"utterance_id":"u","phrase":f"Count {word} tiles"}
    asr=[{"word":w,"start":i*.2} for i,w in enumerate(["Count",digit,"tiles"])]
    assert corroborate_cue(cue,bind(expected,aligned),asr)["forced_onset"]==0
    asr[1]["word"]=str(int(digit)+1)
    with pytest.raises(TimingReview,match="does not corroborate"):
        corroborate_cue(cue,bind(expected,aligned),asr)
