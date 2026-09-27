# mmlabs.online showcase

Static site generated from `apps.json`. No framework, no runtime dependencies.

The home page is `home.html` (the landing page design). `{{url:slug}}` and `{{page:slug}}` in it are filled from `apps.json` at build time; everything else is copied as is.

## Build
    python3 build.py        # writes ./dist
    python3 build.py --watch  # while editing: serves http://localhost:8000 and rebuilds on every save

Watch mode rebuilds when `apps.json`, `home.html`, `assets/`, `pages/`, `blog/` or `build.py` change. Each rebuild runs the latest `build.py`, so no restart is needed.

## Add or update an app
1. Edit `apps.json` (copy an existing app entry).
2. `"detail": false` lists the app on the home page without a detail page (use until a brief exists).
3. `"page": "pages/<slug>.html"` publishes a hand-made landing page as the app's page (the build adds a small bar linking back to all apps and to the app). The source product briefs stay in `design/`; the landing pages in `pages/` are the public versions.
4. Run `python3 build.py` again.

## Add a blog post
1. Add an entry to `blog/posts.json` (slug, title, tag, color, dek, cover, read). Put the cover illustration (1140 × 420) in `assets/blog/` and set `image` and `alt`; without them the post shows a placeholder labelled with `cover`. For the card in "Fresh from the lab", add a card-sized illustration (326 × 220, e.g. an SVG with viewBox 652 × 440) and set `thumb`; without it the card shows a placeholder.
2. Write the article body in `blog/<slug>.html`. `{{page:slug}}` links to an app page and `{{home}}` to the home page.
3. Run `python3 build.py`. The post is published at `blog/<slug>/`, uses the home page's header, newsletter and footer, and shows up in "Fresh from the lab" (`{{posts}}` in `home.html`).

## Serve (WSL + Docker)
The image builds the site itself and serves it with nginx on port 3000:

    docker build -t mmlabs-site .
    docker run -d --name mmlabs-home --restart unless-stopped -p 3000:3000 mmlabs-site

Point the Cloudflare Tunnel hostname `mmlabs.online` to `http://localhost:3000`.

## Notes
- Pages are plain HTML. The home page adds one small script, `assets/home.js`, for the interaction states in `design/mmlabs-interaction-states.html` (Apps dropdown, sticky header, section highlight in the nav, clickable cards, form checks and toast). Without it every link and form still works.
- Logos: `assets/logo-long.png` (headers), `assets/logo-short.png` (browser tab icon). Both have transparent padding that the CSS trims with negative margins; if you replace them with differently padded images, adjust those margins.
