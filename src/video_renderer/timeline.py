"""Sample-clock timeline; spoken tokens and display labels are separate."""
import re
from decimal import Decimal, ROUND_HALF_UP


def normalize_written_terms(text):
    text = text.replace("’", "'").lower()
    text = re.sub(r"(?<![\w,])\d{1,3}(?:,\d{3})+(?![\d,])", lambda m: m[0].replace(",", ""), text)
    return re.sub(r"\bgpt[- ](\d)(?:[.-](\d))?\b", lambda m: "gpt" + m[1] + (m[2] or ""), text)


def tokens(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", normalize_written_terms(text))


def speech_terms(words):
    """Normalize equivalent ASR spellings without merging different values."""
    return [term for term,_ in normalized_terms(words)]


def normalized_terms(words):
    """Yield normalized terms with first word index for timing evidence."""
    names = ("zero one two three four five six seven eight nine ten eleven twelve "
             "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
    aliases = {**{name: str(index) for index,name in enumerate(names)},
               "cm": "centimeters", "centimeter": "centimeters", "km": "kilometers", "kilometer": "kilometers"}
    tens=dict(zip("twenty thirty forty fifty sixty seventy eighty ninety".split(),range(20,100,10),strict=True))
    narrow=set(names[1:10])
    i=0
    while i<len(words):
        t=words[i]
        if t in tens and i+1<len(words) and words[i+1] in narrow:
            yield str(tens[t]+int(aliases[words[i+1]])),i
            i+=2
        else:
            yield str(tens[t]) if t in tens else aliases.get(t,t),i
            i+=1


def sample(time, rate=48000):
    return int((Decimal(str(time)) * rate).to_integral_value(rounding=ROUND_HALF_UP))


def start_frame(samples, fps, rate=48000):
    return (samples * fps + rate // 2) // rate


def end_frame(samples, fps, rate=48000):
    return (samples * fps + rate - 1) // rate


class TimingReview(ValueError):
    pass


def possessive_form(word):
    # Only an orthographic apostrophe before terminal s. No plural deletion.
    return word[:-2]+"s" if word.endswith("'s") else word


APOSTROPHE_DROPS = {"you'll", "they'll", "it'll", "didn't", "doesn't", "isn't", "aren't", "wasn't",
                    "hasn't", "won't", "they've", "you've", "we've", "you're", "they're",
                    "don't", "couldn't", "wouldn't", "shouldn't", "hadn't", "weren't"}


def fused_form(word):
    return word.replace("'", "") if word in APOSTROPHE_DROPS else possessive_form(word)


def aligned_word_matches(spoken, aligned):
    if possessive_form(spoken) == possessive_form(aligned):
        return True
    # The forced aligner can drop an internal apostrophe on these words.
    # Do not conflate real different words such as we'll/well or I'll/ill.
    return spoken in APOSTROPHE_DROPS and aligned == fused_form(spoken)


def clock_fusion(a,b):
    return (a in {"twenty","thirty","forty","fifty","oh"} and
            b in {"one","two","three","four","five","six","seven","eight","nine"})


def corroborated_spelling(wanted, measured, span, asr):
    if aligned_word_matches(wanted, measured):
        return True
    if not asr or wanted not in {"we're", "we'll", "can't", "i'll"} or measured != wanted.replace("'", ""):
        return False
    return any(wanted in tokens(word["word"]) and abs(word["start"] - span["start"]) <= .40 for word in asr)


def bind(script, aligned, asr=None):
    """Map ordered engine words to approved utterances, retaining exact ranges."""
    word_tokens, indexes = [], []
    for i, entry in enumerate(aligned):
        ts = tokens(entry["word"])
        word_tokens.extend(ts)
        indexes.extend([i] * len(ts))
    bound = {}
    pos = 0
    for u in script:
        words, spans = [], []
        groups=re.findall(r"[a-z0-9]+(?:'[a-z]+)?(?:[-‐‑—–][a-z0-9]+(?:'[a-z]+)?)*",
                          normalize_written_terms(u["text"]))
        i=0
        while i<len(groups):
            parts=tokens(groups[i])
            if (i+1<len(groups) and clock_fusion(groups[i],groups[i+1])
                    and word_tokens[pos:pos+1]==[groups[i]+groups[i+1]]):
                parts.append(groups[i+1]); i+=1
            i+=1
            words.extend(parts)
            observed = word_tokens[pos:pos+len(parts)]
            if len(observed) == len(parts) and all(
                    corroborated_spelling(a, b, aligned[indexes[pos+j]], asr)
                    for j, (a, b) in enumerate(zip(parts, observed))):
                spans.extend(aligned[indexes[j]] for j in range(pos,pos+len(parts)))
                pos+=len(parts)
            elif len(parts)>1 and word_tokens[pos:pos+1] in (
                    ["".join(parts)], ["".join(fused_form(p) for p in parts)]):
                outer=aligned[indexes[pos]]
                spans.extend({**outer,"internal_start":i>0,"internal_end":i<len(parts)-1}
                             for i in range(len(parts)))
                pos+=1
            else:
                raise TimingReview(f"alignment token mismatch in {u['id']}: expected {parts!r}, observed {word_tokens[pos:pos+len(parts)]!r}")
        bound[u["id"]] = (words,spans)
    if pos!=len(word_tokens):
        raise TimingReview("alignment token mismatch: extra trailing tokens")
    return bound


def cue_sample(cue, bound):
    if "ms" in cue:
        return cue["ms"] * 48
    text, alignment = bound[cue["utterance_id"]]
    phrase = tokens(cue["phrase"])
    if not phrase:
        raise TimingReview("empty cue phrase")
    matches = [i for i in range(len(text)) if text[i:i + len(phrase)] == phrase]
    occurrence = cue.get("occurrence")
    if (occurrence is None and len(matches) != 1) or (occurrence is not None and not 1 <= occurrence <= len(matches)):
        raise TimingReview(f"{cue['utterance_id']}: phrase {cue['phrase']!r} matched {len(matches)} times at {matches}; provide a valid occurrence")
    i = matches[(occurrence or 1) - 1]
    edge = cue.get("edge", "start")
    idx = i if edge == "start" else i + len(phrase) - 1
    if alignment[idx].get(f"internal_{edge}"):
        raise TimingReview("cue uses an internal boundary of a fused alignment token")
    return sample(alignment[idx][edge]) + cue.get("offset_ms", 0) * 48


def corroborate_cue(cue, bound, asr, tolerance=.65):
    """Independent lexical check near each forced onset, not a confidence score."""
    raw = {**cue, "edge": "start", "offset_ms": 0}
    onset = cue_sample(raw, bound) / 48000
    phrase = speech_terms([possessive_form(t) for t in tokens(cue["phrase"])])
    raw_words=[(possessive_form(t),w) for w in asr for t in tokens(w["word"])]
    spoken=[(t,raw_words[i][1]) for t,i in normalized_terms([v for v,_ in raw_words])]
    # Independent ASR can write “8×10” as one word span.
    # This alternative is limited to x between exact numeric values.
    written=[]
    for w in asr:
        raw_text=re.sub(r"(?<=\d)\s*[×x]\s*(?=\d)"," by ",w["word"],flags=re.I)
        written.extend((possessive_form(t),w) for t in tokens(raw_text))
    graphic=[(t,written[i][1]) for t,i in normalized_terms([v for v,_ in written])]
    # ASR sometimes assigns the initial word the outgoing silence as well.
    # Require the *same phrase*, but allow the forced onset anywhere inside
    # that bounded ASR span instead of demanding agreement on its left edge.
    nearby = [[a for a, _ in sequence[i:i + len(phrase)]] for sequence in (spoken,graphic) for i, (_, w) in enumerate(sequence)
              if abs(w["start"] - onset) <= tolerance or
              (w["start"] <= onset <= w.get("end",w["start"]) and w.get("end",w["start"])-w["start"]<=1.2)]
    if phrase not in nearby:
        raise TimingReview(f"independent transcript does not corroborate cue {cue['phrase']!r} near {onset:.2f}s")
    return {"forced_onset": onset, "transcript_match_within_seconds": tolerance}
