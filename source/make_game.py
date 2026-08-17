#!/usr/bin/env python3
"""Emit game.html: a self-contained matching game.

The review deck carries declensions, claims and validation indexes that the
game does not need. This trims to the playable subset so the file stays small.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
deck = json.load(open(os.path.join(HERE, "data/deck.json"), encoding="utf-8"))

by_id = {c["id"]: c for c in deck["words"]}

words = []
for c in deck["words"]:
    if c["role"] != "deck":
        continue
    parts = []
    for p in c["compound"]["parts"]:
        top = p["candidates"][0] if p["candidates"] else None
        parts.append({
            "surface": p["surface"],
            "lemma": top["lemma"] if top else None,
            "de": top["gloss"]["de"] if top and top["gloss"] else None,
            "en": top["gloss"]["en"] if top and top["gloss"] else None,
        })
    deg = None
    if c["wordclass"] == "adj" and c["paradigm"]:
        p = c["paradigm"]
        pick = lambda d: (p[d]["kk"]["nf"]["sg"] or {}).get("form")
        deg = [pick("strong"), pick("comparative"), pick("super_strong")]
        forms = {g: (p["strong"][g]["nf"]["sg"] or {}).get("form")
                 for g in ("kk", "kvk", "hk")}
    words.append({
        "wc": c["wordclass"],
        "deg": deg,
        "forms": forms if c["wordclass"] == "adj" and c["paradigm"] else None,
        "id": c["id"],
        "de": [g["text"] for g in c["glosses"]["de"]],
        "en": [g["text"] for g in c["glosses"]["en"]],
        "g": c["gender_short"],
        "tags": c["tags"],
        "parts": parts,
        "builds": [b for b in c["builds"] if by_id.get(b, {}).get("role") == "deck"],
        "prod": c["productivity"],
        "freq": c["corpus"]["total"],
        "d": c["distractors"],
        "note": c["note"],
        "fam": [{"w": f["word"], "p": f["pos"], "de": f["de"], "en": f["en"],
                 "rel": f["rel"], "mm": f["middle_voice"], "base": f["base"]}
                for f in c["family"]],
        "deriv": c["derivation"],
    })

# Support lemmas that only ever appear inside compounds still need glosses,
# so the breakdown can show what each part means.
support = {c["id"]: {"de": c["glosses"]["de"][0]["text"],
                     "en": c["glosses"]["en"][0]["text"],
                     "prod": c["productivity"],
                     "builds": [b for b in c["builds"]
                                if by_id.get(b, {}).get("role") == "deck"]}
           for c in deck["words"] if c["role"] == "part"}

# Concrete nouns to show adjective agreement against, one bucket per gender,
# so the example sentence is never the same three words twice.
demo = {"m": [], "f": [], "n": []}
for c in deck["words"]:
    # Concrete things only. Random pairing against people or body parts
    # produces phrases like "hvit modir" that read as nonsense.
    ok_tags = {"object", "food", "place", "animal", "nature"}
    if c["role"] == "deck" and c["wordclass"] == "noun" and c["gender_short"] \
            and not c["compound"]["parts"] and (set(c["tags"]) & ok_tags):
        demo[c["gender_short"]].append(
            {"w": c["id"], "de": c["glosses"]["de"][0]["text"],
             "en": c["glosses"]["en"][0]["text"]})

payload = {"version": 1, "words": words, "support": support, "demo": demo}

tpl = open(os.path.join(HERE, "game_template.html"), encoding="utf-8").read()
blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
out = os.path.join(HERE, "game.html")
open(out, "w", encoding="utf-8").write(tpl.replace("__GAME_JSON__", blob))
print("wrote %s (%d KB, %d words, %d support)"
      % (out, os.path.getsize(out) // 1024, len(words), len(support)))
