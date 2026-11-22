"""Paired public-API count controls for marked marbles and occupied seats."""
import json,sys,httpx
from pathlib import Path
from v4_controls import send

url,output=sys.argv[1:]
root=Path(output)
with httpx.Client(base_url=url,timeout=25) as h:
    for topic,amount,cells in (
        ("same-marbles",6,[(x,.42) for x in (.16,.29,.42,.55,.68,.81)]),
        ("occupied-seats",5,[(x,y) for x,y in ((.23,.36),(.5,.36),(.77,.36),(.23,.53),(.5,.53))]),
    ):
        sess=h.post("/v2/sessions",json={"story_context":"Count only the visible active tokens.",
              "visual_signature":"Paper shapes with clear spacing.","graphic_theme":"paper"})
        sess.raise_for_status()
        path=f"/v2/sessions/{sess.json()['session_id']}/panels"
        def disc(pt):
            return {"type":"shape","shape":"disc","at":pt,"extent":[.07,.039],"ink":"accent"}
        correct=[disc([x,y]) for x,y in cells]
        if topic=="occupied-seats":
            correct.append({"type":"text","text":"EMPTY","role":"support","at":[.77,.53]})
        candidate=correct+[disc([.87,.56] if topic=="same-marbles" else [.77,.595])]
        for role,variants in (("negative",[]),("repair",[correct])):
            req={"op":"new_scene","paper_scene":True,"key":role,"scene_id":"count",
                 "objective":"Keep only the correct number of separate tokens visible.",
                 "instruction":"An exact count.","overlays":candidate,"overlay_repairs":variants,"retry_budget":1,
                 "component_claims":[{"region":[.08,.27,.95,.67],"rgb":[191,77,49],"minimum_pixels":65,"expected":amount}]}
            d=root/f"{topic}-{role}"
            result=send(h,path,req,d)
            (d/"status.json").write_text(json.dumps(result,indent=2))
            assert result["state"]==("accepted" if variants else "needs_review"),result
            if variants:
                assert result["summary"]["accepted_attempt"]==1
            for fn in ("composed.png","review.json"):
                (d/fn).write_bytes(h.get(result["artifacts"][fn]).content)
            print(topic,role,result["state"],flush=True)
