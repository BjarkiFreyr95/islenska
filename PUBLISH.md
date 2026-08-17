# Publishing

`index.html` is the whole game in one file. No build step on GitHub's side.

## First-time setup

1. Create a **public** repo on github.com (e.g. `islenska`).
2. **Add file → Upload files** → drag in *everything from this zip*, including
   the `source` folder. Commit.
3. **Settings → Pages** → Source: *Deploy from a branch* →
   branch `main`, folder `/ (root)` → **Save**.
4. Wait about a minute, reload that page. It shows your link:
   `https://<username>.github.io/<repo>/`

## Updating later

Upload a new `index.html` over the old one and commit. Pages redeploys in about
a minute and the link stays the same.

Progress survives updates. It is stored per browser and keyed by word id, so
anything already learnt stays learnt as long as you do not rename words.

If a deploy fails with a 503, that is GitHub, not you — check githubstatus.com
and re-run the job from the Actions tab later.

## Sharing with someone

- Send the link. Opening it is enough; there is nothing to install.
- On a phone: **Add to Home Screen**. It then opens like an app and works
  offline.
- No account, no signup, nothing leaves their device.

## Alternatives to GitHub Pages

- **Email `index.html` as an attachment.** It works straight from the
  download. No hosting at all, but no easy way to push updates.
- **Netlify Drop** (app.netlify.com/drop) — drag the folder, get a link in
  seconds.

## Note on `review.html`

It is uploaded alongside the game and reachable at
`https://<username>.github.io/<repo>/review.html`. That is harmless — it is a
curation tool with no secrets in it — but it is not meant for learners. Delete
it from the repo if you would rather it not be public.
