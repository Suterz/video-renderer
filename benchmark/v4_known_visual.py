"""Retained V3 zipper and reflection negatives, with V4 claims attached."""
from pathlib import Path
import json,sys
import httpx

from v4_controls import send

url, out=sys.argv[1:]
root=Path.home()/"Videos/storyboard-v3/rc-holdout-results"
with httpx.Client(base_url=url,timeout=25) as h:
    for k in ("H05","H09"):
        req=json.loads((root/k/"request.json").read_text())
        if k=="H05":
            for beat in req["beats"][1:]:
                for mark in beat["panel"]["overlays"]:
                    if mark["type"]=="arrow":
                        mark["part_target"]="zipper slider block at the Y junction of the two rows of teeth, not its rectangular pull or ring"
        else:
            req["beats"][1]["panel"]["action_claim"]="The actual child moves toward the mirror and its image moves by the same distance."
        folder=Path(out)/k
        r=send(h,"/v2/renders",req,folder)
        (folder/"status.json").write_text(json.dumps(r,indent=2))
        print(k,r["state"],r.get("error",""),flush=True)
        if r["state"]=="succeeded":
            (folder/"video.mp4").write_bytes(h.get(r["video_url"]).content)
