"""Tekst, faktabokser og tidsplan for «The Order We Were Built»."""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

CHORUS = [
    "This is the order we were built,",
    "layer on layer, silt on silt —",
    "the gradient first, then the ancient core,",
    "then the wheel, then the breath, then so much more.",
    "Dig down through me and you dig through time,",
    "every step a deeper rhyme —",
    "we run it forward, we always will,",
    "in the order, the order we were built.",
]

SECTIONS = {
    "intro": ("Intro", "Four billion years ago", [
        "Before the code, before the cell,",
        "before the first thing learned to swell —",
        "there was a rock, there was a tide,",
        "and a current running deep inside.",
    ], "Before DNA and before cells, alkaline hydrothermal vents held a natural proton (pH) "
       "gradient across thin mineral walls — the same kind of gradient all life still uses."),
    "verse1": ("Verse 1 — The Vent", "The proton gradient", [
        "I am the wheel in the alkaline dark,",
        "a turbine turning on a sunless spark.",
        "No sun reached down, no breath, no name —",
        "just protons falling, and I caught the flame.",
        "The vent made the gradient, the rock made the door,",
        "I drank the difference between sea and pore.",
        "The engine was here before the fire,",
        "the current older than the first desire.",
    ], "ATP synthase is a molecular turbine: protons crossing a membrane spin its rotor to make ATP. "
       "Early life may have used free geochemical gradients before it could pump its own."),
    "chorus1": ("Chorus", "Layer on layer", CHORUS,
                "The hook is the syllabus: proton gradient → glycolysis (the ancient core) → "
                "the Krebs wheel → oxygen breathing — in the order they evolved."),
    "verse2": ("Verse 2 — The Anaerobic Core", "Glycolysis", [
        "Then came the sugar, and a way to break",
        "a little loose change for a living's sake.",
        "Glycolysis — older than the air,",
        "no oxygen needed, I was already there.",
        "Just two coins of ATP — it never needed more,",
        "the oldest recipe still kept on the cell's old floor.",
        "When the breathing fails, when the air runs thin,",
        "the cell still falls back to where it's always been.",
    ], "Glycolysis splits glucose into two pyruvate in the cytoplasm, netting just 2 ATP with no "
       "oxygen at all. A sprinting muscle still falls back on this ancient core."),
    "chorus2": ("Chorus", "Layer on layer", CHORUS[:4],
                "Gradient → glycolysis → Krebs wheel → breath: the oldest pathways sit in the "
                "cytoplasm, the newest deep inside the mitochondrion."),
    "verse3": ("Verse 3 — The Wheel That Ran Backwards", "The Krebs cycle", [
        "There's a wheel in the middle and it spins both ways —",
        "first it turned to build in the carbon-hungry days,",
        "pulling CO₂ down, stitching life from stone,",
        "the reverse of the cycle the textbooks own.",
        "Then the world turned over, and the wheel turned too,",
        "forward now to burn what the backward wheel grew.",
        "Same ancient turns, same ancient art —",
        "once it made the body, now it tears it apart.",
    ], "The Krebs cycle can run in reverse: the reductive TCA cycle fixes CO₂ to build carbon "
       "skeletons. The oxidative, fuel-burning direction came later. Same wheel, opposite purposes."),
    "bridge": ("Bridge — The Poison That Became Power", "Oxygen", [
        "Then the green ones came and they poisoned the sky,",
        "oxygen rising, and the old world cried.",
        "But poison is power if you learn how to fall —",
        "I let the spent electrons drop, and oxygen caught them all.",
        "(Becomes water. Becomes ten times more.)",
        "And the engine that could breathe it? We swallowed it whole —",
        "the guest in the matrix we never let go.",
    ], "~2.4 billion years ago cyanobacteria filled the air with O₂. Oxygen became the final "
       "electron acceptor — ~10× more ATP than glycolysis. An engulfed bacterium became the mitochondrion."),
    "final": ("Chorus — Final", "Four billion years", CHORUS[:5] + [
        "four billion years in a single climb —",
        "take one breath and you run it still,",
        "in the order, the order we were built.",
    ], "Every breath you take runs these pathways in the sequence they appeared across four billion years."),
    "outro": ("Outro", "Turning still", [
        "I was turning before there was breath...",
        "I am turning still.",
    ], "ATP synthase has been turning, essentially unchanged, since before Earth had oxygen in its air."),
}


def n_syll(text):
    return max(1, len(re.findall(r"[aeiouy]+", text.lower())))


def load():
    cfg = json.load(open(os.path.join(HERE, "timing.json")))
    secs, lines = [], []
    sl = cfg["sections"]
    for i, s in enumerate(sl):
        end = sl[i + 1]["start"] if i + 1 < len(sl) else cfg["end"]
        label, era, lyr, fact = SECTIONS[s["key"]]
        if "lines" in s:
            spans = s["lines"]
        else:
            v0, v1 = s["vocal"]
        if "lines" in s:
            pass
        elif "line_starts" in s:
            starts = s["line_starts"] + [v1]
        else:
            w = [n_syll(l) + 3 for l in lyr]
            tot = sum(w); acc = 0; starts = []
            for x in w:
                starts.append(v0 + (v1 - v0) * acc / tot); acc += x
            starts.append(v1)
        if "lines" not in s:
            spans = [(starts[k], starts[k + 1]) for k in range(len(lyr))]
        sec = dict(key=s["key"], label=label, era=era, fact=fact, t0=s["start"], t1=end, lines=[])
        for k, text in enumerate(lyr):
            ln = dict(text=text, t0=spans[k][0], t1=spans[k][1], section=s["key"], idx=k)
            sec["lines"].append(ln); lines.append(ln)
        secs.append(sec)
    return secs, lines, cfg["end"]


SECS, LINES, END = load()
BEATS = json.load(open(os.path.join(HERE, "beats.json")))
