"""Sample-clock timeline; spoken tokens and display labels are separate."""
import re
from decimal import Decimal, ROUND_HALF_UP


def tokens(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.replace("’", "'").lower())


def sample(time, rate=48000):
    return int((Decimal(str(time)) * rate).to_integral_value(rounding=ROUND_HALF_UP))


def start_frame(samples, fps, rate=48000):
    return (samples * fps + rate // 2) // rate


def end_frame(samples, fps, rate=48000):
    return (samples * fps + rate - 1) // rate


class TimingReview(ValueError):
    pass


def bind(script, aligned):
    """Map ordered engine words to approved utterances, retaining exact ranges."""
    word_tokens, indexes = [], []
    for i, entry in enumerate(aligned):
        ts = tokens(entry["word"])
        word_tokens.extend(ts)
        indexes.extend([i] * len(ts))
    expected = [t for u in script for t in tokens(u["text"])]
    if word_tokens != expected:
        raise TimingReview(f"alignment token mismatch: expected {expected}, observed {word_tokens}")
    bound = {}
    pos = 0
    for u in script:
        words = tokens(u["text"])
        bound[u["id"]] = (words, [aligned[indexes[j]] for j in range(pos, pos + len(words))])
        pos += len(words)
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
    return sample(alignment[idx][edge]) + cue.get("offset_ms", 0) * 48


def corroborate_cue(cue, bound, asr, tolerance=.65):
    """Independent lexical check near each forced onset, not a confidence score."""
    raw = {**cue, "edge": "start", "offset_ms": 0}
    onset = cue_sample(raw, bound) / 48000
    aliases = {**dict(zip("zero one two three four five six seven eight nine".split(), "0123456789")),
               "cm": "centimeters", "km": "kilometers"}
    phrase = [aliases.get(t, t) for t in tokens(cue["phrase"])]
    spoken = [(aliases.get(t, t), w) for w in asr for t in tokens(w["word"])]
    nearby = [[a for a, _ in spoken[i:i + len(phrase)]] for i, (_, w) in enumerate(spoken)
              if abs(w["start"] - onset) <= tolerance]
    if phrase not in nearby:
        raise TimingReview(f"independent transcript does not corroborate cue {cue['phrase']!r} near {onset:.2f}s")
    return {"forced_onset": onset, "transcript_match_within_seconds": tolerance}
