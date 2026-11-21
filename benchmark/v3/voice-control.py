"""Unscored narrator comparison for a verified candidate."""
from pathlib import Path
import httpx,json,sys,time

base=Path.home()/"Videos/storyboard-v3"
key=sys.argv[1]
root=base/"rc-dev-results"/key
original=json.loads((root/"outcome.json").read_text())
previous=Path(original["job_dir"])
request=json.loads((root/"request.json").read_text())
initial=json.loads((previous/"manifest.json").read_text())
request["reuse_visuals_from"]=original["job_id"]
request["voice_profile"]="heart" if request["voice_profile"]=="ryan" else "ryan"
dest=base/"voice-control"/key
dest.mkdir(parents=True,exist_ok=False)
with httpx.Client(base_url="http://127.0.0.1:8815",timeout=30) as c:
    r=c.post("/v2/renders",json=request)
    r.raise_for_status()
    post=r.json()
    (dest/"submission.json").write_text(json.dumps(post,indent=2))
    for _ in range(400):
        time.sleep(2)
        v=c.get(post["status_url"]).json()
        if v["state"] not in ("queued","running"):
            break
    (dest/"terminal.json").write_text(json.dumps(v,indent=2))
    if v["state"] != "succeeded":
        raise SystemExit(v)
    result=c.get(post["status_url"]+"/manifest").json()
    assert [x["sha256"] for x in result["panels"]]==[x["sha256"] for x in initial["panels"]]
    assert result["reused"] and result["wav_sha256"]!=initial["wav_sha256"]
    cuts=[[i["frame"] for i in m["beats"]] for m in (initial,result)]
    assert cuts[0]!=cuts[1]
    video=c.get(post["video_url"])
    video.raise_for_status()
    (dest/"second-voice.mp4").write_bytes(video.content)
    (dest/"comparison.json").write_text(json.dumps({"per_voice_cuts":cuts,
        "narrators":[initial["voice_profile"],result["voice_profile"]],
        "identical_panel_sha256":[x["sha256"] for x in initial["panels"]],
        "seconds":[m["verification"]["ffprobe"]["format"]["duration"] for m in (initial,result)]},indent=2))
