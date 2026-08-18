#!/usr/bin/env python3
"""Build deck.json from data/words.tsv + data/pool.tsv using BIN (`islenska`).

Nouns only. Output is regenerated from scratch each run; human verdicts live
separately in verdicts.jsonl so re-running never destroys review work.

Review model: one card per LEMMA. A lemma's meaning and declension are
reviewed exactly once. A compound card additionally asserts how it splits and
which lemma each fragment comes from, but does not re-litigate those lemmas.
"""
import json
import os
import re
import sys
from collections import defaultdict

from icegrams import Ngrams
from islenska import Bin
from islenska.dawgdictionary import Wordbase

NGRAMS = Ngrams()  # Risamalheild-derived unigram counts, shipped offline


def freq(form):
    """Corpus occurrences of a surface form in the Icelandic Gigaword Corpus."""
    try:
        return NGRAMS.freq(form)
    except Exception:
        return 0

BIN = Bin()
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# Icelandic case order, as taught: nefnifall, tholfall, thagufall, eignarfall.
CASES = ["nf", "þf", "þgf", "ef"]
CASE_IS = {"nf": "NF", "þf": "ÞF", "þgf": "ÞGF", "ef": "EF"}
CASE_NAME = {"nf": "nefnifall", "þf": "þolfall",
             "þgf": "þágufall", "ef": "eignarfall"}
# How likely each slot is to be the linking form of a compound modifier.
# Measured on real compounds: acc.sg leads, then gen.sg, then gen.pl.
# Accusative alone covers only about 60% of cases.
LINK_RANK = ["ÞFET", "EFET", "EFFT", "ÞFFT", "NFET", "NFFT", "ÞGFET", "ÞGFFT"]
SLOT_LABEL = {"NFET": "nf.et", "ÞFET": "þf.et", "ÞGFET": "þgf.et", "EFET": "ef.et",
              "NFFT": "nf.ft", "ÞFFT": "þf.ft", "ÞGFFT": "þgf.ft", "EFFT": "ef.ft"}
POS_LABEL = {"kk": "noun", "kvk": "noun", "hk": "noun",
             "lo": "adj", "so": "verb", "ao": "adv"}
GENDER = {"kk": "m (karlkyn)", "kvk": "f (kvenkyn)", "hk": "n (hvorugkyn)"}
GENDER_SHORT = {"kk": "m", "kvk": "f", "hk": "n"}
NOUN = ("kk", "kvk", "hk")
# BIN register codes worth surfacing; anything else passes through raw.
REGISTER = {"URE": "obsolete", "FORN": "archaic", "SKA": "poetic",
            "GAM": "old", "VILLA": "error", "STAD": "regional"}
DROP_REGISTER = {"URE", "VILLA"}  # obsolete / erroneous: never shown
MARK_RE = re.compile(r"^(NF|ÞF|ÞGF|EF)(ET|FT)(gr)?(\d*)$")
# Adjectives: degree x declension strength x gender x case x number.
# FSB/FVB = positive strong/weak, MST = comparative (weak only),
# ESB/EVB = superlative strong/weak.
ADJ_GENDERS = [("kk", "KK"), ("kvk", "KVK"), ("hk", "HK")]
ADJ_DEGREES = [("strong", "FSB"), ("weak", "FVB"),
               ("comparative", "MST"), ("super_strong", "ESB"), ("super_weak", "EVB")]
ADJ_MARK_RE = re.compile(r"^(FSB|FVB|MST|ESB|EVB)-(KK|KVK|HK)-(NF|ÞF|ÞGF|EF)(ET|FT)(\d*)$")


def head_entry(word, pos=None):
    """Pick the BIN entry for a written lemma.

    Prefer the entry whose own lemma equals the word: without this,
    lookup("lög") returns the entry for "lag" (lög is its plural) and the real
    lemma "lög" (law) is never indexed. An explicit pos from the TSV wins.
    """
    _, entries = BIN.lookup(word)
    if not entries:
        return None
    return sorted(entries, key=lambda e: (
        bool(pos) and e.ofl != pos,
        e.ord != word,
        e.ofl not in NOUN,
        getattr(e, "hluti", "") != "alm",
    ))[0]


