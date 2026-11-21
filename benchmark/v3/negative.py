import json
from pathlib import Path
import sys
import time

import httpx

video,frame,out=sys.argv[1:]
path=Path(out);path.mkdir(parents=True,exist_ok=True)
tests={}


def done(client, pending):
    d=pending.json()
    for _ in range(240):
        r=client.get(d["status_url"]);r.raise_for_status()
        d=r.json()
        if d["state"] not in ("running","queued"):
            return d
        time.sleep(2)
    return d


with httpx.Client(base_url=frame,timeout=20) as h:
    s=h.post("/v2/sessions",json={"story_context":"negative control",
                                 "visual_signature":"Simple navy outline on warm paper."})
    s.raise_for_status()
    url=f"/v2/sessions/{s.json()['session_id']}/panels"
    p={"key":"tiny","op":"new_scene","scene_id":"test","paper_scene":True,
       "objective":"Distinguish ticks on a ruler","instruction":"Negative case", "retry_budget":0,
       "overlays":[{"type":"segment","from":[.2,.5],"to":[.22,.5],"divisions":12}]}
    r=h.post(url,json=p);r.raise_for_status();d=done(h,r)
    tests["unreadable_geometry"]={"expected":"needs_review","observed":d["state"],"detail":d}
    p.update(key="reversed",overlays=[{"type":"arrow","from":[.7,.5],"to":[.2,.5]}],
             expected_links=[{"from":"start","to":"finish"}])
    r=h.post(url,json=p);r.raise_for_status();d=done(h,r)
    tests["wrong_directed_ports"]={"expected":"needs_review","observed":d["state"],"detail":d}
with httpx.Client(base_url=video,timeout=20) as h:
    p={"op":"new_scene","scene_id":"x","objective":"Negative case","instruction":"Blank","paper_scene":True}
    req={"title":"Negative editorial checks","visual":{"story_context":"contract test",
         "visual_signature":"Plain paper, navy ink."},"voice_profile":"heart","script":[
         {"id":"a","text":"Read it now, but the result appears only at the end.",
          "caption":"THE RESULT","caption_not_before_beat":"reveal"}],
         "beats":[{"id":"opening","cue":{"ms":0},"panel":p},
                  {"id":"reveal","cue":{"utterance_id":"a","phrase":"at the end"},"panel":{**p,"scene_id":"y"}}]}
    r=h.post("/v2/renders",json={**req,"max_ms":45000})
    tests["exactly_45_seconds"]={"expected":422,"observed":r.status_code,"detail":r.json()}
    r=h.post("/v2/renders",json=req);r.raise_for_status();d=done(h,r)
    tests["premature_caption"]={"expected":"needs_review","observed":d["state"],"detail":d}
    if d["state"]=="needs_review" and "would disclose" not in d.get("error",""):
        tests["premature_caption"]["wrong_reason"]=True
    (path/"negative-results.json").write_text(json.dumps(tests,indent=2))
for k,v in tests.items():
    print(k,v["observed"],v.get("detail",{}).get("error",""))
assert all(x["expected"]==x["observed"] and not x.get("wrong_reason") for x in tests.values())
