#!/usr/bin/env python3
"""Build the mmlabs static site: home.html is the home page, apps.json drives the app pages.

Usage:  python3 build.py            -> writes ./dist
        python3 build.py --watch    -> builds, serves dist on http://localhost:8000 and rebuilds on every
                                       change to apps.json, home.html, assets/, pages/, blog/ or build.py (Ctrl+C to stop)
To add an app: add an entry to apps.json and run the script again.
To add a blog post: add an entry to blog/posts.json and write its body in blog/<slug>.html.
Posts are published at blog/<slug>/ and listed in "Fresh from the lab" on the home page.
Set "detail": false for an app that has no brief yet (listed, no detail page).
Set "page" to a standalone landing page (e.g. pages/x.html) to publish it as the app's page
instead of the generated one; the build adds a small mmlabs bar with "All apps" and "Open app".
"""
import hashlib, json, re, shutil, subprocess, sys, threading, time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
WATCHED = [ROOT / "apps.json", ROOT / "home.html", ROOT / "assets", ROOT / "pages", ROOT / "blog", ROOT / "build.py"]
data = site = apps = posts = None
STATUS = {"live": "Live", "in-development": "In development", "planned": "Planned"}

def has_detail(a): return a.get("detail", True)

def head(title, desc, depth):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<link rel="icon" type="image/png" href="{up}assets/logo-short.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Figtree:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}assets/site.css">
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="{up or './'}"><img src="{up}assets/logo-long.png" alt="mmlabs" width="124" height="66"></a>
  <nav aria-label="Main"><a href="{up}#apps">Apps</a><a href="{up}#about">About</a></nav>
</div></header>
<main>
"""

def foot():
    return f"""</main>
<footer><div class="wrap">© 2026 mmlabs · {e(site['domain'])}</div></footer>
</body>
</html>
"""

def status_html(a):
    s = a.get("status")
    if not s: return ""
    label = a.get("statusNote") or STATUS.get(s, s)
    return f'<span class="status {e(s)}">{e(label)}</span>'

MAIL_ICON = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#1A2442" stroke-width="2.6" '
             'stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M4 7l8 6 8-6"/></svg>')

def social_links():
    # Icons for site.social in apps.json; an empty value hides that icon.
    s = site.get("social", {})
    items = [("facebook", "Facebook", s.get("facebook"), "#FFDCE5", "f"),
             ("email", "Email", s.get("email") and f"mailto:{s['email']}", "#DCEBFF", MAIL_ICON),
             ("linkedin", "LinkedIn", s.get("linkedin"), "#D5F3E6", "in")]
    return "".join(
        f'<a href="{e(href)}" aria-label="{label}" style="background:{bg}"'
        + ("" if key == "email" else ' target="_blank" rel="noopener"') + f">{icon}</a>"
        for key, label, href, bg, icon in items if href)

# "Back to top" button added to every page. It appears after scrolling down a screen.
# mm- prefixed and self-contained so it looks the same on the home page and on each app's own design.
TO_TOP = """<style>
.mm-top{position:fixed;right:24px;bottom:24px;z-index:90;width:48px;height:48px;border-radius:24px;display:flex;align-items:center;justify-content:center;
  background:#fff;color:#1A2442;border:3px solid #1A2442;box-shadow:0 4px 0 #1A2442;cursor:pointer;padding:0;
  opacity:0;visibility:hidden;transform:translateY(12px);transition:opacity .2s ease,transform .2s ease,visibility .2s,background-color .15s ease}