def rank_form(k):
    """Sort key separating the standard form from marked variants.

    BIN flags secondary forms three ways: beinkunn 0, a register code in
    bmalsnid, and a digit suffix on the mark (NFFT2). Corpus frequency breaks
    remaining ties. Sorting alphabetically instead is what produced "tannir"
    where the standard plural of tönn is "tennur".
    """
    m = MARK_RE.match(k.mark)
    variant_no = int(m.group(4)) if m and m.group(4) else 0
    return (getattr(k, "beinkunn", 0) != 1, bool(k.bmalsnid),
            variant_no, -freq(k.bmynd), k.bmynd)


def cell(hits):
    """One paradigm cell: the standard form, plus surviving variants, each
    with its corpus count so a disagreement is visible rather than asserted."""
    hits = [h for h in hits if h.bmalsnid not in DROP_REGISTER]
    if not hits:
        return None
    ordered = sorted(hits, key=rank_form)
    primary = ordered[0]
    variants, seen = [], {primary.bmynd}
    for k in ordered[1:]:
        if k.bmynd in seen:
            continue
        seen.add(k.bmynd)
        reg = REGISTER.get(k.bmalsnid, k.bmalsnid) if k.bmalsnid else "variant"
        variants.append({"form": k.bmynd, "register": reg, "freq": freq(k.bmynd)})
    return {"form": primary.bmynd, "freq": freq(primary.bmynd),
            "variants": variants}


def paradigm(lemma, pos):
    """Full noun paradigm in the hestur layout: four cases x
    {singular, plural, singular definite, plural definite}."""
    if pos not in NOUN:
        return None
    entry = head_entry(lemma, pos)
    if entry is None:
        return None
    bid = entry.bin_id
    out = {}
    for c in CASES:
        row = {}
        for num, suffix in (("sg", "ET"), ("pl", "FT")):
            slot = CASE_IS[c] + suffix
            try:
                hits = [h for h in BIN.lookup_variants(entry.ord, pos, (slot,))
                        if h.bin_id == bid]
            except Exception:
                hits = []
            row[num] = cell([h for h in hits if "gr" not in h.mark])
            row[num + "_def"] = cell([h for h in hits if "gr" in h.mark])
        out[c] = row
    return out if any(out[c]["sg"] or out[c]["pl"] for c in CASES) else None


def adj_cell(hits):
    """One adjective cell: standard form plus surviving variants."""
    hits = [h for h in hits if h.bmalsnid not in DROP_REGISTER]
    if not hits:
        return None
    def key(k):
        m = ADJ_MARK_RE.match(k.mark)
        vno = int(m.group(5)) if m and m.group(5) else 0
        return (getattr(k, "beinkunn", 0) != 1, bool(k.bmalsnid),
                vno, -freq(k.bmynd), k.bmynd)
    ordered = sorted(hits, key=key)
    primary = ordered[0]
    variants, seen = [], {primary.bmynd}
    for k in ordered[1:]:
        if k.bmynd in seen:
            continue
        seen.add(k.bmynd)
        variants.append({"form": k.bmynd,
                         "register": REGISTER.get(k.bmalsnid, k.bmalsnid) or "variant",
                         "freq": freq(k.bmynd)})
    return {"form": primary.bmynd, "freq": freq(primary.bmynd), "variants": variants}


def adj_paradigm(lemma):
    """Adjective forms grouped degree -> gender -> case -> number.

    Indeclinable adjectives (einmana) legitimately return almost nothing;
    that shows up as a low-coverage flag rather than an error.
    """
    entry = head_entry(lemma, "lo")
    if entry is None:
        return None
    bid = entry.bin_id
    out, filled = {}, 0
    for dname, dcode in ADJ_DEGREES:
        block = {}
        for gname, gcode in ADJ_GENDERS:
            rows = {}
            for c in CASES:
                row = {}
                for num, suf in (("sg", "ET"), ("pl", "FT")):
                    mark = "%s-%s-%s%s" % (dcode, gcode, CASE_IS[c], suf)
                    try:
                        hits = [h for h in BIN.lookup_variants(entry.ord, "lo", (mark,))
                                if h.bin_id == bid]
                    except Exception:
                        hits = []
                    row[num] = adj_cell(hits)
                    if row[num]:
                        filled += 1
                rows[c] = row
            block[gname] = rows
        out[dname] = block
    if not filled:
        return None
    out["_filled"] = filled
    return out


