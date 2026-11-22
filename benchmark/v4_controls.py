"""Public API controls: no pre-rendered assets or silent caller retries."""
import argparse
import json
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor
import httpx


def send(h,path,body,folder):
    folder.mkdir(parents=True,exist_ok=False)
    (folder/"request.json").write_text(json.dumps(body,indent=2))
    r=h.post(path,json=body)
    initial=r.json()
    (folder/"submission.json").write_text(json.dumps(initial,indent=2))
    if r.status_code==422:
        return {"state":"invalid","diagnostic":initial}
    r.raise_for_status()
    for _ in range(800):
        d=h.get(initial["status_url"]).json()
        if d["state"] not in ("queued","running"):
            return d
        time.sleep(1)
    raise TimeoutError(initial)


def parts(url,root):
    with httpx.Client(base_url=url,timeout=20) as h:
        s=h.post("/v2/sessions",json={"story_context":"An illustrated mechanism with a small upper latch and a longer neighboring handle.",
             "visual_signature":"Dark ink and rust shapes on ivory.","graphic_theme":"paper"})
        s.raise_for_status()
        path=f"/v2/sessions/{s.json()['session_id']}/panels"
        for name,variant in (("wrong",0),("correct",1),("repaired",2)):
            shapes=[
              {"type":"shape","shape":"rect","at":[.48,.40],"extent":[.17,.08],"ink":"accent"},
              {"type":"shape","shape":"rect","at":[.48,.50],"extent":[.17,.10],"ink":"accent"},
              {"type":"text","at":[.48,.22],"text":"WHICH PART IS THE LATCH?","role":"question"}
            ]
            good={"type":"arrow","from":[.79,.30],"to":[.50,.40],"target_region":[.395,.36,.566,.441],"target_rgb":[191,77,49]}
            bad={**good,"to":[.5,.49]}
            body={"op":"new_scene","paper_scene":True,"key":name,"scene_id":"mechanism","instruction":"Two visibly adjacent parts.",
                  "objective":"Mark the short latch, not the long handle.", "overlays":shapes+[good if variant==1 else bad],
                  "retry_budget":1,"overlay_repairs":[shapes+[good]] if variant==2 else []}
            out=root/f"part-{name}"
            d=send(h,path,body,out)
            (out/"status.json").write_text(json.dumps(d,indent=2))
            assert d["state"]==("needs_review" if variant==0 else "accepted"),d
            for filename in ("review.json","phone.png"):
                if filename in d.get("artifacts",{}):
                    (out/filename).write_bytes(h.get(d["artifacts"][filename]).content)
            if variant==2:
                assert d["summary"]["accepted_attempt"]==1,d
            print(name,d["state"],flush=True)
        # An annotation-only request cannot certify an action.
        d=send(h,path,{"key":"false-motion","scene_id":"mechanism","op":"overlay_only","parent_panel_id":d["panel_id"],
            "instruction":"Move only the label.","objective":"Show the handle moving.","action_claim":"The handle travels right."},root/"motion-negative")
        (root/"motion-negative/status.json").write_text(json.dumps(d,indent=2))
        assert d["state"]=="invalid",d


def reveal_controls(url,root):
    with httpx.Client(base_url=url,timeout=20) as h:
        for positive in (True,False,"repair"):
            title="Count the equal gaps"
            tick={"type":"segment","from":[.24,.47],"to":[.76,.47],"divisions":2,"fact":"ruler"}
            label={"type":"text","at":[.5,.28],"text":"ONE GAP IS TWO UNITS","fact":"scale","role":"value"}
            req={"title":title,"visual":{"story_context":"Diagram with fixed scale and endpoints.",
                  "visual_signature":"A clear map-style paper diagram.", "graphic_theme":"atlas"},
                 "voice_profile":"heart",
                 "script":[{"id":"setup","text":"Each gap stands for two units."},
                           {"id":"q","text":"How many units are there in two gaps?","pause_after_ms":1650,"caption":"How many units are there in two gaps?"},
                           {"id":"r","text":"Two gaps make four units.","caption":""}],
                 "instructional":{"question_utterance":"q","answer_beat":"answer","required_facts":["ruler","scale"],"minimum_ms":1180,"region":[.1,.2,.9,.78]},
                 "beats":[{"id":"opening","cue":{"ms":0},"panel":{"op":"new_scene","scene_id":"scale","paper_scene":True,
                           "instruction":"An exact scale.","objective":"Show the key and mark the span.","overlays":[label]+([tick] if positive is True else [{"type":"segment","from":[.24,.47],"to":[.76,.47]}]),
                           "overlay_repairs":[[label,tick]] if positive=="repair" else [],"retry_budget":1}},
                          {"id":"answer","cue":{"utterance_id":"r","phrase":"Two gaps"},"parent":"opening",
                           "panel":{"op":"overlay_only","scene_id":"scale","instruction":"Reveal answer.","objective":"Show four units.",
                                    "overlays":[label,tick,{"type":"text","at":[.5,.64],"text":"TWO GAPS = FOUR UNITS","role":"value"}]}}]}
            folder=root/("before-repaired" if positive=="repair" else "before-correct" if positive else "before-wrong")
            d=send(h,"/v2/renders",req,folder)
            (folder/"status.json").write_text(json.dumps(d,indent=2))
            if positive:
                assert d["state"]=="succeeded",d
                (folder/"video.mp4").write_bytes(h.get(d["video_url"]).content)
                m=h.get(d["status_url"]+"/manifest").json()
                if positive=="repair":
                    assert m["panels"][0]["accepted_attempt"]==1,m
                (folder/"manifest.json").write_text(json.dumps(m,indent=2))
            else:
                assert d["state"]=="needs_review" and "ruler" in d["error"],d
            print(folder.name,d["state"],flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("root",type=Path)
    p.add_argument("--frame",default="http://127.0.0.1:8830")
    p.add_argument("--video",default="http://127.0.0.1:8831")
    a=p.parse_args()
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks=[pool.submit(parts,a.frame,a.root),pool.submit(reveal_controls,a.video,a.root)]
        for f in tasks:
            f.result()