.mm-top.show{opacity:1;visibility:visible;transform:none}
.mm-top:active{transform:translateY(4px);box-shadow:0 0 0 #1A2442}
.mm-top:focus-visible{outline:3px solid #5B9BF0;outline-offset:3px}
@media (hover:hover){.mm-top.show:hover{background:#F2B233;transform:translateY(-3px);box-shadow:0 7px 0 #1A2442}}
@media (max-width:768px){.mm-top{right:16px;bottom:16px;width:44px;height:44px}}
@media (prefers-reduced-motion:reduce){.mm-top{transition:none}}
</style>
<button class="mm-top" type="button" aria-label="Back to top" title="Back to top"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg></button>
<script>
(function(){
  var b=document.querySelector('.mm-top');
  function t(){b.classList.toggle('show',window.scrollY>window.innerHeight*.8)}
  window.addEventListener('scroll',t,{passive:true});t();
  b.addEventListener('click',function(){
    var still=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({top:0,behavior:still?'auto':'smooth'});
    var f=document.querySelector('a[href],button');if(f&&f!==b)f.focus({preventScroll:true});
  });
})();
</script>
"""

def bust(m):
    # assets/ is cached for 30 days (see Dockerfile), so CSS/JS links get ?v=<content hash> to fetch edits right away.
    f = ROOT / m.group(2)
    return m.group(0) if not f.is_file() else f'{m.group(1)}{m.group(2)}?v={hashlib.md5(f.read_bytes()).hexdigest()[:8]}"'

def publish(path, html):
    # Every page goes through here so it gets the back-to-top button and cache-busted CSS/JS links.
    html = re.sub(r'((?:href|src)="(?:\.\./)*)(assets/[\w/.-]+\.(?:css|js))"', bust, html)
    path.write_text(html.replace("</body>", TO_TOP + "</body>", 1), encoding="utf-8")

def fill(html, up=""):
    # {{url:slug}} and {{page:slug}} are filled from apps.json, {{social}} and {{email}} from site.social,
    # {{home}} with the path back to the home page. up is the path from the page to the site root.
    by_slug = {a["slug"]: a for a in apps}
    def app_link(m):
        a = by_slug[m.group(2)]
        return e(a["url"]) if m.group(1) == "url" or not has_detail(a) else f'{up}apps/{e(a["slug"])}/'
    html = html.replace("{{social}}", social_links()).replace("{{email}}", e(site["social"]["email"]))
    html = html.replace("{{home}}", up or "./")
    return re.sub(r"\{\{(url|page):([\w-]+)\}\}", app_link, html)

def post_card(p, up=""):
    href = f'{up}blog/{e(p["slug"])}/'
    # "thumb" is the card-sized illustration (326 × 220); the title below says what it shows, so alt is empty
    thumb = (f'<img class="thumb" src="{up}{e(p["thumb"])}" alt="" width="326" height="220" loading="lazy">' if p.get("thumb")
             else f'<div class="placeholder" style="background:{e(p["color"])}">Post image 326 × 220</div>')
    return (f'<div class="post" data-href="{href}">{thumb}'
            f'<div class="post-body"><span class="tag" style="background:{e(p["color"])}">{e(p["tag"])}</span>'
            f'<h3><a href="{href}">{e(p["title"])}</a></h3><small>{e(p["read"])}, by the mmlabs team</small></div></div>')

def build_home():
    # home.html is the landing page design; {{posts}} becomes the cards in "Fresh from the lab".
    html = (ROOT / "home.html").read_text(encoding="utf-8")
    html = html.replace("{{posts}}", "\n      ".join(post_card(p) for p in posts))
    publish(DIST / "index.html", fill(html))

def home_part(html, pattern, up):
    # A block cut from home.html (header, newsletter, footer) with its links pointed back at the home page.
    part = re.search(pattern, html, re.S).group(0)
    part = part.replace('href="./"', f'href="{up}"').replace('href="#', f'href="{up}#').replace('src="assets/', f'src="{up}assets/')
    return fill(part, up)

def build_post(p, others):
    # Blog posts share the home page's header, newsletter and footer, so they always match it.
    up = "../../"
    home = (ROOT / "home.html").read_text(encoding="utf-8")
    header = home_part(home, r'<header class="header".*?</header>', up)
    header = header.replace('<a class="on" ', '<a ').replace(f'<a href="{up}#news">', f'<a class="on" href="{up}#news" aria-current="page">')
    newsletter = home_part(home, r'<section class="newsletter".*?</section>', up)
    footer = home_part(home, r'<footer class="footer".*?</footer>', up)
    body = fill((ROOT / "blog" / f'{p["slug"]}.html').read_text(encoding="utf-8"), up)
    c = e(p["color"])
    # "image" (with "alt") replaces the cover placeholder; posts without one keep the placeholder
    cover = (f'<img class="a-cover a-cover-img" src="{up}{e(p["image"])}" alt="{e(p["alt"])}" width="1140" height="420">'
             if p.get("image") else f'<div class="placeholder a-cover" style="background:{c}">{e(p["cover"])}<br>1140 × 420</div>')
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(p["title"])} · mmlabs</title>
<meta name="description" content="{e(p["dek"])}">
<meta property="og:title" content="{e(p["title"])}">
<meta property="og:description" content="{e(p["dek"])}">
<meta property="og:type" content="article">
<link rel="icon" type="image/png" href="{up}assets/logo-short.png">
<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Nunito:wght@500;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}assets/home.css">
<link rel="stylesheet" href="{up}assets/blog.css">
<script src="{up}assets/home.js" defer></script>
</head>

<body>

{header}

<main>
<section class="a-hero">
  <div class="container">
    <a class="a-back" href="{up}#news">‹ All updates</a>
    <span class="tag" style="background:{c}">{e(p["tag"])}</span>
    <h1>{e(p["title"])}</h1>
    <p class="a-dek">{e(p["dek"])}</p>
    <p class="a-by">By the mmlabs team<span aria-hidden="true">•</span>{e(p["read"])}</p>
    {cover}
  </div>
</section>

<article class="a-body">
{body}
<div class="a-author"><span class="a-avatar" aria-hidden="true">mm</span><div><b>The mmlabs team</b><small>Small apps for everyday work</small></div></div>
</article>

<section class="news a-more">
  <div class="container">
    <h2 class="section-title">Keep reading</h2>
    <div class="row">
      {"".join(post_card(o, up) for o in others)}
    </div>
  </div>
</section>
</main>

{newsletter}

{footer}

<div class="toast" id="toast" role="status" aria-live="polite"></div>

</body>
</html>
"""
    out = DIST / "blog" / p["slug"]
    out.mkdir(parents=True, exist_ok=True)
    publish(out / "index.html", html)

def sec(title, body):
    return f'<section class="block split"><h2>{e(title)}</h2><div>{body}</div></section>\n'

# Thin mmlabs strip added to the top of an app landing page so it links back to the site and on to the app.
# Class names are prefixed with mm- and styles are self-contained so they don't clash with the page's own CSS.
PAGE_STRIP = """<style>
.mm-strip{background:#243259;color:#fff;font:700 14px/1.2 system-ui,-apple-system,"Segoe UI",sans-serif;position:relative;z-index:1000}
.mm-strip-in{max-width:1160px;margin:0 auto;padding:10px 24px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.mm-strip a{color:inherit;text-decoration:none}
.mm-back{display:inline-flex;align-items:center;gap:10px;padding:6px 10px;margin-left:-10px;border-radius:14px;transition:background-color .15s ease}
.mm-back img{height:28px;width:28px;border-radius:8px;background:#fff}
.mm-open{display:inline-flex;align-items:center;height:36px;padding:0 18px;border-radius:18px;background:#F2B233;color:#1A2442!important;border:2px solid #1A2442;box-shadow:0 3px 0 #1A2442;white-space:nowrap;transition:transform .15s ease,box-shadow .15s ease}
.mm-strip a:focus-visible{outline:3px solid #5B9BF0;outline-offset:2px}
@media (hover:hover){.mm-back:hover{background:rgba(255,255,255,.12)}.mm-open:hover{transform:translateY(-2px);box-shadow:0 5px 0 #1A2442}}
.mm-open:active{transform:translateY(3px);box-shadow:0 0 0 #1A2442}
@media (max-width:560px){.mm-back span{display:none}}
</style>
<div class="mm-strip"><div class="mm-strip-in">
  <a class="mm-back" href="../../#apps" aria-label="All mmlabs apps"><img src="../../assets/logo-short.png" alt="">← <span>All mmlabs apps</span></a>
  <a class="mm-open" href="{url}">Open {name} ↗</a>
</div></div>
"""

def build_page(a):
    html = (ROOT / a["page"]).read_text(encoding="utf-8")
    strip = PAGE_STRIP.replace("{url}", e(a["url"])).replace("{name}", e(a["name"]))
    if not a.get("url"):  # no live app yet (e.g. a concept): drop the "Open app" button
        strip = re.sub(r'\n  <a class="mm-open"[^\n]*</a>', "", strip)
    html = re.sub(r"<body[^>]*>", lambda m: m.group(0) + "\n" + strip, html, count=1)
    html = html.replace("</head>", '<link rel="icon" type="image/png" href="../../assets/logo-short.png">\n</head>', 1)
    return html

def build_detail(a, nxt):
    out = DIST / "apps" / a["slug"]
    out.mkdir(parents=True, exist_ok=True)
    if a.get("page"):
        publish(out / "index.html", build_page(a))
        return
    parts = []
    if a.get("problem"):
        parts.append(sec("The problem", "".join(f"<p>{e(p)}</p>" for p in a["problem"])))
    if a.get("steps"):
        parts.append(f'<section class="block"><div class="split" style="margin-bottom:2rem"><h2>How it works</h2><div></div></div><ol class="steps">'
                     + "".join(f"<li><h3>{e(t)}</h3><p>{e(d)}</p></li>" for t, d in a["steps"]) + "</ol></section>\n")
    if a.get("features"):
        parts.append(sec("What it does", '<ul class="features">' + "".join(
            f"<li><h3>{e(t)}</h3><p>{e(d)}</p></li>" for t, d in a["features"]) + "</ul>"))
    if a.get("audience"):
        parts.append(sec("Who it's for", f"<p>{e(a['audience'])}</p>"))
    if a.get("scopeOut"):
        parts.append(sec("What it deliberately doesn't do", '<ul class="plain">' + "".join(f"<li>{e(x)}</li>" for x in a["scopeOut"]) + "</ul>"))
    if a.get("tech") or a.get("privacy"):
        body = ('<ul class="tags">' + "".join(f"<li>{e(t)}</li>" for t in a["tech"]) + "</ul>") if a.get("tech") else ""
        if a.get("privacy"): body += f"<p>{e(a['privacy'])}</p>"
        parts.append(sec("Under the hood", body))
    if a.get("roadmap"):
        parts.append(sec("Where it stands", '<ol class="roadmap">' + "".join(
            f'<li><span class="when">{e(w)}</span><div><h3>{e(t)}</h3><p>{e(d)}</p></div></li>' for w, t, d in a["roadmap"]) + "</ol>"))

    desc = f"{a['name']}: {a['summary']}"
    html = head(f"{a['name']} · {a['category']} · mmlabs", desc, 2) + f"""<div class="wrap">
<a class="crumb" href="../../#apps">← All apps</a>
<div class="dhero">
  <span class="cat">{e(a['category'])}</span>
  <h1>{e(a['name'])}</h1>
  {f'<p class="tag">{e(a["tagline"])}</p>' if a.get("tagline") else ""}
  <p class="sum">{e(a['summary'])}</p>
  <div class="row"><a class="btn" href="{e(a['url'])}">Open {e(a['name'])}</a>{status_html(a)}</div>
</div>
{''.join(parts)}
<nav class="next" aria-label="More apps">
  <a href="../../#apps"><small>Back to</small><strong>All apps</strong></a>
  <a href="../{e(nxt['slug'])}/" style="text-align:right"><small>Next app</small><strong>{e(nxt['name'])}</strong></a>
</nav>
</div>
""" + foot()
    publish(out / "index.html", html)

def build():
    global data, site, apps, posts
    data = json.loads((ROOT / "apps.json").read_text(encoding="utf-8"))
    site, apps = data["site"], data["apps"]
    posts = json.loads((ROOT / "blog" / "posts.json").read_text(encoding="utf-8"))["posts"]
    shutil.rmtree(DIST, ignore_errors=True)
    shutil.copytree(ROOT / "assets", DIST / "assets", dirs_exist_ok=True)
    build_home()
    detailed = [a for a in apps if has_detail(a)]
    for i, a in enumerate(detailed):
        build_detail(a, detailed[(i + 1) % len(detailed)])
    for p in posts:
        build_post(p, [o for o in posts if o is not p][:2])
    print(f"Built {1 + len(detailed) + len(posts)} pages into {DIST}")

def snapshot():
    out = {}
    for w in WATCHED:
        try:
            for f in ([w] if w.is_file() else w.rglob("*") if w.exists() else []):
                if f.is_file(): out[f] = f.stat().st_mtime
        except OSError:  # a file was renamed or deleted mid-scan; the next scan picks it up
            pass
    return out

class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()
    def log_message(self, *args): pass

def fresh_build():
    # Each build runs in a new process so edits to build.py itself take effect without a restart.
    if subprocess.run([sys.executable, str(ROOT / "build.py")]).returncode:
        print("Build failed (see the error above); still watching.")

def watch(port=8000):
    fresh_build()
    server = ThreadingHTTPServer(("", port), partial(NoCacheHandler, directory=str(DIST)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Serving http://localhost:{port} and watching for changes (Ctrl+C to stop)")
    seen = snapshot()
    try:
        while True:
            time.sleep(0.5)
            now = snapshot()
            if now == seen: continue
            time.sleep(0.2)  # let the editor finish writing
            before, seen = seen, snapshot()
            changed = sorted(f.relative_to(ROOT).as_posix() for f in set(before) | set(seen) if before.get(f) != seen.get(f))
            print(f"[{time.strftime('%H:%M:%S')}] Changed: {', '.join(changed)}")
            fresh_build()
    except KeyboardInterrupt:
        server.shutdown()

if __name__ == "__main__":
    watch() if "--watch" in sys.argv else build()
