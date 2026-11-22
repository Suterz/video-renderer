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
        "DRAW THE SCENE", "An apple and a pear sit beside an open basket.","Where should the apple go?",
        "Follow the arrow past the pear, toward the dark part.","The apple goes into the basket opening.")


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
    def mug(x,y,s,striped,key):
        items=[rect(x-.072*s,y-.062*s,x+.068*s,y+.075*s,"pale"),
               oval(x+.081*s,y,.094*s,.085*s,"ink",key+"-handle"),
               oval(x+.084*s,y,.045*s,.048*s,"pale"),
               rect(x-.072*s,y-.062*s,x+.068*s,y+.075*s,"pale")]
        if striped:
            items += [rect(x+.066*s,y+.030*s,x+.093*s,y+.047*s,"accent"),
                      rect(x+.089*s,y+.016*s,x+.114*s,y+.032*s,"accent")]
        # The handle is partly occluded by the cup itself and has an aperture;
        # require the actual pointing pixel later, not its entire original fill.
        items[1].pop("fact")
        return items
    a=[]
    for x,key in ((.21,"one"),(.49,"two"),(.77,"three")):
        a+=mug(x,.46,.95,key=="two",key)
    a += [label("SAME TRAY",.50,.68)]
    b=mug(.43,.45,2.35,True,"two")+mug(.83,.45,.8,False,"three")
    b+=[arrow(.68,.264,.716,.465,[.697,.407,.730,.491],[72,37,54])]
    return a,b,"SAME STRIPED HANDLE",(
        "FIND THE HANDLE","Three mugs are on a tray. Only the middle handle has colored marks.","Which handle should we follow in the close view?",
        "The crop keeps the same marked mug.","The arrow lands on the dark handle of that same mug.")


DETAILS={"D21":knot,"D22":basket,"D24":book,"D25":cups}


def diagram_request(case_id,original_req,original_oracle):
    opening,shown,closing,(headline,intro,question,mechanism,answer)=DETAILS[case_id]()
    fixed=[label(headline,.50,.16,"question")]
    opening=fixed+opening
    shown=fixed+shown
    close=shown+[label(closing,.50,.818,"value")]
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
