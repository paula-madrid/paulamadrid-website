"""Builds paulamadrid.xyz.

Edit content/projects.txt (project pages) or the HOME / CV text below, then run:
    python3 build.py            # uses images in img/ where present, Readymag's CDN otherwise
    python3 build.py --remote   # always uses Readymag's CDN (for previews)
Writes index.html, cv/index.html and one folder per project, so URLs match the old site.
"""
import html, json, pathlib, re, shutil, sys

ROOT = pathlib.Path(__file__).parent
IMG = ROOT / "img"
RM = "https://i-p.rmcdn.net/6807745e32e5581e3597e94e/"
RMC = "https://c-p.rmcdn.net/6807745e32e5581e3597e94e/"
REMOTE = "--remote" in sys.argv
CROPS = json.loads((ROOT / "content" / "crops.json").read_text())

# ---------------------------------------------------------------- content
HOME = '''
<p>Hi! I’m a <b>graphic designer</b> and <b>illustrator</b> based in Copenhagen, with a love for bold, vivid visuals and clear communication.</p>
<p>Between 2017 and 2025, I led graphic design at the Danish architecture studio BIG – Bjarke Ingels Group. There, I worked across editorial, stationery, exhibitions, branding, and digital design.</p>
<p>Take a look at my <a href="{root}cv/">full CV</a> here.</p>
<p>My experience spans:</p>
<p>· Visual Identity Design<br>· Editorial &amp; Print Design<br>· Exhibition &amp; Environmental Graphics<br>· Infographics Design<br>· Signage &amp; Wayfinding<br>· Editorial &amp; Corporate Illustration</p>
<p>If you're interested in working together or have any questions, you can reach me via <a href="mailto:m4dridestudi0@gmail.com">email</a>.</p>
<p class="social"><a href="https://www.instagram.com/paula.madrid/" target="_blank" rel="noopener">Instagram</a> · <a href="https://www.linkedin.com/in/paulamadrid000/" target="_blank" rel="noopener">LinkedIn</a> · <a href="https://www.behance.net/madriddd" target="_blank" rel="noopener">Behance</a></p>
'''
AVATAR = "C:5497052/Image-cc7390ce-fb5c-4390-bf82-93516699a7cd.gif"

CV_EXPERIENCE = [
    ("BIG - Bjarke Ingels Group (Copenhagen, Denmark)", "6 years 8 months", [
        ("Global Graphic Design &amp; Exhibitions Lead", "Jul 2023 - Sept 2025 · 2 years 2 months"),
        ("Lead Graphic Designer", "Jul 2020 - Jun 2023 · 3 years"),
        ("Designer", "Jan 2019 - May 2020 · 1 year 6 months")]),
    ("Sulitze Muñoz Architects (Madrid, Spain)", "6 months", [
        ("Architectural Drafter", "Jul 2018 - Dec 2018 · 6 months")]),
    ("BIG - Bjarke Ingels Group (Copenhagen, Denmark)", "1 year", [
        ("Design Assistant", "Jul 2017 - Jul 2018 · 1 year")]),
    ("EFFEKT (Copenhagen, Denmark)", "6 months", [
        ("Design Assistant", "Jan 2017 - Jun 2017 · 6 months")]),
]
CV_TALKS = [
    'Contributor to <a href="https://www.dezeen.com/2025/06/25/well-made-objects-pearson-lloyd-exhibition/" target="_blank" rel="noopener">Godt Lavet</a><br>Exhibition, curated by Pearson Lloyd (2025)',
    'Speaker at <a href="https://2024.designmatters.io/lineup/paula-madrid/" target="_blank" rel="noopener">DesignMatters 2024</a><br>Talk: "Crafting Clarity: The Power of Visual Storytelling" (2024)',
    'Contributor to <a href="https://aarch.dk/en/the-winners-of-drawing-of-the-year-2017/" target="_blank" rel="noopener">Drawing of the Year</a><br>Publication by Aarhus School of Architecture (2017)',
]
CV_EDUCATION = [
    ("M.Arch. by Universidad San Pablo CEU, Madrid (Spain)", "2009 - 2016"),
    ("Visiting School Program in Architectural Association, London (UK)", "2013 - 2014"),
]
CV_TRAINING = [
    ("Wayfinding and Signage Design Course (30h) in ual:", "2024"),
    ("Motion Graphics with After Effects (150h) in School of Motion", "2019"),
]
YEAR = "2026"

