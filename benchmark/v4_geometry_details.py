"""Author-controlled illustrations for the difficult part/action fixtures.

Coordinates here describe drawn elements of a diagram, not predicted
coordinates of parts on a diffusion image.
"""


def shape(vertices,ink,fact=None):
    return {"type":"shape","shape":"polygon","vertices":vertices,"ink":ink,**({"fact":fact} if fact else {})}


def oval(x,y,w,h,ink,fact=None):
    return {"type":"shape","shape":"disc","at":[x,y],"extent":[w,h],"ink":ink,**({"fact":fact} if fact else {})}


def rect(x1,y1,x2,y2,ink,fact=None):
    return shape([[x1,y1],[x2,y1],[x2,y2],[x1,y2]],ink,fact)


def line(x,y,w,z,ink="ink"):
    return {"type":"segment","from":[x,y],"to":[w,z],"ink":ink}


def label(text,x,y,role="support"):
    return {"type":"text","text":text,"at":[x,y],"role":role}


def arrow(x,y,u,v,box,rgb):
    return {"type":"arrow","from":[x,y],"to":[u,v],"target_region":box,"target_rgb":rgb}


def basket():
    setup=[shape([[.48,.48],[.91,.48],[.83,.71],[.57,.71]],"accent"),
           oval(.70,.485,.42,.14,"pale"),oval(.70,.484,.32,.101,"ink","basket-opening"),
           oval(.23,.31,.16,.11,"accent","apple"),oval(.235,.63,.16,.15,"pale","pear"),
           shape([[.205,.267],[.25,.246],[.28,.262],[.25,.277]],"ink")]
    setup+=[line(.579,y,.824,y,"pale") for y in (.56,.613,.657)]
    setup+=[line(x,.58,x+.024,.68) for x in (.60,.66,.72,.78)]
    setup+=[label("APPLE",.23,.40),label("PEAR",.24,.738),label("BASKET",.70,.767)]
    return setup,setup+[arrow(.29,.34,.696,.483,[.59,.441,.81,.521],[72,37,54])], "INSIDE THE OPENING",(
        "FOLLOW THE APPLE", "An apple and a pear sit beside an open basket.","Where should the apple go?",
        "Follow the arrow from the apple into the dark oval.","The apple goes into the basket opening.")


def knot():
    setup=[]
    for x,c,key in ((.28,"pale","left-bag"),(.72,"accent","right-bag")):
        setup.append(shape([[x-.17,.43],[x+.17,.43],[x+.14,.73],[x-.14,.73]],c,key))
        setup.append(rect(x+.055,.495,x+.128,.597,"pale" if c=="accent" else "accent"))
        setup += [shape([[x-.14,.36],[x-.13,.46],[x-.022,.422]],"accent" if x<.5 else "ink"),
                  shape([[x+.14,.36],[x+.13,.46],[x+.022,.422]],"accent" if x<.5 else "ink")]
        setup.append(rect(x-.022,.399,x+.022,.446,"ink" if x<.5 else "accent",f"{key}-knot"))
    setup += [line(.18,.39,.24,.407,"pale"),line(.18,.423,.244,.43,"pale")]
    # Bag bodies are deliberately covered by the tags and knots.
    for s in setup:
        if s.get("fact") in ("left-bag","right-bag"):
            s.pop("fact")
    return setup,setup+[arrow(.40,.28,.279,.422,[.258,.399,.302,.446],[72,37,54])],"KNOT · NOT THE TAG",(
        "FIND THE PART","Two ribbons hold tags. The left ribbon has stripes.","Where is the knot on the striped ribbon?",
        "Look between the two ribbon loops.","The arrow marks the center knot, not the tag.")


def book():
    binding=rect(.223,.25,.258,.66,"accent","binding")
    a=[rect(.225,.25,.75,.66,"ink"),binding,label("FRONT COVER",.53,.721)]
    # Three faces from known projected coordinates. The cover tapers to the
    # right, with spine and page block separate in the new projection.
    b=[shape([[.22,.32],[.57,.22],[.57,.62],[.22,.72]],"ink"),
       shape([[.22,.32],[.247,.337],[.247,.714],[.22,.72]],"accent"),
       shape([[.57,.22],[.68,.28],[.68,.64],[.57,.62]],"pale"),
       arrow(.121,.44,.234,.49,[.222,.355,.246,.683],[191,77,49])]
    return a,b,"BOUND EDGE = SPINE",(
        "FIND THE BINDING","The spine is the edge that binds a book's pages.","Can you find the same part after the book turns?",
        "The cover turns away and the light page block becomes visible.","The arrow points to the same spine, not the pages.")


