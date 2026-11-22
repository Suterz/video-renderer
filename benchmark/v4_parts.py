"""Authored cut-paper part studies for generated-art refusals; not scored."""
import json,sys
from pathlib import Path
import httpx
from v4_controls import send


def polygon(points,ink,fact=None):
    return {"type":"shape","shape":"polygon","vertices":points,"ink":ink,**({"fact":fact} if fact else {})}


def disc(x,y,w,h,ink,fact=None):
    return {"type":"shape","shape":"disc","at":[x,y],"extent":[w,h],"ink":ink,**({"fact":fact} if fact else {})}


def line(a,b,ink="ink"):
    return {"type":"segment","from":a,"to":b,"ink":ink}


def text(value,pos):
    return {"type":"text","text":value,"at":pos,"role":"support"}


def basket():
    # Perspective opening and body are deliberately different visible shapes.
    a=[polygon([[.50,.49],[.90,.49],[.83,.72],[.58,.72]],"accent"),
       disc(.70,.49,.42,.145,"pale"),disc(.70,.488,.33,.105,"ink","opening"),
       disc(.22,.31,.16,.105,"accent","apple"),
       polygon([[.19,.276],[.23,.249],[.28,.263],[.235,.279]],"ink"),
       disc(.23,.63,.15,.15,"pale","pear")]
    a += [line([.553,y],[.861,y]) for y in (.568,.624,.676)]
    a += [line([x,.58],[x+.026,.69]) for x in (.585,.64,.69,.74,.79)]
    a+= [text("APPLE",[.22,.40]),text("PEAR",[.23,.739]),text("BASKET",[.70,.759])]
    overlays={"type":"arrow","from":[.29,.337],"to":[.69,.478],"target_region":[.582,.454,.827,.517],
              "target_rgb":[72,37,54]}
    return a,overlays,"Where does the apple go?","The apple can go inside the dark opening.","INSIDE THE OPENING"


def zipper():
    a=[polygon([[.18,.26],[.31,.22],[.49,.47],[.49,.73],[.23,.73]],"ink","left-fabric"),
       polygon([[.82,.26],[.69,.22],[.51,.47],[.51,.73],[.77,.73]],"ink","right-fabric")]
    for k in range(7):
        y=.28+k*.025
        x=.326+k*.022
        a += [line([x,y],[x+.035,y-.006],"pale"),line([1-x,y],[1-x-.035,y-.006],"pale")]
    a += [polygon([[.453,.431],[.547,.431],[.565,.493],[.435,.493]],"accent","slider"),
          polygon([[.477,.504],[.523,.504],[.54,.62],[.46,.62]],"pale","pull"),
          text("TWO DIFFERENT PARTS",[.5,.772])]
    overlay={"type":"arrow","from":[.81,.41],"to":[.50,.462],"target_region":[.455,.434,.545,.49],"target_rgb":[191,77,49]}
    return a,overlay,"Which part joins the two rows of teeth?","The short upper slider joins the teeth.","SLIDER · NOT THE PULL"


api,out=sys.argv[1:]
with httpx.Client(base_url=api,timeout=30) as h:
    for make in (basket,zipper):
        paper,arrow,question,answer,tag=make()
        emb=[g["fact"] for g in paper if "fact" in g]
        key=make.__name__
        req={"title":question,"voice_profile":"heart","visual":{"story_context":"Exact labeled illustration, original cut-paper style.",
              "visual_signature":"Flat warm cut-paper shapes with dark ink and red edges.","graphic_theme":"paper"},
             "script":[{"id":"intro","text":"Look closely at the drawing."},{"id":"q","text":question,"pause_after_ms":1600},
                       {"id":"a","text":answer}],
             "instructional":{"question_utterance":"q","answer_beat":"answer","required_facts":emb,
                 "minimum_ms":1050,"region":[.10,.22,.93,.79],"spoken_answer_phrases":[answer]},
             "beats":[{"id":"opening","cue":{"ms":0},"panel":{"op":"new_scene","paper_scene":True,"scene_id":key,
                    "objective":"The visually distinct objects are the givens.","instruction":"Present the exact parts.","overlays":paper}},
                  {"id":"answer","parent":"opening","cue":{"utterance_id":"a","phrase":" ".join(answer.split()[:3])},
                   "panel":{"op":"overlay_only","scene_id":key,"instruction":"Mark the specific visible part.","objective":answer,
                            "overlays":paper+[arrow,text(tag,[.50,.818])]}}]}
        folder=Path(out)/key
        result=send(h,"/v2/renders",req,folder)
        (folder/"status.json").write_text(json.dumps(result,indent=2))
        if result["state"]=="succeeded":
            (folder/"video.mp4").write_bytes(h.get(result["video_url"]).content)
            (folder/"manifest.json").write_bytes(h.get(result["status_url"]+"/manifest").content)
        print(key,result["state"],result.get("error"),flush=True)
