# íslenska

A vocabulary game for learning Icelandic nouns, verbs and adjectives, with
German and English glosses.

**Play:** https://bjarkifreyr95.github.io/islenska/

The point of it is compounds. Icelandic builds most of its vocabulary by
joining words together, so once you know `hús` and `sjúkur` you have most of
`sjúkrahús` already. Every compound breaks apart after you answer, and
adjectives show the noun they came from and the verb built on top.

## What is here

| path | what it is |
|---|---|
| `index.html` | the game — one file, no external requests, works offline |
| `review.html` | curation tool for checking generated data before it ships |
| `source/` | everything needed to rebuild the two files above |

Neither page loads fonts, scripts or anything else from the network. Nothing is
sent anywhere, and progress never leaves the browser.

## Rebuilding

```
pip install -r source/requirements.txt
cd source
python build.py         # data/*.tsv -> data/deck.json
python make_game.py     # -> game.html    (rename to ../index.html to publish)
python make_review.py   # -> review.html
```

`build.py` takes declensions and compound analysis from
[BÍN](https://bin.arnastofnun.is/) via `islenska`, and corpus frequencies from
the Icelandic Gigaword Corpus via `icegrams`. Both ship their data offline.

## Editing the vocabulary

Edit only the TSV files. Everything else is generated and gets overwritten.

| file | holds |
|---|---|
| `source/data/words.tsv` | nouns |
| `source/data/adjectives.tsv` | adjectives |
| `source/data/verbs.tsv` | verbs |
| `source/data/pool.tsv` | words that only appear inside compounds |
| `source/data/family.tsv` | related words: adjective → noun / verb |

`de` and `en` take several senses separated by `|`, first one primary. `note`
is free text shown on the card.

### Overriding a compound split

The `split` column overrides the automatic analysis when it gets a word wrong:

| value | meaning |
|---|---|
| *(empty)* | analyse automatically |
| `none` | treat as a simple word, never split |
| `far=för sími=sími` | use these fragments, with these lemmas |
| `hring=hringur laga=-` | `-` marks a derivational suffix, not a word |

The fragments must join back into the original word; the build warns if they
do not.

## Word identity

A card is identified by word class plus lemma — `noun:vinna` and `verb:vinna`
are two separate cards, because *vinna* is both a feminine noun (work) and a
verb (to work). The spelling alone is only ever a display label. Progress,
mastery, distractors and compound parts all key on the qualified id, so two
words that happen to be spelled alike can never share a progress slot.

## Verbs

Each verb card carries the full personal conjugation pulled from BÍN: present
and past for ég / þú / hann-hún / við / þið / þau, plus the infinitive, supine,
imperative, present participle and the middle-voice form where one exists. The
reviewer also shows the subjunctive.

Icelandic has no inflected future, so the future row is constructed as
`munu` + infinitive and labelled as built rather than looked up. Everyday
speech more often uses `ætla að`.

Traps the build handles automatically, worth knowing if you add verbs:

- `SP-` marks are fused question forms (*talarðu*) and `OP-` marks are
  impersonal constructions (*mig munar*). Neither belongs in a conjugation.
- `BH-ST` is the *clipped* imperative (*kom*), `BH-ET` the singular (*komdu*),
  `BH-FT` the plural (*komið*). All three are kept.
- Deponent verbs such as `ferðast` have no active forms, so the middle voice
  is read as the real paradigm.
- Two verbs can share a spelling *and* both have complete paradigms — `heita`
  is "to be called" (past *hét*) and "to heat" (past *heitti*). When that
  happens the build prints an AMBIGUOUS warning and marks the card
  low-confidence until a `bin_id` is pinned in `verbs.tsv`.

`verbs.tsv` has two override columns: `bin_id` pins which BÍN lemma to use, and
`supine` overrides a sense-dependent form (`geta` takes *getað* as the
auxiliary "be able to", not *getið*).

## Progress

Progress saves automatically in the player's browser. If the browser refuses to
store data — private windows usually do — the settings screen says so rather
than failing silently.

Each word has a strength from 0 to 5, and the mastery bar is the sum of those
across the deck. A correct answer adds one, a wrong answer removes one, and
nothing is retired until the player chooses to retire it: at full strength the
game offers to mark it learnt, and *My progress* lets them mark or un-mark
anything by hand. Marking by hand also sets strength to 5, so the two numbers
never contradict each other. Compounds earn strength only for themselves, never
for their parts.

Round length counts answered questions, not distinct words, so 12 means exactly
12 and a small lane simply cycles round again.

*My progress* has two views: a flat word list, and **word families**, which
groups every stem with the longer words built from it and shows how many of
them you have met.

## Credits

Inflections and compound analysis from BÍN (Beygingarlýsing íslensks
nútímamáls), Árni Magnússon Institute. Frequency data from the Icelandic
Gigaword Corpus via Miðeind's `icegrams`. Check the licence terms of both
before redistributing the generated data.