def cups():
    def mug(x,y,s,striped):
        items=[rect(x-.072*s,y-.062*s,x+.068*s,y+.075*s,"pale"),
               oval(x+.081*s,y,.094*s,.085*s,"ink"),
               oval(x+.084*s,y,.045*s,.048*s,"pale"),
               rect(x-.072*s,y-.062*s,x+.068*s,y+.075*s,"pale")]
        if striped:
            items += [rect(x+.066*s,y+.030*s,x+.093*s,y+.047*s,"accent"),
                      rect(x+.089*s,y+.016*s,x+.114*s,y+.032*s,"accent")]
        return items
    a=[{**line(.12,.552,.88,.552),"fact":"tray"}]
    for x in (.21,.49,.77):
        a+=mug(x,.46,1,x==.49)
    a += [label("THREE MUGS",.50,.68)]
    # The two neighbors lie outside this crop. The same scale applies to
    # the center cup, its handle, the marks and the distance to the tray.
    b=[line(.05,.6984,.95,.6984)]+mug(.43,.45,2.7,True)
    b+=[arrow(.71,.264,.755,.465,[.736,.400,.768,.493],[72,37,54])]
    return a,b,"SAME STRIPED HANDLE",(
        "FIND THE HANDLE","Three mugs are on a tray. Only the middle handle has colored marks.","Which handle should we follow in the close view?",
        "The crop keeps the same marked mug.","The arrow lands on the dark handle of that same mug.")


def robot():
    def board(x,y,left,face,caption):
        # Three columns and three rows, all equal in screen pixels.
        x1=x+.27;y1=y+.152
        grid=[line(x,y,x1,y),line(x,y1,x1,y1)]
        grid += [line(x+.09*i,y,x+.09*i,y1) for i in range(4)]
        grid += [line(x,y+i*.0506667,x1,y+i*.0506667) for i in (1,2)]
        cx=x+left[0]*.09+.045;cy=y+left[1]*.0506667+.025333
        if face=="up":
            a=[[cx,cy-.014],[cx-.027,cy+.013],[cx+.027,cy+.013]]
        else:
            a=[[cx+.025,cy],[cx-.023,cy-.016],[cx-.023,cy+.016]]
        return grid+[shape(a,"accent","robot-start" if caption=="START FACING UP" else None),
                     label(caption,x+.135,y1+.035)]
    a=board(.365,.335,(1,2),"up","START FACING UP")
    a+=[{**label("FORWARD · RIGHT TURN · FORWARD",.50,.63),"fact":"commands"}]
    b=board(.15,.245,(1,1),"up","1 · MOVED")
    b+=board(.58,.245,(1,1),"right","2 · TURNED")
    b+=board(.365,.575,(2,1),"right","3 · MOVED")
    return a,b,"TWO MOVES · ONE TURN",(
        "A TURN IS NOT A STEP","The robot faces up. Its commands are forward, turn right, then forward.",
        "How many grid spaces does it move?","Compare the robot's tile before and after the turn.",
        "The robot moves two spaces. The turn only changes direction.")


DETAILS={"D21":knot,"D22":basket,"D24":book,"D25":cups,"D40":robot}


