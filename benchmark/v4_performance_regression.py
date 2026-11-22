"""Voice and real uploaded pause controls with identical visuals."""
import hashlib,json
from io import BytesIO
from pathlib import Path
import time,wave
import httpx

base=Path.home()/"Videos/storyboard-v4"
original=json.loads((base/"pilot/D11/outcome.json").read_text())
job=Path(original["job_dir"])
m=json.loads((job/"manifest.json").read_text())
req=json.loads((base/"pilot/D11/request.json").read_text())
original_profile=req["voice_profile"]
req["reuse_visuals_from"]=job.name
p=base/"performance"
p.mkdir(exist_ok=False)
with httpx.Client(base_url="http://127.0.0.1:8831",timeout=30) as h:
    for mode in ("other-voice","paused-upload"):
        current=json.loads(json.dumps(req))
        if mode=="other-voice":
            current["voice_profile"]="ryan" if original_profile=="heart" else "heart"
            r=h.post("/v2/renders",json=current)
        else:
            current["voice_profile"]=None
            for u in current["script"]:
                u.pop("pause_after_ms",None)
            scene=m["instructional_evidence"]
            point=(scene["answer_frame"]+scene["question_end_frame"])/60
            with wave.open(str(job/"narration.wav"),"rb") as f:
                assert f.getnchannels()==1 and f.getframerate()==48000 and f.getsampwidth()==2
                data=f.readframes(f.getnframes())
            i=round(point*48000)*2
            result=BytesIO()
            with wave.open(result,"wb") as f:
                f.setparams((1,2,48000,0,"NONE","not compressed"))
                f.writeframes(data[:i]+bytes(76800)+data[i:])
            r=h.post("/v2/renders/upload",data={"request":json.dumps(current)},
                     files={"audio":("pause.wav",result.getvalue(),"audio/wav")})
        r.raise_for_status()
        d=r.json()
        here=p/mode;here.mkdir()
        (here/"submission.json").write_text(json.dumps(d))
        path=d["status_url"]
        for _ in range(650):
            time.sleep(2)
            d=h.get(path).json()
            if d["state"] not in ("queued","running"):
                break
        (here/"status.json").write_text(json.dumps(d,indent=2))
        if d["state"]!="succeeded":
            print(mode,d,flush=True);continue
        v=h.get(path+"/manifest").json()
        assert [x["sha256"] for x in m["panels"]]==[x["sha256"] for x in v["panels"]]
        original_cuts=[x["frame"] for x in m["beats"]]
        aligned_cuts=[x["frame"] for x in v["beats"]]
        assert original_cuts!=aligned_cuts
        if mode=="paused-upload":
            assert all(abs((b-a)-24)<=4 for a,b in zip(original_cuts[1:],aligned_cuts[1:])),(original_cuts,aligned_cuts)
        media=h.get(d["video_url"]).content
        (here/"video.mp4").write_bytes(media)
        (here/"evidence.json").write_text(json.dumps({"before_frames":original_cuts,"after_frames":aligned_cuts,
            "frame_shifts":[b-a for a,b in zip(original_cuts,aligned_cuts)],"same_art":[x["sha256"] for x in v["panels"]],
            "verified_decode":v["instructional_evidence"],"mp4_sha256":hashlib.sha256(media).hexdigest()},indent=2))
        print(mode,"rendered",original_cuts,aligned_cuts,flush=True)
