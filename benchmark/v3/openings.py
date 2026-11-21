"""Unscored creative control: one recording and timing, two separate layouts."""
import json
import hashlib
from pathlib import Path
import sys
import time

import httpx
from corpus import HERE, read_cases, compile_case

base,store,out=sys.argv[1:]
out=Path(out); out.mkdir(parents=True,exist_ok=True)
case=read_cases(HERE/"first.tsv")["D01"]
prior=None
with httpx.Client(base_url=base,timeout=30) as h:
    for kind in ("graphic","market"):
        req,_=compile_case(case,"v3")
        req["title"]="Which is cheaper per orange? — "+kind
        req["script"]=[{"id":"question","text":"Which costs less per orange? Take a look.","caption":None}]
        req["beats"]=req["beats"][:1]
        req["closing_hold_ms"]=2300
        req["voice_profile"]="ryan"
        req["reuse_recording_from"]=prior
        p=req["beats"][0]["panel"]
        p["overlays"][0]["text"]="WHICH COSTS LESS PER ORANGE?"
        p["overlays"]=[p["overlays"][0],
                       {"type":"text","text":"3 FOR $6","role":"value","at":[.28,.66]},
                       {"type":"text","text":"5 FOR $8","role":"value","at":[.72,.66]}]
        if kind=="market":
            p.pop("layout")
            req["visual"].pop("assets")
            p["instruction"]=("Illustrated street market. A curious shopper in the upper third looks down at two clearly separated open grocery bags on a low counter, left and right. "
                              "Exactly THREE round oranges clearly visible in the left and FIVE in the right, none hidden, no other fruit. "
                              "The two bag bodies begin well below the shopper and are keyed to x=28 percent and x=72 percent. "
                              "Leave the bottom quarter clear. No lettering, numbers, arrow or price tag.")
        else:
            layout=p["layout"]["layers"]
            for i,entry in enumerate(layout):
                pool=([(.20,.45),(.28,.45),(.36,.45)] if i<3 else [(.64,.43),(.72,.43),(.80,.43),(.68,.52),(.76,.52)])
                entry["center"]=list(pool[i if i<3 else i-3])
                entry["width"]=.071
        r=h.post("/v2/renders",json=req);r.raise_for_status()
        d=r.json()
        (out/f"{kind}-submission.json").write_text(json.dumps(d,indent=2))
        for _ in range(450):
            time.sleep(2)
            s=h.get(d["status_url"]).json()
            if s["state"] not in ("queued","running"):
                break
        (out/f"{kind}-status.json").write_text(json.dumps(s,indent=2))
        if s["state"]!="succeeded":
            print(kind,s,flush=True)
            if not prior:
                raise SystemExit("no accepted opening recording; preserve first failure")
            continue
        dest=out/f"{kind}.mp4"
        r=h.get(d["video_url"]);r.raise_for_status()
        dest.write_bytes(r.content)
        m=Path(store)/d["id"]/"manifest.json"
        manifest=json.loads(m.read_text())
        (out/f"{kind}-evidence.json").write_text(json.dumps({"mp4_sha256":hashlib.sha256(r.content).hexdigest(),
            "wav_sha256":manifest["wav_sha256"],"duration":manifest["verification"]["ffprobe"]["format"]["duration"]},indent=2))
        prior=d["id"]
        print(kind,prior,manifest["wav_sha256"],flush=True)
