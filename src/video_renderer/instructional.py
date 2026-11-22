"""Temporal claims use accepted frame evidence and the encoded pixels."""
import subprocess
from pathlib import Path
from PIL import Image,ImageChops,ImageStat


class InstructionalReview(ValueError):
    pass


def exposure(mark, question, answer, frame_facts, starts, fps, minimum_ms):
    """A mark must exist on every displayed panel from question to answer."""
    if not 0 <= question < answer:
        raise InstructionalReview("question must precede answer")
    if (answer-question)*1000 < minimum_ms*fps:
        raise InstructionalReview("comparison hold is shorter than the requested minimum")
    selected=[i for i,s in enumerate(starts) if s < answer and (i==len(starts)-1 or starts[i+1]>question)]
    if not selected or any(mark not in frame_facts[i] for i in selected):
        raise InstructionalReview(f"required visual fact {mark!r} absent while viewer is asked to decide")
    return selected


def decode(ffmpeg,path,indices):
    ns=sorted(set(indices))
    select="+".join(f"eq(n\\,{n})" for n in ns)
    data=subprocess.check_output([str(ffmpeg),"-v","error","-i",str(path),"-an","-vf",
         f"select={select},scale=360:640","-fps_mode","passthrough","-f","rawvideo","-pix_fmt","rgb24","pipe:1"],timeout=90)
    stride=360*640*3
    if len(data)!=len(ns)*stride:
        raise InstructionalReview("could not decode every required reveal boundary")
    return {n:Image.frombytes("RGB",(360,640),data[i*stride:(i+1)*stride]) for i,n in enumerate(ns)}


def encoded_match(decoded, intended, rect, max_error=12):
    # Compare local evidence regions, not full-frame averages that hide a lost tick.
    box=tuple(round(v*(360,640)[i%2]) for i,v in enumerate(rect))
    ref=intended.convert("RGB").resize((360,640),Image.Resampling.LANCZOS)
    diff=ImageStat.Stat(ImageChops.difference(decoded.crop(box),ref.crop(box)))
    error=sum(diff.mean)/3
    if error>max_error:
        raise InstructionalReview(f"encoded frame disagrees with checked visual region (mean error {error:.1f})")
    return round(error,3)


def spoken_disclosures(bound,phrases,answer_sample):
    """Check explicitly declared answer phrases against forced original timing.

    This is a literal semantic guard, not a paraphrase detector. It never
    chooses a different answer or retimes the caller's footage.
    """
    from .timeline import sample,tokens
    findings=[]
    for phrase in phrases:
        sought=tokens(phrase)
        if len(sought)<2:
            raise InstructionalReview("answer embargo requires at least two spoken tokens")
        hits=[]
        for id_,(words,spans) in bound.items():
            for i in range(len(words)-len(sought)+1):
                if words[i:i+len(sought)]==sought:
                    hits.append({"utterance":id_,"start_sample":sample(spans[i]["start"])})
        if not hits:
            raise InstructionalReview(f"declared spoken answer phrase {phrase!r} does not occur")
        if any(h["start_sample"]<answer_sample for h in hits):
            raise InstructionalReview(f"spoken answer {phrase!r} occurs before its declared reveal")
        findings.append({"phrase":phrase,"matches":hits})
    return findings
