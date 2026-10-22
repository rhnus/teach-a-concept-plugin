"""Maintain a project's concept library: short visual teaching packs kept in the repo.

A project opts in with `init`, which writes .concepts/config.json and a copy of this tool to
.concepts/tool/, so teammates, git hooks and CI can run it without Claude. Each pack is
<library>/<slug>/index.html plus meta.json; the library index (README.md and index.html) is
generated from the meta files, so never hand-edit it.

  init      [--brand B] [--theme default|nus|path.css] [--library docs/concepts] [--branch main] [--hook]
  new       <slug> --title T --summary S --type proposal|advice|code|process|concept --owner O
            --audience A [--minutes 30] [--sources path ...] [--references text ...]
  verify    <slug>                 fingerprint the sources, stamp reading time, mark current
  check     [--files f ...] [--staged] [--mark] [--hook]
  set       <slug> key=value ...   e.g. artifact_url=... start_here=2 owner=...
  supersede <old> <new>
  remove    <slug> [--committed]
  link      <path> [line] [end]    web URL for a source file (Azure DevOps, GitHub, GitLab, Bitbucket)
  theme     <default|nus|path.css> re-theme every pack and the index
  publish-copy <slug> [--out f]     write the pack without its <html>/<head>/<body> wrapper, for hosts that add their own
  install-hook                     non-blocking git pre-commit warning
  index | list | sync-tool

Run from anywhere inside the project; the project root is the folder holding .concepts/.
"""
import argparse
import datetime
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

VERSION = "1.0.1"
TOOL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE = os.path.join(TOOL_DIR, "assets", "pack-template.html")
THEMES = os.path.join(TOOL_DIR, "assets", "themes")
TYPES = {"proposal": "Proposal", "advice": "Advice", "code": "Code walkthrough",
         "process": "Process", "concept": "Concept"}
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
THEME_BLOCK = re.compile(r"/\* theme:start \*/.*?/\* theme:end \*/", re.S)
STATUS_BLOCK = re.compile(r"<!-- concept-status -->.*?<!-- /concept-status -->", re.S)
READ_BLOCK = re.compile(r"<!-- read-time -->.*?<!-- /read-time -->", re.S)
SOURCES_BLOCK = re.compile(r"<!-- sources -->.*?<!-- /sources -->", re.S)
WRAPPER = re.compile(r"<!doctype html>\s*|</?html\b[^>]*>\s*|</?head>\s*|</?body>\s*|<meta charset=[^>]*>\s*|"
                     r"<meta name=\"viewport\"[^>]*>\s*", re.I)
SOURCES_SHOWN = 3
PLACEHOLDER = re.compile(r"\[\[[^\]]+\]\]")
HOOK_MARK = "concept-library pre-commit"
DEFAULTS = {"version": 1, "library": "docs/concepts", "brand": "Concept library", "theme": "default",
            "theme_key": "concepts-theme", "branch": "main", "link": "auto"}

ROOT = None
CONFIG = None


class ToolError(Exception):
    pass


def fail(message):
    raise ToolError(message)


# ---------- project discovery ----------

def find_root(start):
    here = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(here, ".concepts", "config.json")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            return None
        here = parent


def load_project(start="."):
    global ROOT, CONFIG
    ROOT = find_root(start)
    if not ROOT:
        fail("no concept library here. Run `concepts.py init` in the project folder first")
    with open(os.path.join(ROOT, ".concepts", "config.json"), encoding="utf-8") as f:
        CONFIG = {**DEFAULTS, **json.load(f)}


def library():
    return os.path.join(ROOT, CONFIG["library"])


