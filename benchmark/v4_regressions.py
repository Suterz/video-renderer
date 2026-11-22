"""Post-V3 known-case experiments; never write into a scored run."""
from pathlib import Path
import hashlib,json,os,sys,time
import httpx

from v4_controls import send

ROOT=Path.home()/"Videos/storyboard-v4"
old=Path.home()/"Videos/storyboard-v3"
url=os.environ.get("V4_REG_URL","http://127.0.0.1:8831")


def repaired_lesson(root,h):
    reply="The short upper latch holds the door."
    target=[.49,.40]
    good={"type":"arrow","from":[.75,.31],"to":target,"target_region":[.39,.36,.57,.445],"target_rgb":[191,77,49]}
    bad={**good,"to":[.49,.50]}
    setup=[
       {"type":"text","text":"WHICH PART HOLDS THE DOOR?","role":"question","at":[.5,.19],"fact":"question-title"},
       {"type":"shape","shape":"rect","at":[.48,.40],"extent":[.17,.08],"ink":"accent","fact":"latch"},
       {"type":"shape","shape":"rect","at":[.48,.50],"extent":[.17,.10],"ink":"accent","fact":"handle"},
       {"type":"text","text":"LATCH","role":"value","at":[.25,.40],"fact":"upper-label"},
       {"type":"text","text":"HANDLE","role":"support","at":[.25,.50],"fact":"lower-label"},
    ]
    end={"type":"text","at":[.5,.70],"text":"THE LATCH KEEPS IT CLOSED","role":"question"}
    req={"title":"Latch and handle","voice_profile":"heart","visual":{"story_context":"Explain a simple door latch.",
         "graphic_theme":"paper","visual_signature":"High contrast warm diagram."},
         "script":[{"id":"guide","text":"The short part is the latch. The long part is the handle."},
                   {"id":"ask","text":"Which part holds the door shut?","pause_after_ms":1550},
                   {"id":"answer","text":reply}],
         "instructional":{"question_utterance":"ask","answer_beat":"reveal","minimum_ms":1100,
             "required_facts":["latch","handle","upper-label","lower-label"],"region":[.08,.16,.92,.78]},
         "beats":[{"id":"opening","cue":{"ms":0},"panel":{"op":"new_scene","paper_scene":True,"scene_id":"door",
                   "instruction":"Two separate parts of a door closure.","objective":"Leave both parts visible.","overlays":setup}},
                  {"id":"reveal","parent":"opening","cue":{"utterance_id":"answer","phrase":"The short upper latch"},
                   "panel":{"op":"overlay_only","scene_id":"door","instruction":"Point at the upper latch.","objective":"Reveal the upper latch.",
                            "overlays":setup+[bad,end],"overlay_repairs":[setup+[good,end]],"retry_budget":1}}]}
    out=root/"full-repair"
    status=send(h,"/v2/renders",req,out)
    (out/"status.json").write_text(json.dumps(status,indent=2))
    print("full-repair",status["state"],status.get("error"),flush=True)
    if status["state"]=="succeeded":
        manifest=h.get(status["status_url"]+"/manifest").json()
        assert manifest["panels"][1]["accepted_attempt"]==1,manifest
        video=h.get(status["video_url"]).content
        (out/"video.mp4").write_bytes(video)
        (out/"manifest.json").write_text(json.dumps(manifest,indent=2))
        print("recorded repaired MP4",hashlib.sha256(video).hexdigest(),flush=True)


def speech(root,h):
    for key in ("H03","H04","H07","H10"):
        path=old/"rc-holdout-results"/key/"request.json"
        req=json.loads(path.read_text())
        if key=="H07":
            req["beats"][1]["cue"]["phrase"]="Read each stack’s"
        out=root/f"known-v3-{key}"
        status=send(h,"/v2/renders",req,out)
        (out/"status.json").write_text(json.dumps(status,indent=2))
        print(key,status["state"],status.get("error"),flush=True)
        if status["state"]=="succeeded":
            (out/"video.mp4").write_bytes(h.get(status["video_url"]).content)
            (out/"manifest.json").write_bytes(h.get(status["status_url"]+"/manifest").content)


if __name__=="__main__":
    with httpx.Client(base_url=url,timeout=25) as h:
        if sys.argv[1]=="speech":
            speech(ROOT/os.environ.get("V4_REG_OUTPUT","known-speech"),h)
        else:
            repaired_lesson(ROOT/os.environ.get("V4_REG_OUTPUT","known-repairs"),h)