def diagram_request(case_id,original_req,original_oracle):
    opening,shown,closing,(headline,intro,question,mechanism,answer)=DETAILS[case_id]()
    fixed=[label(headline,.50,.16,"question")]
    opening=fixed+opening
    # The prediction proof is defined on the opening; the answer's arrow can
    # legitimately overlap a small part that is being pointed at. Its separate
    # own-mask/target-region assertion still has to pass.
    shown=[{k:v for k,v in g.items() if k!="fact"} for g in fixed+shown]
    close=shown+[label(closing,.50,.818 if case_id!="D40" else .831,"value")]
    req={"title":question,"voice_profile":original_req["voice_profile"],
         "visual":{"story_context":"An explicit authored diagram with distinguishable parts.",
                   "visual_signature":"Warm editorial cut-paper illustration with distinct silhouettes; no ornamental text.","graphic_theme":"paper"},
         "script":[{"id":"setup","text":intro},{"id":"question","text":question,"caption":question,"pause_after_ms":1750},
                   {"id":"mechanism","text":mechanism,"caption":""},{"id":"answer","text":answer}],
         "instructional":{"question_utterance":"question","answer_beat":"demonstrate","minimum_ms":1180,
                       "required_facts":[g["fact"] for g in opening if "fact" in g] or ["heading"],"region":[.04,.13,.95,.84],
                       "spoken_answer_phrases":[answer]},
         "beats":[]}
    if "heading" in req["instructional"]["required_facts"]:
        fixed[0]["fact"]="heading"
    panels=[("setup",None,{"ms":0},opening),("demonstrate","setup",{"utterance_id":"mechanism","phrase":" ".join(mechanism.split()[:3])},shown),
             ("conclude","demonstrate",{"utterance_id":"answer","phrase":" ".join(answer.split()[:3])},close)]
    for key,parent,cue,overlays in panels:
        req["beats"].append({"id":key,"parent":parent,"cue":cue,
            "panel":{"op":"overlay_only" if parent else "new_scene","paper_scene":not bool(parent),
                     "scene_id":"parts","objective":"Show the exact named part that the viewer is asked about.",
                     "instruction":"Draw only the authored silhouettes and check the visible target, not an approximate neighboring part.","overlays":overlays}})
    oracle={**original_oracle,"stage":[[],[],[]],"art_continuity_requires_review":True,
            "authored_variant":"flat cut-paper exact-part composition; independent visual adjudication required"}
    return req,oracle


def shelf_request(original,oracle):
    opening,reveal,closing = json_clone(original["beats"])
    original=json_clone(original)
    original["visual"]["assets"]={"book":{"kind":"generated_cutout","seed":144,
        "visual":"One upright blue closed book with a plain rectangular cover, isolated on pure white without text.",
        "keep_largest_component":True}}
    original["script"]=[{"id":"setup","text":"Books three and five are on the shelf."},
                         {"id":"question","text":"Which book goes in the middle?","pause_after_ms":1600},
                         {"id":"mechanism","text":"Insert book four, leaving the neighboring books still."},
                         {"id":"answer","text":"The order is three, four, five."}]
    original["instructional"]={"question_utterance":"question","answer_beat":"demonstrate",
         "minimum_ms":1080,"required_facts":["book-3","book-5"],"region":[.08,.12,.92,.80]}
    def layout(values):
        xs={3:.23,4:.50,5:.77}
        return {"layers":[{"id":f"book{v}","asset":"book","center":[xs[v],.45],"width":.15,"max_height":.18} for v in values]}
    def drawings(values):
        return [label("FIND THE MISSING BOOK",.5,.14,"question"),line(.09,.58,.91,.58)]+[
            {**label(str(v),x,.66,"value"),"fact":f"book-{v}"} for v,x in ((3,.23),(4,.5),(5,.77)) if v in values]
    opening["panel"]={"op":"new_scene","scene_id":"shelf","instruction":"Place the two existing books as visible cutouts.",
                      "objective":"Establish books three and five with a clear empty position.",
                      "layout":layout((3,5)),"overlays":drawings((3,5))}
    reveal["panel"]={"op":"layout_transition","scene_id":"shelf","instruction":"Insert the actual new book in the middle.",
                      "objective":"Keep both adjacent books intact.",
                      "layout":layout((3,4,5)),"inserted_instances":["book4"],"overlays":drawings((3,4,5))}
    reveal["cue"]={"utterance_id":"mechanism","phrase":"Insert book four"}
    closing["panel"]={"op":"overlay_only","scene_id":"shelf","instruction":"Keep the shelf.","objective":"Show the complete order.",
                      "overlays":drawings((3,4,5))+[label("THREE, FOUR, FIVE",.50,.78,"value")]}
    closing["cue"]={"utterance_id":"answer","phrase":"The order is"}
    original["beats"]=[opening,reveal,closing]
    return original,{**oracle,"stage":[[],[],[]],"art_continuity_requires_review":True,
                      "authored_variant":"pixel-checked book insertion with fixed neighbors"}


def json_clone(value):
    from copy import deepcopy
    return deepcopy(value)
