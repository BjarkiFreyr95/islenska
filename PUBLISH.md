# Publishing the game

`game.html` is one self-contained file. Nothing to install, no server, no accounts.

## GitHub Pages (recommended)

1. Sign in at github.com and click **New repository**.
   Name it e.g. `islenska`, set it **Public**, tick **Add a README file**, click Create.
2. On the repo page click **Add file → Upload files**.
   Drag in `game.html`. Rename it to `index.html` first — Pages serves that
   automatically, so the link has no filename in it.
   Click **Commit changes**.
3. Go to **Settings → Pages** (left sidebar).
   Under *Build and deployment* → *Source*, choose **Deploy from a branch**.
   Branch: **main**, folder: **/ (root)**. Click **Save**.
4. Wait about a minute, then reload the Settings → Pages screen. It shows:
   `https://<your-username>.github.io/islenska/`
   That is the link you send. It works on any phone or desktop browser.

To update later: upload a new `index.html` over the old one. The link stays the same.

## Telling your friend

- Open the link, then **Add to Home Screen** (Share menu on iPhone,
  ⋮ menu on Android). It then opens like an app and works offline.
- Progress is stored in their own browser. There is no login and nothing is
  sent anywhere.
- Clearing browser data erases progress. **Save / load progress** on the
  summary screen gives copyable text as a backup.

## Alternatives

- **Email the file.** Attach `game.html`; they open it and it just works.
  No hosting at all. Downside: no easy way to send updates.
- **Netlify Drop** (app.netlify.com/drop). Drag the folder onto the page and
  get a link in seconds. You need an account to keep the link permanently.

## Rebuilding after editing words

    pip install -r source/requirements.txt
    cd source
    python build.py && python make_game.py && python make_review.py

Edit only the TSVs in `source/data/`. Everything else regenerates.
