# íslenska

A small vocabulary game for learning Icelandic nouns and adjectives, with
German and English glosses.

**Play:** https://bjarkifreyr95.github.io/islenska/

The point of it is compounds. Icelandic builds most of its vocabulary by
joining words together, so once you know `hús` and `sjúkur` you have most of
`sjúkrahús` already. Every compound in the game breaks apart after you answer,
and adjectives show the noun they came from and the verb built on top.

## What is here

| path | what it is |
|---|---|
| `index.html` | the game — one self-contained file, no server, works offline |
| `review.html` | curation tool for checking generated data before it ships |
| `source/` | everything needed to rebuild the two files above |

## Rebuilding

```
pip install -r source/requirements.txt
cd source
python build.py         # data/*.tsv -> data/deck.json
python make_game.py     # -> game.html    (rename to ../index.html to publish)
python make_review.py   # -> review.html
```

`build.py` pulls declensions and compound analysis from
[BÍN](https://bin.arnastofnun.is/) via the `islenska` package, and corpus
frequencies from the Icelandic Gigaword Corpus via `icegrams`. Both ship their
data offline, so no network access is needed.

## Editing the vocabulary

Edit only the TSV files. Everything else is generated and will be overwritten.

| file | holds |
|---|---|
| `source/data/words.tsv` | nouns in the deck |
| `source/data/adjectives.tsv` | adjectives in the deck |
| `source/data/pool.tsv` | words that only appear inside compounds, glossed but not drilled |
| `source/data/family.tsv` | related words: adjective → noun / verb |

Columns are tab-separated. `de` and `en` accept several senses separated by
`|`, first one primary. The `note` column is free text shown on the card, for
anything the pipeline cannot work out on its own.

`family.tsv` is `lemma, related, pos, de, en, rel`, where `rel` is `noun`,
`verb` or `stem`. Every row is checked against BÍN at build time and anything
unfindable is printed as a warning.

## Reviewing generated data

Open `review.html` and go through the cards. Each one makes a list of numbered
claims — meaning, declension, how a compound splits, which lemma each part
comes from. Everything starts accepted; press a number to reject one and add a
correction. Cards are sorted worst-confidence first, so if you stop halfway
you have already seen everything doubtful.

## Progress

The game keeps progress in the player's own browser. There is no account and
nothing is sent anywhere. *Save / load progress* on the summary screen gives
copyable text for moving between devices.

## Credits

Inflections and compound analysis from BÍN (Beygingarlýsing íslensks
nútímamáls), Árni Magnússon Institute. Frequency data from the Icelandic
Gigaword Corpus via Miðeind's `icegrams`. Check the licence terms of both
before redistributing the generated data.