def all_forms(lemma, pos):
    """surface form -> [link slots], indefinite forms only."""
    out = defaultdict(list)
    for slot in LINK_RANK:
        try:
            hits = BIN.lookup_variants(lemma, pos, (slot,))
        except Exception:
            continue
        for h in hits:
            if "gr" in h.mark:
                continue
            out[h.bmynd].append(slot)
    return out


# -legur, -aður etc. are derivational suffixes, not words. Splitting duglegur
# into dug + legur is technically what the DAWG finds but is not a compound.
SUFFIX_BLOCK = {"legur", "leg", "legt", "lega", "aður", "uður", "óttur",
                "samur", "vænn", "laus", "fullur"}
# These are derivational suffixes, not words. Splitting them off as compound
# parts is wrong, but naming them is genuinely useful: -legur is English -ly.
SUFFIX_GLOSS = {
    "legur": "-legur / -leg / -legt turns a noun into an adjective, "
             "like English -ly or German -lich",
    "óttur": "-óttur means shaped like or covered in",
    "laus": "-laus means without, like English -less",
    "fullur": "-fullur means full of",
    "samur": "-samur means inclined to",
    "aður": "-aður forms an adjective from a noun, like English -ed",
}


def derivation(word):
    """If the word ends in a derivational suffix over a real stem, describe it."""
    for suf in sorted(SUFFIX_GLOSS, key=len, reverse=True):
        if not word.endswith(suf) or len(word) - len(suf) < 2:
            continue
        stem = word[: -len(suf)]
        for cand in (stem, stem + "ur", stem + "i", stem + "a", stem + "ur"):
            e = head_entry(cand)
            if e and e.ord == cand and e.ofl in NOUN + ("lo",):
                return {"stem": cand, "suffix": suf, "note": SUFFIX_GLOSS[suf]}
        return {"stem": None, "suffix": suf, "note": SUFFIX_GLOSS[suf]}
    return None


def parse_split_override(spec):
    """`split` column: empty = automatic, `none` = force simplex,
    `hring=hringur laga=-` = these fragments, with an explicit lemma each
    (`-` meaning deliberately unresolved)."""
    spec = (spec or "").strip()
    if not spec:
        return None
    if spec.lower() == "none":
        return []
    out = []
    for tok in spec.split():
        if "=" in tok:
            frag, lemma = tok.split("=", 1)
        else:
            frag, lemma = tok, ""
        # `-` means deliberately not a word: a derivational suffix such as
        # -laga. It must not fall through to the resolver, which would happily
        # match it against some unrelated lemma.
        out.append((frag, lemma if lemma and lemma != "-" else None, True))
    return out


def split_compound(word):
    """BIN-backed segmentation. min_word is lowered from the library default
    of 8, a typographic guard that would skip short compounds like hugmynd."""
    seg = Wordbase.insert_soft_hyphens(word, mode="natural", min_word=4,
                                       min_left=2, min_right=2, hyphen="-")
    parts = [p for p in seg.split("-") if p]
    if len(parts) < 2 or parts[-1] in SUFFIX_BLOCK:
        return []
    return parts


def umlaut_variants(frag):
    """u-umlaut froze old stems into compounds: hand- (hönd), tann- (tönn).
    Reverse the vowel alternation and re-check BIN."""
    seeds = set()
    for i, ch in enumerate(frag):
        if ch == "a":
            seeds.add(frag[:i] + "ö" + frag[i + 1:])
            seeds.add(frag[:i] + "e" + frag[i + 1:])
        elif ch == "o":
            seeds.add(frag[:i] + "ö" + frag[i + 1:])
        elif ch == "u":
            seeds.add(frag[:i] + "y" + frag[i + 1:])
    out = []
    for seed in sorted(seeds):
        for suf in ("", "ur", "r", "i", "a", "n", "ll", "nn", "l", "ð"):
            e = head_entry(seed + suf)
            if e and e.ord == seed + suf and e.ofl in NOUN:
                out.append((seed + suf, e.ofl))
    return out