def git(*args, cwd=None, check=True):
    out = subprocess.run(["git", *args], cwd=cwd or ROOT, capture_output=True, text=True)
    if check and out.returncode != 0:
        fail(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout.strip()


def today():
    return datetime.date.today().isoformat()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------- packs ----------

def meta_path(slug):
    return os.path.join(library(), slug, "meta.json")


def page_path(slug):
    return os.path.join(library(), slug, "index.html")


def load(slug):
    if not os.path.isfile(meta_path(slug)):
        fail(f"no pack called {slug}")
    with open(meta_path(slug), encoding="utf-8") as f:
        return json.load(f)


def save(meta):
    write(meta_path(meta["slug"]), json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    stamp_page(meta)


def packs():
    if not os.path.isdir(library()):
        return []
    return [load(name) for name in sorted(os.listdir(library())) if os.path.isfile(meta_path(name))]


# ---------- source fingerprints ----------

def source_files(sources):
    """Every file under the sources (tracked, plus untracked files git doesn't ignore), project-relative."""
    if not sources:
        return []
    listed = git("ls-files", "-co", "--exclude-standard", "--", *sources)
    return sorted({p for p in listed.splitlines() if p and os.path.isfile(os.path.join(ROOT, p))})


def fingerprint(sources):
    """Content hashes rather than a commit id, so squash merges and rebases never orphan a pack."""
    result = {}
    for rel in source_files(sources):
        with open(os.path.join(ROOT, rel), "rb") as f:
            result[rel] = hashlib.sha1(f.read().replace(b"\r\n", b"\n")).hexdigest()[:12]
    return result


def drift(meta):
    old = meta.get("fingerprint") or {}
    new = fingerprint(meta["sources"])
    changed = [p for p in new if p in old and new[p] != old[p]]
    added = [p for p in new if p not in old]
    removed = [p for p in old if p not in new]
    return changed, added, removed


# ---------- links ----------

def remote_parts():
    url = git("remote", "get-url", "origin", check=False)
    patterns = [
        ("azure", r"https://(?:[^@/]+@)?dev\.azure\.com/(?P<org>[^/]+)/(?P<project>[^/]+)/_git/(?P<repo>[^/?#]+)"),
        ("azure", r"(?:ssh://)?git@ssh\.dev\.azure\.com:v3/(?P<org>[^/]+)/(?P<project>[^/]+)/(?P<repo>[^/?#]+)"),
        ("azure", r"https://(?:[^@/]+@)?(?P<org>[^./]+)\.visualstudio\.com/(?:DefaultCollection/)?(?P<project>[^/]+)/_git/(?P<repo>[^/?#]+)"),
        ("bitbucket", r"(?:https://(?:[^@/]+@)?|(?:ssh://)?git@)(?P<host>[^/:]*bitbucket[^/:]*)[:/](?P<path>.+?)(?:\.git)?/?$"),
        ("gitlab", r"(?:https://(?:[^@/]+@)?|(?:ssh://)?git@)(?P<host>[^/:]*gitlab[^/:]*)[:/](?P<path>.+?)(?:\.git)?/?$"),
        ("github", r"(?:https://(?:[^@/]+@)?|(?:ssh://)?git@)(?P<host>[^/:]*github[^/:]*)[:/](?P<path>.+?)(?:\.git)?/?$"),
    ]
    for kind, pattern in patterns:
        m = re.match(pattern, url)
        if m:
            return kind, m.groupdict()
    return None, {}


def link_for(path, line=None, end=None):
    """A web URL for a project file, or None when the host isn't recognised."""
    repo_path = (git("rev-parse", "--show-prefix") + path.replace("\\", "/")).lstrip("/")
    branch = CONFIG["branch"]
    end = end or line
    if CONFIG["link"] != "auto":
        return CONFIG["link"].format(path=repo_path, branch=branch, line=line or "", end=end or "")
    kind, p = remote_parts()
    q = urllib.parse.quote
    if kind == "azure":
        url = (f"https://dev.azure.com/{p['org']}/{p['project']}/_git/{p['repo']}"
               f"?path={q('/' + repo_path)}&version=GB{q(branch)}")
        if line:
            url += f"&line={line}&lineEnd={end}&lineStartColumn=1&lineEndColumn=1&lineStyle=plain&_a=contents"
        return url
    if kind == "github":
        return f"https://{p['host']}/{p['path']}/blob/{q(branch)}/{q(repo_path)}" + (f"#L{line}-L{end}" if line else "")
    if kind == "gitlab":
        return f"https://{p['host']}/{p['path']}/-/blob/{q(branch)}/{q(repo_path)}" + (f"#L{line}-{end}" if line else "")
    if kind == "bitbucket":
        return f"https://{p['host']}/{p['path']}/src/{q(branch)}/{q(repo_path)}" + (f"#lines-{line}:{end}" if line else "")
    return None


def link_or_relative(path, slug):
    url = link_for(path)
    if url:
        return url
    return os.path.relpath(os.path.join(ROOT, path), os.path.join(library(), slug)).replace("\\", "/")


# ---------- page rendering ----------

def theme_css(name=None):
    name = name or CONFIG["theme"]
    builtin = os.path.join(THEMES, f"{name}.css")
    path = builtin if os.path.isfile(builtin) else os.path.join(ROOT, name)
    if not os.path.isfile(path):
        fail(f"theme not found: {name} (built in: {', '.join(sorted(t[:-4] for t in os.listdir(THEMES)))}, "
             f"or a .css path relative to the project)")
    return read(path).strip()


def apply_theme(text, css):
    return THEME_BLOCK.sub(lambda _: f"/* theme:start */\n{css}\n/* theme:end */", text)


def fill(text, values):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def sources_html(meta):
    """The header's "Built from" line; a long list folds behind a count so the header stays short."""
    e = html.escape
    items = [f'<a href="{e(link_or_relative(s, meta["slug"]))}">{e(s)}</a>' for s in meta["sources"]]
    items += [e(r) for r in meta["references"]]
    if not items:
        return "Built from notes supplied by the owner"
    if len(items) <= SOURCES_SHOWN:
        return "Built from " + ", ".join(items)
    return (f'Built from <details><summary>{len(items)} sources</summary>'
            f'<span class="source-list">{", ".join(items)}</span></details>')


def render_pack(meta):
    e = html.escape
    page = fill(read(TEMPLATE), {
        "title": e(meta["title"]), "summary": e(meta["summary"]), "type_label": e(TYPES[meta["type"]]),
        "audience": e(meta["audience"]), "minutes": str(meta["meeting_minutes"]), "owner": e(meta["owner"]),
        "sources": sources_html(meta),
        "date": meta["created"], "brand": e(CONFIG["brand"]), "theme_key": e(CONFIG["theme_key"]),
        "pack_path": e(f"{CONFIG['library']}/{meta['slug']}/index.html"),
    })
    return apply_theme(page, theme_css())


def status_line(meta):
    if meta["status"] == "superseded":
        return f'Superseded by <a href="../{meta["superseded_by"]}/index.html">{html.escape(meta["superseded_by"])}</a>.'
    if meta["status"] == "needs-review":
        return f"Needs review: its sources changed after it was checked on {meta['checked_date']}."
    return f"Current, checked against the code on {meta['checked_date']}."


def stamp_page(meta):
    """Rewrite the generated blocks in the pack (status banner, source list) from meta.json."""
    page = page_path(meta["slug"])
    if not os.path.isfile(page):
        return
    banner = (f'<!-- concept-status --><p class="concept-status concept-status--{meta["status"]}">'
              f'{status_line(meta)}</p><!-- /concept-status -->')
    sources = f"<!-- sources -->{sources_html(meta)}<!-- /sources -->"
    text = read(page)
    updated = SOURCES_BLOCK.sub(lambda _: sources, STATUS_BLOCK.sub(lambda _: banner, text))
    if updated != text:
        write(page, updated)


def reading_minutes(text):
    body = text[text.find("<main"):]
    for tag in ("svg", "pre", "script", "style"):
        body = re.sub(rf"<{tag}\b.*?</{tag}>", " ", body, flags=re.S)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    return max(1, math.ceil(words / 200)), words


# ---------- library index ----------

LIBRARY_CSS = """<style>
.sec-h { font: 700 26px/1.12 var(--display); color: var(--accent); margin: 32px 0 12px; }
ol.start { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; counter-reset: step; }
ol.start li { counter-increment: step; display: grid; grid-template-columns: 36px minmax(0, 1fr); gap: 2px 12px;
  padding: 12px 16px; border: 1px solid var(--line); border-radius: 10px; background: var(--tint); }
ol.start li::before { content: counter(step); grid-row: span 2; width: 32px; height: 32px; border-radius: 50%;
  background: var(--brand-fill); color: var(--on-blue); font: 700 18px/32px var(--display); text-align: center; }
ol.start a { font: 700 19px/1.2 var(--display); }
ol.start span { color: var(--muted); font-size: 15px; }
.filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.filters input, .filters select { font: 15px var(--body); color: var(--ink); background: var(--surface);
  border: 1px solid var(--line); border-radius: 8px; padding: 7px 12px; }
.filters input { flex: 1 1 220px; min-width: 0; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.card { background: var(--card); border: 1px solid var(--line); border-top: 3px solid var(--highlight);
  border-radius: 4px 4px 10px 10px; padding: 12px 14px; display: grid; gap: 6px; align-content: start; }
.card:hover { box-shadow: var(--shadow); background: var(--surface); }
.card h3 { margin: 0; font: 700 19px/1.15 var(--display); }
.card h3 a { text-decoration: none; }
.card p { margin: 0; font-size: 15px; }
.card .meta { font-size: 13px; color: var(--muted); }
.pills { display: flex; gap: 6px; flex-wrap: wrap; }
.pill { font: 600 12px/1 var(--body); padding: 5px 9px; border-radius: 99px; white-space: nowrap; }
.pill.type { color: var(--accent); background: var(--link-bg); }
.pill.current { color: var(--done); background: var(--done-bg); }
.pill.needs-review { color: var(--progress); background: var(--progress-bg); }
.pill.superseded { color: var(--todo); background: var(--todo-bg); }
.empty { color: var(--muted); }
</style>"""


def sorted_packs():
    order = {"current": 0, "needs-review": 1, "superseded": 2}
    return sorted(packs(), key=lambda m: (order[m["status"]], m["title"].lower()))


def readme(all_packs):
    start = sorted((m for m in all_packs if m["start_here"]), key=lambda m: m["start_here"])
    lines = [f"# {CONFIG['brand']}: concept library", "",
             "Short visual teaching packs: one design or architecture concept, proposal, piece of code or work "
             "process each. Open a pack's `index.html` in a browser (press **P** to present), or use its shared link.",
             "", "Generated by `.concepts/tool/scripts/concepts.py index` from each pack's `meta.json`. "
             "Don't edit this file by hand.", ""]
    if start:
        lines += ["## Start here", ""]
        lines += [f"{m['start_here']}. [{m['title']}]({m['slug']}/index.html): {m['summary']}" for m in start]
        lines.append("")
    lines += ["## All packs", "", "| Pack | Type | Owner | Status | Last checked | Shared link |",
              "|---|---|---|---|---|---|"]
    for m in all_packs:
        link = f"[open]({m['artifact_url']})" if m["artifact_url"] else ""
        status = m["status"] + (f" by `{m['superseded_by']}`" if m["superseded_by"] else "")
        lines.append(f"| [{m['title']}]({m['slug']}/index.html) | {m['type']} | {m['owner']} | {status} | "
                     f"{m['checked_date']} | {link} |")
    if not all_packs:
        lines.append("| *No packs yet* | | | | | |")
    return "\n".join(lines) + "\n"


def library_html(all_packs):
    e = lambda v: html.escape(str(v or ""))
    template = apply_theme(fill(read(TEMPLATE), {"theme_key": e(CONFIG["theme_key"])}), theme_css())
    head = template[template.index("<script>try"):template.index("</style>") + len("</style>")]
    start = sorted((m for m in all_packs if m["start_here"]), key=lambda m: m["start_here"])
    start_items = "".join(f'<li><a href="{e(m["slug"])}/index.html">{e(m["title"])}</a><span>{e(m["summary"])}</span></li>'
                          for m in start)
    cards = "".join(
        f'<article class="card" data-type="{e(m["type"])}" data-status="{e(m["status"])}">'
        f'<div class="pills"><span class="pill type">{e(TYPES[m["type"]])}</span>'
        f'<span class="pill {e(m["status"])}">{e(m["status"].replace("-", " "))}</span></div>'
        f'<h3><a href="{e(m["slug"])}/index.html">{e(m["title"])}</a></h3><p>{e(m["summary"])}</p>'
        f'<p class="meta">{e(m["owner"])} · for {e(m["audience"])} · {e(m["meeting_minutes"])} min · '
        f'checked {e(m["checked_date"])}'
        + (f' · <a href="{e(m["artifact_url"])}">shared link</a>' if m["artifact_url"] else "")
        + "</p></article>" for m in all_packs)
    options = "".join(f'<option value="{k}">{v}</option>' for k, v in TYPES.items())
    start_block = f'<h2 class="sec-h">Start here</h2><ol class="start">{start_items}</ol>' if start else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Concept Library</title>
{head}
{LIBRARY_CSS}
</head><body>
<header class="mast"><div class="wrap">
<div class="top"><span class="brand">{e(CONFIG["brand"])}</span>
<span class="actions"><button type="button" id="themeToggle"></button></span></div>
<h1>Concept library</h1>
<p class="lede">How we design, build and work, one concept at a time.</p>
</div></header>
<main class="wrap">
{start_block}
<h2 class="sec-h">All packs</h2>
<div class="filters"><input id="q" type="search" placeholder="Search packs" aria-label="Search packs">
<select id="type" aria-label="Type"><option value="">All types</option>{options}</select>
<select id="status" aria-label="Status"><option value="">All statuses</option><option value="current">Current</option>
<option value="needs-review">Needs review</option><option value="superseded">Superseded</option></select></div>
<div class="grid" id="grid">{cards or '<p class="empty">No packs yet.</p>'}</div>
</main><script>
const root = document.documentElement, toggle = document.getElementById('themeToggle');
function isDark() {{ return root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches; }}
function label() {{ toggle.textContent = isDark() ? 'Light mode' : 'Dark mode'; }}
toggle.addEventListener('click', () => {{
  root.dataset.theme = isDark() ? 'light' : 'dark';
  try {{ localStorage.setItem({json.dumps(CONFIG["theme_key"])}, root.dataset.theme); }} catch (e) {{}}
  label();
}});
label();
const q = document.getElementById('q'), t = document.getElementById('type'), s = document.getElementById('status');
function filter() {{
  const text = q.value.toLowerCase();
  document.querySelectorAll('.card').forEach(c => {{
    c.hidden = !(c.textContent.toLowerCase().includes(text) && (!t.value || c.dataset.type === t.value)
      && (!s.value || c.dataset.status === s.value));
  }});
}}
[q, t, s].forEach(el => el.addEventListener('input', filter));
</script></body></html>
"""


def write_index():
    all_packs = sorted_packs()
    write(os.path.join(library(), "README.md"), readme(all_packs))
    write(os.path.join(library(), "index.html"), library_html(all_packs))


# ---------- vendored tool ----------

def vendored_dir():
    return os.path.join(ROOT, ".concepts", "tool")


def vendored_version():
    script = os.path.join(vendored_dir(), "scripts", "concepts.py")
    if not os.path.isfile(script):
        return None
    m = re.search(r'^VERSION = "([^"]+)"', read(script), re.M)
    return m.group(1) if m else "0"


def version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "0"))


def running_vendored():
    return os.path.normcase(TOOL_DIR) == os.path.normcase(os.path.abspath(vendored_dir()))


def sync_tool(force=False):
    """Copy this tool into .concepts/tool/ so the project can run it without the plugin."""
    if running_vendored():
        return False
    current = vendored_version()
    if not force and current and version_tuple(current) >= version_tuple(VERSION):
        return False
    target = vendored_dir()
    if os.path.isdir(target):
        shutil.rmtree(target)
    shutil.copytree(os.path.join(TOOL_DIR, "scripts"), os.path.join(target, "scripts"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(TOOL_DIR, "assets"), os.path.join(target, "assets"))
    print(f"updated .concepts/tool to {VERSION}" + (f" (was {current})" if current else ""))
    return True


# ---------- commands ----------

def default_branch(root):
    ref = subprocess.run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=root,
                         capture_output=True, text=True).stdout.strip()
    if ref:
        return ref.split("/", 1)[1]
    for name in ("main", "master", "develop"):
        if subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{name}"], cwd=root,
                          capture_output=True).returncode == 0:
            return name
    return subprocess.run(["git", "branch", "--show-current"], cwd=root, capture_output=True,
                          text=True).stdout.strip() or "main"


def cmd_init(a):
    global ROOT, CONFIG
    root = os.path.abspath(a.root)
    if subprocess.run(["git", "rev-parse", "--git-dir"], cwd=root, capture_output=True).returncode != 0:
        fail(f"{root} is not inside a git repository")
    config_path = os.path.join(root, ".concepts", "config.json")
    existing = {}
    if os.path.isfile(config_path):
        with open(config_path, encoding="utf-8") as f:
            existing = json.load(f)
    config = {**DEFAULTS, **existing}
    for key in ("library", "brand", "theme", "branch", "theme_key"):
        value = getattr(a, key)
        if value:
            config[key] = value
    if "branch" not in existing and not a.branch:
        config["branch"] = default_branch(root)
    if not a.brand and "brand" not in existing:
        config["brand"] = os.path.basename(root)
    ROOT, CONFIG = root, config
    theme_css()
    write(config_path, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    sync_tool(force=True)
    write_index()
    kind, _ = remote_parts()
    print(f"concept library ready: {config['library']}/ (theme {config['theme']}, links to "
          f"{kind or 'relative paths'} on {config['branch']})")
    if a.hook:
        install_hook()


def cmd_new(a):
    if not SLUG.match(a.slug):
        fail(f"slug must be lowercase-with-hyphens: {a.slug}")
    if os.path.exists(os.path.join(library(), a.slug)):
        fail(f"pack already exists: {CONFIG['library']}/{a.slug}")
    for s in a.sources:
        if not os.path.exists(os.path.join(ROOT, s)):
            fail(f"source not found (paths are relative to the project folder {ROOT}): {s}")
    commit = git("rev-parse", "--short", "HEAD", check=False) or None
    meta = {
        "slug": a.slug, "title": a.title, "summary": a.summary, "type": a.type, "audience": a.audience,
        "owner": a.owner, "meeting_minutes": a.minutes, "sources": a.sources, "references": a.references,
        "created": today(), "checked_commit": commit, "checked_date": today(), "fingerprint": fingerprint(a.sources),
        "status": "current", "superseded_by": None, "start_here": None, "artifact_url": None,
    }
    write(page_path(a.slug), render_pack(meta))
    save(meta)
    write_index()
    print(f"created {CONFIG['library']}/{a.slug}/index.html - fill every [[...]], then run verify {a.slug}")


def cmd_verify(a):
    meta = load(a.slug)
    text = read(page_path(a.slug))
    left = PLACEHOLDER.findall(text)
    if left:
        fail(f"{a.slug} still has {len(left)} unfilled placeholder(s): {', '.join(left[:5])}")
    minutes, words = reading_minutes(text)
    write(page_path(a.slug), READ_BLOCK.sub(lambda _: f"<!-- read-time --><b>{minutes}</b> min read<!-- /read-time -->", text))
    meta.update(checked_commit=git("rev-parse", "--short", "HEAD", check=False) or None, checked_date=today(),
                fingerprint=fingerprint(meta["sources"]), status="current", superseded_by=None)
    save(meta)
    write_index()
    print(f"{a.slug}: current ({words} words, about {minutes} min to read, {len(meta['fingerprint'])} source files)")


def coerce(value):
    if value.lower() in ("null", "none", ""):
        return None
    return int(value) if value.isdigit() else value


def cmd_set(a):
    meta = load(a.slug)
    for pair in a.pairs:
        key, _, value = pair.partition("=")
        if key not in meta or key in ("slug", "checked_commit", "checked_date", "fingerprint", "created"):
            fail(f"cannot set {key}")
        if key == "type" and value not in TYPES:
            fail(f"type must be one of {', '.join(TYPES)}")
        meta[key] = [v for v in value.split(",") if v] if key in ("sources", "references") else coerce(value)
    save(meta)
    write_index()
    print(f"{a.slug}: updated {', '.join(p.partition('=')[0] for p in a.pairs)}")


def cmd_supersede(a):
    load(a.new)
    meta = load(a.old)
    meta.update(status="superseded", superseded_by=a.new, start_here=None)
    save(meta)
    write_index()
    print(f"{a.old}: superseded by {a.new}")


def cmd_remove(a):
    meta = load(a.slug)
    pointing = [m["slug"] for m in packs() if m["superseded_by"] == a.slug]
    if pointing:
        fail(f"{a.slug} supersedes {', '.join(pointing)}; point them elsewhere first "
             f"(set <slug> superseded_by=<other>) or supersede {a.slug} instead")
    if git("ls-files", "--", f"{CONFIG['library']}/{a.slug}", check=False) and not a.committed:
        fail(f"{a.slug} is already committed, so teammates may have it. Pass --committed to delete it anyway "
             f"(git history keeps a copy), or supersede it if a newer pack replaces it")
    shutil.rmtree(os.path.join(library(), a.slug))
    write_index()
    print(f"removed {CONFIG['library']}/{a.slug}")
    if meta["artifact_url"]:
        print(f"its shared copy still exists: {meta['artifact_url']}")


def cmd_check(a):
    touched = None
    if a.staged:
        touched = set(git("diff", "--cached", "--name-only", "--relative").splitlines())
    elif a.files:
        touched = {f.replace("\\", "/") for f in a.files}
    hits = []
    for meta in packs():
        if meta["status"] == "superseded":
            continue
        changed, added, removed = drift(meta)
        if touched is not None:
            changed, added, removed = ([p for p in group if p in touched] for group in (changed, added, removed))
        if changed or added or removed:
            hits.append((meta, changed, added, removed))
    if a.hook and hits:
        print("Teaching packs that describe code in this commit (update them, or run `check --mark`):")
    for meta, changed, added, removed in hits:
        print(f"{meta['slug']} ({meta['owner']}): {meta['title']}")
        for label, group in (("changed", changed), ("added", added), ("removed", removed)):
            for p in group:
                print(f"  {label:<8} {p}")
        if a.mark and meta["status"] != "needs-review":
            meta["status"] = "needs-review"
            save(meta)
    if a.mark and hits:
        write_index()
    if not hits and not a.hook:
        print("no packs affected")


def cmd_link(a):
    url = link_for(a.path, a.line, a.end)
    if not url:
        print("origin isn't a recognised host; use a relative path, or set \"link\" in .concepts/config.json "
              "to a template with {path} {branch} {line} {end}", file=sys.stderr)
        sys.exit(1)
    print(url)


def cmd_publish_copy(a):
    load(a.slug)
    out = a.out or os.path.join(tempfile.gettempdir(), "teach-a-concept", f"{a.slug}.html")
    write(out, WRAPPER.sub("", read(page_path(a.slug))))
    print(out)


def cmd_theme(a):
    theme_css(a.name)
    CONFIG["theme"] = a.name
    write(os.path.join(ROOT, ".concepts", "config.json"),
          json.dumps({k: v for k, v in CONFIG.items()}, indent=2, ensure_ascii=False) + "\n")
    css = theme_css()
    for meta in packs():
        write(page_path(meta["slug"]), apply_theme(read(page_path(meta["slug"])), css))
    write_index()
    print(f"theme {a.name} applied to {len(packs())} packs and the index")


HOOK_BODY = """#!/bin/sh
# {mark}: warns when staged changes touch code a teaching pack describes. Never blocks a commit.
cd "$(git rev-parse --show-toplevel)/{prefix}" 2>/dev/null || exit 0
[ -f .concepts/tool/scripts/concepts.py ] || exit 0
PY=python3; $PY -c "" 2>/dev/null || PY=python
$PY .concepts/tool/scripts/concepts.py check --staged --hook || true
exit 0
"""


def install_hook():
    hooks = os.path.join(ROOT, git("rev-parse", "--git-path", "hooks"))
    hook = os.path.join(hooks, "pre-commit")
    body = HOOK_BODY.format(mark=HOOK_MARK, prefix=git("rev-parse", "--show-prefix"))
    if os.path.isfile(hook) and HOOK_MARK not in read(hook):
        print(f"{hook} already exists, so it was left alone. Add these lines to it:\n")
        print("\n".join(body.splitlines()[2:-1]))
        return
    write(hook, body)
    os.chmod(hook, 0o755)
    print(f"installed {hook} (each teammate runs install-hook once; git doesn't share hooks)")


def cmd_list(_):
    for m in sorted_packs():
        print(f"{m['status']:<13} {m['slug']:<40} {m['type']:<9} {m['owner']}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--root", default=".")
    i.add_argument("--library")
    i.add_argument("--brand")
    i.add_argument("--theme")
    i.add_argument("--branch")
    i.add_argument("--theme-key", dest="theme_key")
    i.add_argument("--hook", action="store_true")
    n = sub.add_parser("new")
    n.add_argument("slug")
    n.add_argument("--title", required=True)
    n.add_argument("--summary", required=True)
    n.add_argument("--type", required=True, choices=list(TYPES))
    n.add_argument("--owner", required=True)
    n.add_argument("--audience", required=True)
    n.add_argument("--minutes", type=int, default=30)
    n.add_argument("--sources", nargs="*", default=[])
    n.add_argument("--references", nargs="*", default=[])
    sub.add_parser("verify").add_argument("slug")
    st = sub.add_parser("set")
    st.add_argument("slug")
    st.add_argument("pairs", nargs="+")
    su = sub.add_parser("supersede")
    su.add_argument("old")
    su.add_argument("new")
    rm = sub.add_parser("remove")
    rm.add_argument("slug")
    rm.add_argument("--committed", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("--files", nargs="*")
    c.add_argument("--staged", action="store_true")
    c.add_argument("--mark", action="store_true")
    c.add_argument("--hook", action="store_true", help=argparse.SUPPRESS)
    lk = sub.add_parser("link")
    lk.add_argument("path")
    lk.add_argument("line", nargs="?", type=int)
    lk.add_argument("end", nargs="?", type=int)
    sub.add_parser("theme").add_argument("name")
    pc = sub.add_parser("publish-copy")
    pc.add_argument("slug")
    pc.add_argument("--out", help="where to write it (default: a temp folder; the path is printed)")
    sub.add_parser("install-hook")
    sub.add_parser("index")
    sub.add_parser("list")
    sub.add_parser("sync-tool")
    a = p.parse_args(argv)
    try:
        if a.cmd == "init":
            return cmd_init(a)
        load_project()
        if a.cmd == "sync-tool":
            if not sync_tool(force=True):
                print("already running the project's copy; run sync-tool from the plugin to update it")
            return
        sync_tool()
        {"new": cmd_new, "verify": cmd_verify, "set": cmd_set, "supersede": cmd_supersede, "remove": cmd_remove,
         "check": cmd_check, "link": cmd_link, "theme": cmd_theme, "publish-copy": cmd_publish_copy, "list": cmd_list,
         "install-hook": lambda _: install_hook(), "index": lambda _: (write_index(), print("index rebuilt"))
         }[a.cmd](a)
    except ToolError as err:
        print(f"error: {err}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
