# Publishing

`index.html` is the whole game in one file. No external requests at all.

## Updating an existing site
Upload the new `index.html` over the old one and commit. Pages redeploys in
about a minute; the link stays the same. Progress survives, since it is keyed
per browser by word id.

## First-time setup
1. Create a **public** repo (e.g. `islenska`).
2. **Add file → Upload files** → drag in everything from this zip, including
   the `source` folder. Commit.
3. **Settings → Pages** → *Deploy from a branch* → `main`, `/ (root)` → Save.
4. Wait a minute; the link appears on that page.

If a deploy fails with a 503, that is GitHub — check githubstatus.com and
re-run from the Actions tab.

## Sharing
Send the link. On a phone, **Add to Home Screen** — it then works fully
offline, with no fonts or scripts fetched from anywhere.

## review.html
Also uploaded, reachable at `/review.html`. Harmless, but it is a curation tool
rather than something for learners. Delete it from the repo if you prefer.