def levenshtein(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def similarity(a, b):
    m = max(len(a), len(b))
    return 1 - levenshtein(a, b) / m if m else 0


def load_tsv(name):
    rows = []
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            if line.strip():
                rows.append(dict(zip(header, line.rstrip("\n").split("\t"))))
    return rows


def weighted(raw):
    return [{"text": t.strip(), "weight": round(1.0 - 0.25 * i, 2)}
            for i, t in enumerate((raw or "").split("|")) if t.strip()]


def main():
    deck_rows = load_tsv("words.tsv")
    pool_rows = load_tsv("pool.tsv")
    adj_rows = load_tsv("adjectives.tsv") if os.path.exists(
        os.path.join(DATA, "adjectives.tsv")) else []
    fam_rows = load_tsv("family.tsv") if os.path.exists(
        os.path.join(DATA, "family.tsv")) else []
    family = defaultdict(list)
    missing = []
    for r in fam_rows:
        w = r["related"]
        e = head_entry(w, r["pos"] or None)
        base, mm = None, False
        if e is None:
            missing.append("%s->%s (not in BIN at all)" % (r["lemma"], w))
        elif e.ord != w:
            # Middle-voice verbs (hræðast, þreytast) are filed under the active
            # lemma. That is not an error: -st is the miðmynd ending, which
            # usually means "to become X" or is reflexive. Worth teaching.
            _, forms = BIN.lookup(w)
            mm = any("MM" in f.mark for f in forms)
            base = e.ord
            if not mm:
                missing.append("%s->%s (resolves to %s)" % (r["lemma"], w, e.ord))
        family[r["lemma"]].append({
            "word": w, "pos": POS_LABEL.get(r["pos"], r["pos"]),
            "gender": GENDER_SHORT.get(r["pos"]),
            "de": r["de"], "en": r["en"], "rel": r["rel"],
            "in_bin": e is not None, "base": base, "middle_voice": mm,
            "freq": freq(w),
        })
    # Adjectives promoted to their own deck are no longer support-only entries.
    adj_ids = {r["icelandic"] for r in adj_rows}
    pool_rows = [r for r in pool_rows if r["icelandic"] not in adj_ids]
    rows = [dict(r, role="deck", wc="noun") for r in deck_rows] + \
           [dict(r, role="deck", wc="adj", pos="lo") for r in adj_rows] + \
           [dict(r, role="part", wc="noun") for r in pool_rows]

    gloss = {r["icelandic"]: {"de": weighted(r["de"]), "en": weighted(r["en"])}
             for r in rows}
    pinned = {r["icelandic"]: (r.get("pos") or None) for r in rows}

    sys.stderr.write("indexing %d lemmas...\n" % len(rows))
    index = defaultdict(list)
    pos_of = {}
    for r in rows:
        lemma = r["icelandic"]
        e = head_entry(lemma, pinned.get(lemma))
        if e is None:
            continue
        pos_of[lemma] = e.ofl
        for form, slots in all_forms(e.ord, e.ofl).items():
            index[form].append((lemma, e.ofl, slots))
    sys.stderr.write("%d surface forms indexed\n" % len(index))

    def resolve(frag):
        out = []
        for lemma, pos, slots in index.get(frag, []):
            best = min((LINK_RANK.index(s) for s in slots), default=99)
            out.append({"lemma": lemma, "pos": POS_LABEL.get(pos, pos),
                        "gender": GENDER_SHORT.get(pos),
                        "slot": SLOT_LABEL.get(LINK_RANK[best]) if best < 99 else "?",
                        "case_name": CASE_NAME.get(
                            SLOT_LABEL[LINK_RANK[best]].split(".")[0]) if best < 99 else None,
                        "via": "form-index",
                        "_r": (0 if lemma == frag else 1, best)})
        if not out:
            for lemma, pos in sorted(umlaut_variants(frag),
                                     key=lambda t: t[0] not in gloss):
                out.append({"lemma": lemma, "pos": POS_LABEL.get(pos, pos),
                            "gender": GENDER_SHORT.get(pos),
                            "slot": "stem", "case_name": None,
                            "via": "umlaut", "_r": (2, 50)})
        out.sort(key=lambda c: c["_r"])
        for c in out:
            c.pop("_r")
            g = gloss.get(c["lemma"])
            c["gloss"] = ({"de": g["de"][0]["text"], "en": g["en"][0]["text"]}
                          if g else None)
            c["has_card"] = c["lemma"] in gloss
        return out

    cards = []
    for r in rows:
        word = r["icelandic"]
        pos = pos_of.get(word)
        is_adj = r.get("wc") == "adj"
        para = adj_paradigm(word) if is_adj else paradigm(word, pos)
        override = parse_split_override(r.get("split"))
        if override is None:
            parts_raw = [(f, None, False) for f in
                         (split_compound(word) if r["role"] == "deck" else [])]
        else:
            joined = "".join(f for f, _, _ in override)
            if joined != word:
                sys.stderr.write("WARNING: split override for %s does not "
                                 "reconstruct the word (%s)\n" % (word, joined))
            parts_raw = override

        parts, off = [], 0
        for frag, forced, is_override in parts_raw:
            if is_override and not forced:
                cands = []          # explicit suffix, no lemma to find
            elif forced:
                # A curator-supplied lemma always wins over the resolver.
                g = gloss.get(forced)
                e = head_entry(forced, pinned.get(forced))
                cands = [{
                    "lemma": forced,
                    "pos": POS_LABEL.get(e.ofl, "?") if e else "?",
                    "gender": GENDER_SHORT.get(e.ofl) if e else None,
                    "slot": "set by hand", "case_name": None, "via": "override",
                    "gloss": ({"de": g["de"][0]["text"], "en": g["en"][0]["text"]}
                              if g else None),
                    "has_card": forced in gloss,
                }]
            else:
                cands = resolve(frag)
            parts.append({"surface": frag, "span": [off, off + len(frag)],
                          "candidates": cands,
                          "suffix": bool(is_override and not forced)})
            off += len(frag)

        de1 = gloss[word]["de"][0]["text"]
        en1 = gloss[word]["en"][0]["text"]
        claims = [{"id": "gloss", "kind": "gloss", "key": "gloss:" + word,
                   "assert": "%s means \u201c%s\u201d / \u201c%s\u201d" % (word, de1, en1)}]
        if para:
            claims.append({"id": "paradigm",
                           "kind": "adjparadigm" if is_adj else "paradigm",
                           "key": "paradigm:" + word,
                           "assert": "declension of %s is correct" % word})
        if family.get(word):
            claims.append({
                "id": "family", "kind": "family", "key": "family:" + word,
                "assert": "%s is related to %s" % (
                    word, ", ".join(f["word"] for f in family[word]))})
        if is_adj and para:
            deg = [para[d]["kk"]["nf"]["sg"] for d in
                   ("strong", "comparative", "super_strong")]
            if all(deg):
                claims.append({"id": "degrees", "kind": "degrees",
                               "key": "degrees:" + word,
                               "assert": "%s, %s, %s" % tuple(x["form"] for x in deg)})
        if parts:
            claims.append({"id": "split", "kind": "split", "key": "split:" + word,
                           "assert": "%s = %s" % (
                               word, " + ".join(p["surface"] for p in parts))})
            for n, p in enumerate(parts):
                top = p["candidates"][0] if p["candidates"] else None
                claims.append({
                    "id": "part%d" % n, "kind": "part", "index": n,
                    "key": "part:%s->%s" % (p["surface"], top["lemma"] if top else "?"),
                    "surface": p["surface"], "resolved": bool(top),
                    "lemma": top["lemma"] if top else None,
                    "slot": top["slot"] if top else None,
                    "case_name": top["case_name"] if top else None,
                    "gender": top["gender"] if top else None,
                    "via": top["via"] if top else None,
                    "gloss": top["gloss"] if top else None,
                    "has_card": top["has_card"] if top else False,
                    "alts": [c["lemma"] for c in p["candidates"][1:4]],
                    "suffix": p.get("suffix", False),
                    "assert": ("%s- comes from %s" % (p["surface"], top["lemma"])
                               if top else
                               "-%s is a suffix, not a word" % p["surface"]
                               if p.get("suffix") else
                               "%s- comes from an unknown lemma" % p["surface"]),
                })

        # Corpus signals. icegrams counts SURFACE FORMS, so a count is an
        # upper bound: "hurdar" is both gen.sg and a plural variant, and its
        # count conflates the two. Treat these as evidence, not verdicts.
        sg_total = pl_total = 0
        weak = []
        if is_adj:
            if para:
                for d in ("strong", "weak", "comparative", "super_strong", "super_weak"):
                    for g, _ in ADJ_GENDERS:
                        for c in CASES:
                            for k in ("sg", "pl"):
                                x = para[d][g][c][k]
                                if x:
                                    if k == "sg":
                                        sg_total += x["freq"]
                                    else:
                                        pl_total += x["freq"]
        elif para:
            for c in CASES:
                for k in ("sg", "sg_def"):
                    if para[c][k]:
                        sg_total += para[c][k]["freq"]
                for k in ("pl", "pl_def"):
                    if para[c][k]:
                        pl_total += para[c][k]["freq"]
            for c in CASES:
                for k in ("sg", "pl", "sg_def", "pl_def"):
                    x = para[c][k]
                    if not x:
                        continue
                    if x["freq"] == 0 and any(v["freq"] > 0 for v in x["variants"]):
                        weak.append("%s.%s" % (c, k))
                    elif any(v["freq"] > x["freq"] for v in x["variants"]):
                        weak.append("%s.%s" % (c, k))
        corpus = {
            "sg_total": sg_total, "pl_total": pl_total,
            "total": sg_total + pl_total,
            "plural_attested": pl_total > 0,
            "floor_note": True,
            "plural_rare": (not is_adj) and bool(sg_total)
                           and pl_total < sg_total * 0.02,
            "outranked": weak,
        }

        unresolved = sum(1 for p in parts
                         if not p["candidates"] and not p.get("suffix"))
        guessed = sum(1 for p in parts if p["candidates"]
                      and p["candidates"][0]["via"] == "umlaut")
        if is_adj:
            variants = 0
            coverage = (para or {}).get("_filled", 0)
        else:
            variants = sum(len(para[c][k]["variants"])
                           for c in (para or {}) for k in para[c]
                           if para[c][k]) if para else 0
            coverage = None
        conf = ("low" if unresolved or guessed or corpus["outranked"] else
                "medium" if variants or corpus["plural_rare"]
                or any(len(p["candidates"]) > 1 for p in parts)
                else "high")

        cards.append({
            "id": word, "lemma": word, "role": r["role"],
            "wordclass": r.get("wc", "noun"), "coverage": coverage,
            "pos": POS_LABEL.get(pos, "?"),
            "gender": GENDER.get(pos), "gender_short": GENDER_SHORT.get(pos),
            "glosses": gloss[word],
            "tags": [t for t in (r.get("tags") or "").split(",") if t],
            "note": (r.get("note") or "").strip() or None,
            "family": family.get(word, []),
            "derivation": derivation(word) if r.get("wc") == "adj" else None,
            "is_noun": pos in NOUN,
            "compound": {"is_compound": bool(parts), "parts": parts},
            "paradigm": para,
            "corpus": corpus,
            "claims": claims,
            "confidence": conf,
        })

    # ---- productivity: how many deck compounds each lemma helps build ----
    builds = defaultdict(set)
    for c in cards:
        # A stem appearing twice in one word (barn in barnabarn) is still one
        # word built, so collect distinct compounds rather than occurrences.
        for p in c["compound"]["parts"]:
            if p["candidates"]:
                builds[p["candidates"][0]["lemma"]].add(c["id"])
    for c in cards:
        c["builds"] = sorted(builds.get(c["id"], []))
        c["productivity"] = len(c["builds"])

    # ---- distractors: plausible wrong answers, not random ones ----
    # Scored on shared stems, shared topic, orthographic closeness and gender.
    # A candidate is rejected outright if its meaning overlaps the target's,
    # which would make the question unanswerable.
    playable = [c for c in cards if c["role"] == "deck"]
    fam_words = {c["id"]: {f["word"] for f in c["family"]} for c in cards}
    stems = {c["id"]: {p["candidates"][0]["lemma"]
                       for p in c["compound"]["parts"] if p["candidates"]}
             for c in cards}
    for c in playable:
        mine = {g["text"].lower() for g in c["glosses"]["en"]} | \
               {g["text"].lower() for g in c["glosses"]["de"]}
        scored = []
        for o in playable:
            if o["id"] == c["id"]:
                continue
            # Never offer a noun as a distractor for an adjective: the word
            # class alone would give the answer away.
            if o["wordclass"] != c["wordclass"]:
                continue
            theirs = {g["text"].lower() for g in o["glosses"]["en"]} | \
                     {g["text"].lower() for g in o["glosses"]["de"]}
            if mine & theirs:
                continue
            s = 4.0 * similarity(c["id"], o["id"])
            if stems[c["id"]] & stems[o["id"]]:
                s += 3.0
            if set(c["tags"]) & set(o["tags"]):
                s += 2.5
            if fam_words[c["id"]] & fam_words[o["id"]]:
                s += 2.0
            if c["gender_short"] and c["gender_short"] == o["gender_short"]:
                s += 0.5
            scored.append((s, o["id"]))
        scored.sort(reverse=True)
        c["distractors"] = [i for _, i in scored[:10]]

    # Lemma cards come before the compounds that reference them, so a part
    # claim can honestly say the lemma was confirmed earlier.
    order = {"low": 0, "medium": 1, "high": 2}
    cards.sort(key=lambda c: (c["compound"]["is_compound"],
                              order[c["confidence"]], c["id"]))

    validation = {c["id"]: {"pos": c["pos"], "gender": c["gender_short"],
                            "gloss": c["glosses"]["en"][0]["text"],
                            "freq": c["corpus"]["total"]} for c in cards}
    forms = {f: sorted({x[0] for x in v}) for f, v in index.items()}

    out = os.path.join(DATA, "deck.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"version": 3, "words": cards,
                   "validation": {"lemmas": validation, "forms": forms}},
                  fh, ensure_ascii=False, indent=2)

    if missing:
        print("  FAMILY ENTRIES NOT FOUND IN BIN: %s" % ", ".join(missing))
    nfam = sum(len(c["family"]) for c in cards)
    print("  %d family links across %d words"
          % (nfam, sum(1 for c in cards if c["family"])))
    na = sum(1 for c in cards if c["wordclass"] == "adj")
    print("  %d adjectives" % na)
    thin = [c["id"] for c in cards
            if c["wordclass"] == "adj" and (c["coverage"] or 0) < 20]
    print("  thin adjective coverage: %s" % (", ".join(thin) or "none"))
    nd = sum(1 for c in cards if c["role"] == "deck")
    nc = sum(1 for c in cards if c["compound"]["is_compound"])
    print("wrote %s" % out)
    print("  %d cards (%d deck words, %d support parts, %d compounds)"
          % (len(cards), nd, len(cards) - nd, nc))
    print("  %d claims" % sum(len(c["claims"]) for c in cards))
    for b in ("low", "medium", "high"):
        print("  %-7s %d" % (b, sum(1 for c in cards if c["confidence"] == b)))
    rare = [c["id"] for c in cards if c["corpus"]["plural_rare"]]
    out_r = [c["id"] for c in cards if c["corpus"]["outranked"]]
    print("  plural rare/unused: %s" % (", ".join(rare) or "none"))
    print("  variant outranks standard: %s" % (", ".join(out_r) or "none"))
    prod = sorted((c for c in cards if c["productivity"]),
                  key=lambda c: -c["productivity"])
    print("  most productive stems: %s" % ", ".join(
        "%s(%d)" % (c["id"], c["productivity"]) for c in prod[:8]))
    ranked = sorted(cards, key=lambda c: -c["corpus"]["total"])
    print("  most frequent: %s" % ", ".join(
        "%s(%d)" % (c["id"], c["corpus"]["total"]) for c in ranked[:6]))
    print("  least frequent: %s" % ", ".join(
        "%s(%d)" % (c["id"], c["corpus"]["total"]) for c in ranked[-6:]))


if __name__ == "__main__":
    main()
