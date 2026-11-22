"""Controlled additions in two real illustrated episodes."""
from pathlib import Path
import json,sys,httpx
from v4_controls import send

url,root=sys.argv[1:]
with httpx.Client(base_url=url,timeout=30) as h:
    for name,prompt,setup,question,answer in (
        ("book","One simple upright closed royal blue book with a blank plain rectangular cover, isolated on pure white, no markings.",
         "Books three and five are on the shelf.","What belongs in the middle space?","Book four belongs between three and five."),
        ("ticket","One small golden admission ticket, isolated on uniform white, no lettering.",
         "The row has tickets one and three.","Which ticket is missing from the row?","Ticket two goes in the middle space."),
    ):
        low,mid,high=(3,4,5) if name=="book" else (1,2,3)
        def view(with_middle):
            values=[(low,.24),(high,.76)]
            if with_middle:
                values.insert(1,(mid,.5))
            return {
                "layout":{"layers":[{"id":f"item{v}","asset":"item","center":[x,.47],"width":.15,"max_height":.17}
                                    for v,x in values]},
                "overlays":[{"type":"segment","from":[.10,.59],"to":[.90,.59]}]+[
                    {"type":"text","text":str(v),"at":[x,.67],"role":"value","fact":f"number-{v}"} for v,x in values],
            }
        req={"title":f"Put the missing {name} in place","voice_profile":"heart",
             "visual":{"story_context":f"A clear row of numbered {name} illustrations.",
                     "visual_signature":"Warm editorial illustration, simple silhouettes.",
                     "assets":{"item":{"kind":"generated_cutout","visual":prompt,"keep_largest_component":True,"seed":144}}},
             "script":[{"id":"setup","text":setup},{"id":"q","text":question,"pause_after_ms":1700},{"id":"a","text":answer}],
             "instructional":{"question_utterance":"q","answer_beat":"show","required_facts":[f"number-{low}",f"number-{high}"],
                              "minimum_ms":1100,"region":[.06,.25,.94,.79],"spoken_answer_phrases":[answer]},
             "beats":[{"id":"opening","cue":{"ms":0},"panel":{"op":"new_scene","scene_id":"row","objective":setup,
                       "instruction":"Leave the middle space clear for the later explanation.",**view(False)}},
                      {"id":"show","parent":"opening","cue":{"utterance_id":"a","phrase":" ".join(answer.split()[:3])},
                       "panel":{"op":"layout_transition","scene_id":"row","objective":answer,
                                "instruction":"Keep old instances and insert precisely one item.",
                                "inserted_instances":[f"item{mid}"],**view(True)}}]}
        place=Path(root)/name
        result=send(h,"/v2/renders",req,place)
        (place/"status.json").write_text(json.dumps(result,indent=2))
        if result["state"]=="succeeded":
            (place/"video.mp4").write_bytes(h.get(result["video_url"]).content)
            (place/"manifest.json").write_bytes(h.get(result["status_url"]+"/manifest").content)
        print(name,result["state"],result.get("error"),flush=True)