# ---------------------------------------------------------------- parsing
def parse():
    projects, p = [], None
    for raw in (ROOT / "content" / "projects.txt").read_text().splitlines():
        line = raw.rstrip()
        if not line or line.startswith("#") and not line.startswith("## "):
            continue
        if line.startswith("## "):
            slug, title, tags = [s.strip() for s in line[3:].split("|")]
            p = dict(slug=slug, title=title, tags=[t.strip() for t in tags.split(",") if t.strip()], meta=[], blocks=[])
            projects.append(p)
            continue
        kind, _, rest = line.partition(" ")
        if kind == "THUMB":
            parts = rest.split()
            p["thumb"] = parts[0]
            p["thumb_poster"] = parts[1] if len(parts) > 1 and not parts[1] == "tall" else None
            p["tall"] = "tall" in parts
        elif kind == "M":
            p["meta"].append(rest)
        elif kind in ("P", "C"):
            p["blocks"].append(dict(k=kind, html=rest))
        elif kind == "I":
            x, y, w, h, f = rest.split(maxsplit=4)
            p["blocks"].append(dict(k="I", x=int(x), y=int(y), w=int(w), h=int(h), f=f))
    return projects


def src(f, width=1400):
    """Local file if we have it, otherwise Readymag's CDN (cropped as on the old site)."""
    if f.startswith("C:"):                      # gifs live on Readymag's other CDN
        name = f.split("Image-")[1][:8] + ".gif"
        return (None if REMOTE else local(name)) or RMC + f[2:]
    if "/" not in f:                            # a file of our own in img/
        return "img/" + f
    path, _, query = f.partition("?")
    uid = re.search(r"([0-9a-f]{8})-", path).group(1)
    if not REMOTE and (hit := local(uid)):
        return hit
    folder, name = path.split("/")
    query = query or CROPS.get(uid, "")
    return f"{RM}{folder}/image-{name}?w={width}" + (f"&{query}" if query else "")


def local(stem):
    for ext in (".jpg", ".png", ".gif", ".webp"):
        if (IMG / (stem.split(".")[0] + ext)).exists() and (stem.endswith(ext) or "." not in stem):
            return "img/" + stem.split(".")[0] + ext
    return None


# ---------------------------------------------------------------- rendering
e = html.escape
U = "calc({}*var(--u))".format


def bands(images):
    """Group images whose vertical extents overlap into one band, like the old page."""
    out = []
    for im in images:
        if out and im["y"] < out[-1]["bottom"] - 4:
            out[-1]["items"].append(im)
            out[-1]["bottom"] = max(out[-1]["bottom"], im["y"] + im["h"])
        else:
            out.append(dict(top=im["y"], bottom=im["y"] + im["h"], items=[im]))
    return out


def img_tag(f, w, h, rel, alt, eager=False):
    s = src(f)
    if s.startswith("img/"):
        s = rel + s
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return f'<img src="{e(s)}" alt="{e(alt)}" width="{w}" height="{h}" {load} decoding="async">'


def render_blocks(p, rel):
    out, run, n = [], [], [0]

    def flush():
        for b in bands(run):
            items = []
            for im in b["items"]:
                n[0] += 1
                style = f'left:{U(im["x"]-193)};top:{U(im["y"]-b["top"])};width:{U(im["w"])};height:{U(im["h"])}'
                items.append(f'<figure style="{style}">{img_tag(im["f"], im["w"], im["h"], rel, f"{p["title"]}, image {n[0]}", eager=n[0] == 1)}</figure>')
            out.append(f'<div class="band" style="height:{U(b["bottom"]-b["top"])}">{"".join(items)}</div>')
        run.clear()

    for b in p["blocks"]:
        if b["k"] == "I":
            run.append(b)
            continue
        flush()
        cls = "caption" if b["k"] == "C" else "text"
        out.append(f'<p class="{cls}">{fix_links(b["html"], rel)}</p>')
    flush()
    return "\n".join(out)


def fix_links(h, rel):
    return h.replace('href="../', f'href="{rel}')


def page(title, body, rel, desc, cls):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<link rel="icon" href="{rel}favicon.png" type="image/png">
<link rel="preload" href="{rel}fonts/inclusive-sans-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{rel}style.css">
</head>
<body class="{cls}">
{body}
</body>
</html>
'''


def sidebar(rel):
    av = src(AVATAR)
    av = rel + av if av.startswith("img/") else av
    return f'''<aside class="side">
  <a class="name" href="{rel}">paula madrid</a>
  <img class="avatar" src="{e(av)}" alt="" width="26" height="26">
  <div class="intro">{HOME.format(root=rel)}</div>
  <p class="copy">© {YEAR} paula madrid</p>
