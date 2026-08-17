# Publishing an update

`game.html` is one self-contained file. No install, no server, no accounts.

## Updating an existing GitHub Pages site

1. Open your repo → click `index.html` → the pencil icon isn't needed:
   use **Add file → Upload files** and drop in the new `game.html`,
   renamed to `index.html`. It overwrites the old one.
2. **Commit changes.** Pages redeploys in about a minute. Same link.

Existing progress survives: it is keyed per browser and the word ids have not
changed, so anything already learnt stays learnt.

## First-time setup

1. New **public** repo on github.com (e.g. `islenska`), tick "Add a README file".
2. **Add file → Upload files** → drag in `game.html`, **rename it `index.html`**, commit.
3. **Settings → Pages** → Source: *Deploy from a branch* → branch `main`,
   folder `/ (root)` → Save.
4. Wait ~1 min, reload. Your link: `https://<username>.github.io/islenska/`

If the deploy fails with a 503, check githubstatus.com and re-run the job later.

## For your friend

- Open the link, then **Add to Home Screen**. It runs offline afterwards.
- Progress lives in their browser. No login, nothing sent anywhere.
- **Save / load progress** on the summary screen gives copyable text as a backup.

## Rebuilding after editing words

    pip install -r source/requirements.txt
    cd source
    python build.py && python make_game.py && python make_review.py

Edit only the TSVs in `source/data/`:

| file | what it holds |
|---|---|
| `words.tsv` | nouns |
| `adjectives.tsv` | adjectives |
| `pool.tsv` | words that only appear inside compounds |
| `family.tsv` | related words: adjective -> noun/verb |
