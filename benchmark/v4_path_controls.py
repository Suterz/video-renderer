"""Public API controls: a two-switch circuit and a walkable path on a map."""
from copy import deepcopy
import argparse
import json
from pathlib import Path

import httpx

from v4_controls import send


def claim(x1, x2, y, connected, rgb):
    return {"region": [.1, y-.075, .9, y+.075], "start": [x1,y], "end": [x2,y],
            "rgb": rgb, "connected": connected}


def line(a, b, ink="ink"):
    return {"type": "segment", "from": a, "to": b, "ink": ink}


def label(text, x, y, fact=None):
    return {"type": "text", "text": text, "at": [x,y], "role": "support",
            **({"fact": fact} if fact else {})}


def disc(x,y):
    return {"type":"shape","shape":"disc","at":[x,y],"extent":[.022,.0124],"ink":"ink"}


def circuit(root):
    req = json.loads((root / "geometry/results/D20/request.json").read_text())
    ink = [23,53,85]
    for i, beat in enumerate(req["beats"]):
        p = beat["panel"]
        overlays = p["overlays"]
        # Distinct contact dots and lever, instead of unlabeled dangling stubs.
        stubs = (([.25,.42],[.25,.37]),([.39,.42],[.39,.37]),([.76,.41],[.77,.37]))
        overlays[:] = [o for o in overlays if (o.get("from"),o.get("to")) not in stubs]
        overlays.extend(disc(x,.37) for x in (.25,.39,.61,.77))
        p["path_claims"] = [claim(.20,.50,.37,True,ink),claim(.48,.82,.37,i>0,ink)]
    negative = deepcopy(req)
    negative["beats"][1]["panel"]["overlays"] = [
        o for o in negative["beats"][1]["panel"]["overlays"]
        if (o.get("from"),o.get("to")) != ([.61,.37],[.77,.37])]
    return req, negative


def trail():
    # The sign is not the evidence: the reveal must bridge the actual gap.
    y=.44
    a,b,c,d = ([x,y] for x in (.18,.41,.59,.82))
    path = [line(a,b), line(c,d), label("CABIN",.2,.34), label("LOOKOUT",.8,.34),
            {**line([.49,.31],[.49,.59],"pale"),"fact":"river"}]
    intro = path + [label("TRAIL STOPS AT THE RIVER",.5,.62,"gap")]
    reveal = path + [line(b,c), label("BRIDGE JOINS THE TRAIL",.5,.62)]
    ink = [23,53,85]
    req = {"title":"Reach the lookout", "voice_profile":"heart",
           "visual":{"story_context":"An exact path on a small trail map.",
                     "visual_signature":"Minimal clean trail diagram.","graphic_theme":"atlas"},
           "script":[{"id":"intro","text":"The cabin trail stops at a river."},
                     {"id":"q","text":"Can you follow it to the lookout yet?","pause_after_ms":1700},
                     {"id":"a","text":"The bridge joins the two sides."}],
           "instructional":{"question_utterance":"q","answer_beat":"answer",
                            "minimum_ms":1100,"region":[.1,.2,.9,.76],"required_facts":["river","gap"]},
           "beats":[{"id":"opening","cue":{"ms":0},"panel":{"op":"new_scene","paper_scene":True,
                     "scene_id":"trail","objective":"Show the gap.","instruction":"Draw both disconnected sides.",
                     "overlays":intro,"path_claims":[claim(.2,.8,y,False,ink)]}},
                    {"id":"answer","parent":"opening","cue":{"utterance_id":"a","phrase":"The bridge joins"},
                     "panel":{"op":"overlay_only","scene_id":"trail","objective":"Show a continuous crossing.",
                     "instruction":"Connect the two sides visibly.","overlays":reveal,
                     "path_claims":[claim(.2,.8,y,True,ink)]}}]}
    # Keep the river under the bridge in the reveal rather than painting over it.
    req["beats"][1]["panel"]["overlays"] = [path[4],*path[:4],line(b,c),reveal[-1]]
    negative = deepcopy(req)
    negative["beats"][1]["panel"]["overlays"].remove(line(b,c))
    return req, negative


def main():
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("root", type=Path)
    p.add_argument("out", type=Path)
    a = p.parse_args()
    with httpx.Client(base_url=a.url,timeout=30) as client:
        for name, pair in (("circuit",circuit(a.root)),("trail",trail())):
            for correct, req in zip((True,False),pair,strict=True):
                folder = a.out / (name + ("-correct" if correct else "-wrong"))
                status = send(client,"/v2/renders",req,folder)
                (folder/"status.json").write_text(json.dumps(status,indent=2)+"\n")
                if status["state"]=="succeeded":
                    for url,filename in ((status["video_url"],"video.mp4"),
                                         (status["status_url"]+"/manifest","manifest.json")):
                        response=client.get(url)
                        response.raise_for_status()
                        (folder/filename).write_bytes(response.content)
                print(folder.name,status["state"],status.get("error"),flush=True)
                if correct:
                    assert status["state"]=="succeeded",status
                else:
                    assert status["state"]=="needs_review" and "phone-size path is broken" in status["error"],status


if __name__ == "__main__":
    main()