</aside>'''


def build():
    projects = parse()
    for d in [p["slug"] for p in projects] + ["cv", "bhq-signange-and-wayfinding"]:
        shutil.rmtree(ROOT / d, ignore_errors=True)

    # home: two columns, filled top-down so the tall tile sits where it did
    cols, heights = [[], []], [0, 0]
    order = ["formgiving-book", "flowers-and-dogs-deck-of-cards", "3daysofdesign-visual-identity",
             "geologic-map-of-the-near-side-of-the-moon", "formgiving-exhibition", "munsell-color-system",
             "from-the-arctic-edge-to-ocean-bloom", "marijane", "bhq-signage-and-wayfinding", "sol-y-mar",
             "the-architects-guide-to-the-galaxy", "homing-pigeons", "mitgera-11"]
    by = {p["slug"]: p for p in projects}
    left = ["formgiving-book", "3daysofdesign-visual-identity", "munsell-color-system", "marijane", "sol-y-mar", "homing-pigeons"]
    for slug in order:
        p = by[slug]
        i = 0 if slug in left else 1
        if p.get("thumb_poster") or p["thumb"].endswith(".mp4"):
            media = (f'<video src="img/{p["thumb"]}" poster="img/{p["thumb_poster"]}" muted loop autoplay playsinline '
                     f'preload="metadata" aria-label="{e(p["title"])}"></video>')
        else:
            media = img_tag(p["thumb"], 312, 464 if p["tall"] else 224, "", p["title"], eager=heights[i] < 500)
        cols[i].append(f'<a class="tile{" tall" if p["tall"] else ""}" href="{slug}/" style="order:{order.index(slug)}">{media}<span>{e(p["title"])}</span></a>')
        heights[i] += 464 if p["tall"] else 224
    grid = "".join(f'<div class="col">{"".join(c)}</div>' for c in cols)
    home = f'{sidebar("")}\n<main class="grid">{grid}</main>'
    (ROOT / "index.html").write_text(page("paula madrid", home, "", "Paula Madrid is a graphic designer and illustrator based in Copenhagen.", "home"))

    # projects
    for i, p in enumerate(projects):
        rel = "../"
        prev_p = projects[i - 1] if i else None
        next_p = projects[(i + 1) % len(projects)]
        tags = "".join(f"<li>{e(t)}</li>" for t in p["tags"])
        meta = "<br>".join(p["meta"])
        back = f'{rel}{prev_p["slug"]}/' if prev_p else rel
        body = f'''<nav class="pnav">
  <a href="{back}">← back</a>
  <a href="{rel}">← home</a>
</nav>
<a class="next" href="{rel}{next_p["slug"]}/">next →</a>
<main class="project">
  <h1>{e(p["title"])}</h1>
  <ul class="tags">{tags}</ul>
  <p class="meta">{meta}</p>
{render_blocks(p, rel)}
  <a class="next-bottom" href="{rel}{next_p["slug"]}/">Next: {e(next_p["title"])} →</a>
</main>
<p class="copy foot">© {YEAR} paula madrid</p>'''
        first = re.sub("<[^>]+>", "", next(b["html"] for b in p["blocks"] if b["k"] == "P"))
        out = ROOT / p["slug"] / "index.html"
        out.parent.mkdir()
        out.write_text(page(f"paula madrid — {p['title']}", body, rel, html.unescape(first)[:155], "proj"))

    # old misspelt BHQ address keeps working
    old = ROOT / "bhq-signange-and-wayfinding"
    old.mkdir()
    old.joinpath("index.html").write_text('<!doctype html><meta charset="utf-8"><title>Moved</title>'
        '<link rel="canonical" href="../bhq-signage-and-wayfinding/"><meta http-equiv="refresh" content="0; url=../bhq-signage-and-wayfinding/">')

    # CV
    exp = "".join(f'''<div class="job"><p><b>{c}</b><br>{d}</p>{"".join(f'<p class="role">{r}<br><span>{t}</span></p>' for r, t in roles)}</div>'''
                  for c, d, roles in CV_EXPERIENCE)
    two = lambda rows: "".join(f"<p>{a}<br><span>{b}</span></p>" for a, b in rows)
    cv = f'''{sidebar("../")}
<main class="cv">
  <section><h2>Professional experience</h2>{exp}
    <h2>Talks &amp; showcases</h2>{"".join(f"<p>{t}</p>" for t in CV_TALKS)}</section>
  <section><h2>Education</h2>{two(CV_EDUCATION)}
    <h2>Complementary training</h2>{two(CV_TRAINING)}</section>
</main>'''
    (ROOT / "cv").mkdir()
    (ROOT / "cv" / "index.html").write_text(page("paula madrid — CV", cv, "../", "CV of Paula Madrid, graphic designer and illustrator in Copenhagen.", "cvpage"))
    print(f"built home, CV and {len(projects)} projects ({'remote' if REMOTE else 'local where available'} images)")


build()
