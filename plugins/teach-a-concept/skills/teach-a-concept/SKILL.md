---
name: teach-a-concept
description: Turn one design or architecture concept, proposal, recommendation, piece of implemented code, or new work process into a short, visual, presentable teaching pack for a development team — a learning objective, a plain explanation with diagrams, a real project example, discussion questions, and a labelled list of assumptions and open points — sized to fit a meeting and kept in the repo's concept library. Use when asked to explain, teach, walk the team through, onboard someone to, present or "make a visual doc of" an architecture decision, a design pattern, a proposal or RFC, advice Claude just gave, code that was just implemented, a refactor, a pipeline, or a new workflow or process; when preparing a design review, tech talk, brown-bag or team meeting; or when someone says "help the team understand X" or "make this easier to follow". Also use it to set up a concept library in a project, to update, present, list, find or remove a pack, to build an onboarding reading list, to change the library's theme, or to check which packs are out of date after a code change. Use it even when the request doesn't say "teaching pack" — any request to make a design, change or process understandable to other people belongs here.
---


# Teach one concept to the team

The team reads a pack like this once, a day before or at the start of a meeting, and then talks about it.
So it has one job: get everyone to the same mental model fast enough that the meeting spends its time on
the open decisions, not on catching up. That shapes every rule below — **one concept, grounded in this
project, visual first, short enough to finish inside the meeting, honest about what isn't known.**

## What can come in

The source can be any of these. Each one hides its concept in a different place, so pull it out first.

| Source | Where the concept is | The picture that usually teaches it |
|---|---|---|
| **Proposal / RFC / design note** | the change and the problem it solves | before → after diagram; the option space with the chosen one marked |
| **Advice or a recommendation** (often Claude's own, earlier in the chat) | the rule of thumb and when it applies | decision flow ("if X, do Y"), with the project case walked through it |
| **Implemented code** (a diff, commit, branch or files) | the structure and the flow of data/control | component/ownership diagram + a sequence of one real call path, with `file:line` anchors |
| **New work process** | who does what, in what order, with which checks | swimlane or step flow with gates; a "first time doing it" worked run |
| **A general concept** (e.g. "event bus", "singleton", "server-side scoring") | the idea itself | the generic shape once, then the same shape drawn over this project |

If the request mixes several (say, a proposal plus its implementation), still teach **one** concept and use
the others as evidence for it. A second concept becomes a "next session" line in the open points, not a
second half of the pack — two half-taught ideas leave the room with neither.

## Inputs to collect

1. **The concept** — one sentence. If you can't say it in one, it's too broad.
2. **The audience's current knowledge** — what they already know and use, and what's new to them.
3. **Approved project context** — the files, diff, design note, or conversation the user points at.
4. **Meeting length** — sets the size of the pack (see budget below).
5. **The questions or decisions** the meeting needs to reach.

Take what the conversation already gives you before asking. In a repo, the code, `CLAUDE.md`, docs and
recent commits often answer 3 and part of 2. Ask in **one** batch only for what's genuinely missing,
typically meeting length and the decisions to discuss; if the user just wants a pack and doesn't care,
default to a 30-minute meeting and say so in the assumptions.

## Workflow

Each step ends with a check. Apply the review rule at every check:

- **Continue** when the material is grounded in a source you read and is accurate.
- **Revise** when it's unclear, too broad, or won't fit the time — narrow it, cut it, re-draw it.
- **Stop and ask** when essential context is missing, a claim can't be verified against a source, or the
  material may not be approved for sharing (customer data, credentials, unreleased plans the user hasn't
  cleared, other people's private messages). Say exactly what you need; don't fill the gap with a guess.

### 1. Define the learning objective (reason carefully)

Write one objective in the form *"After this session, the team can ___."* with an observable verb —
explain, choose between, trace, apply, spot — not "understand" or "be aware of".

Check: is it **one** concept, **relevant** to work the team is actually doing, and **achievable** in the
meeting time for this audience? An objective that needs three diagrams of prerequisites isn't achievable
in 30 minutes — narrow it, and move the prerequisites to "assumed knowledge".

### 2. Gather project context

Read the sources the user named, and only as much else as you need to make the example correct. For code,
open the actual files and note `path:line` for every claim you'll make about them; for a proposal, quote
or paraphrase the relevant passage; for a process, find where it lives today (skills, scripts, docs).

Check every fact you'll put in the pack against a source you read. Keep a private list of
*claim → source* while you work; anything without a source either gets one, gets labelled as an
assumption, or gets cut. **Never invent project details** — names of classes, numbers, owners, dates,
"the team already does X". A confident wrong example teaches the wrong model and costs more than a gap.

### 3. Draft the explanation (reason carefully)

Build it in this order, because people need the shape before the details:

1. **The problem it solves** — two or three sentences, in this project's terms.
2. **The core idea** — one diagram plus a short paragraph. The diagram carries the explanation; the text
   says what to look at in it. Pick the picture from the table above.
3. **How it works here** — the project example: the real components, the real flow, one concrete
   walkthrough ("when a user submits the form, …"). For code, link the files.
4. **Where it bends or breaks** — the trade-off, the footgun, the case it doesn't cover. This is what a
   team actually needs to use the concept safely, and it seeds the discussion.

Write for the stated audience: define each term the first time it appears, use the project's own names,
prefer short sentences. Check technical accuracy (does the diagram match the code/source exactly?),
clarity (could someone new to it redraw the core diagram from memory?) and audience fit.

### 4. Prepare discussion questions (reason carefully)

Write 3–5 questions that move the meeting toward the decisions it needs. Good ones are open, specific to
this project, and have a real answer the room doesn't have yet:

- a **decision** question ("Should the billing service adopt this now, or after the migration?"),
- an **application** question ("Which of our modules would change if we applied this?"),
- a **risk** question ("What breaks first if this assumption is wrong?").

Check each one: does it serve the objective, and does it stand only on verified facts? A question that
smuggles in an unverified premise ("Given that the backend is the bottleneck, …") goes to the open points
instead, phrased as something to confirm.

### 5. Assemble and check the pack (quick pass)

Assemble the pack in the structure below, then check it quickly for:

- **Coherence** — objective, explanation, example and questions are all about the same one concept.
- **Timing** — fits the budget below. If it's over, cut detail, not the questions.
- **Completeness** — every section present; every diagram labelled; every assumption marked.
- **Confidentiality** — nothing in it the user hasn't approved for this audience. When unsure, list the
  item in the open points and leave it out of the body.

## Timing budget

Assume people read about 200 words a minute and that the meeting should spend at least half its time
on discussion.

| Meeting | Reading/explaining | Words in the body (excl. diagrams) | Diagrams | Questions |
|---|---|---|---|---|
| 15 min | ~5 min | ≤ 600 | 1–2 | 2–3 |
| 30 min | ~10 min | ≤ 1,200 | 2–3 | 3–4 |
| 60 min | ~20 min | ≤ 2,000 | 3–4 | 4–5 |

`concepts.py verify` counts the words and stamps the reading time into the header for you.

## Pack structure

Use exactly these sections, in this order — the team learns where to look:

1. **Header** — the concept as a title, audience, meeting length, estimated reading time, the source(s)
   it was built from, and the date.
2. **Learning objective** — the one sentence from step 1.
3. **Concept explanation** — problem, core idea with its diagram, where it bends or breaks.
4. **Project example** — the real walkthrough with its diagram and source links.
5. **Discussion questions** — numbered, each tagged decision / application / risk.
6. **Assumptions, open points and items to clarify** — three labelled lists:
   *Assumed* (what you took as true without a source, and why), *Open* (what the meeting should settle),
   *To clarify* (what you need from someone before this is fully right, and who). An empty list says
   "None" — that's information too.

Mark any inline assumption in the body with a visible "Assumption" tag that matches an entry in section 6,
so a reader never mistakes a guess for a fact.

## The concept library: where packs live

Every pack is saved in the project's concept library, in the repo. The library is the master copy: it's
reviewed in PRs, every teammate already has it, and its history says who changed what. A published Artifact
link (or any other share) is only a **presenting copy** of a library page.

```
.concepts/config.json   ← library folder, brand, theme, link branch (committed)
.concepts/tool/         ← a copy of this skill's script and assets, so teammates, hooks and CI can run it
<library>/README.md     ← generated index: "Start here" reading order + every pack (renders on any git host)
<library>/index.html    ← the same index as a searchable page
<library>/<slug>/index.html  ← the pack
<library>/<slug>/meta.json   ← owner, audience, sources and their fingerprints, status, shared link
```

All routine library work goes through **this skill's** script: `python "${CLAUDE_SKILL_DIR}/scripts/concepts.py"`
(use `python3` where `python` isn't on the path). Run it from anywhere inside the project; it finds the
project by its `.concepts/` folder, and keeps `.concepts/tool/` up to date when the skill is newer. Source
paths are relative to the project folder (the one holding `.concepts/`). **Never hand-edit `README.md`,
the library `index.html` or `meta.json`** — the script regenerates them, and a hand edit is lost on the next
run.

| Command | When |
|---|---|
| `init [--brand …] [--theme default\|nus\|<file.css>] [--library docs/concepts] [--branch …] [--hook]` | First use in a project (see below). Re-running keeps existing settings and only changes what you pass. |
| `new <slug> --title … --summary … --type proposal\|advice\|code\|process\|concept --owner … --audience … --minutes 30 --sources <paths> [--references <ticket, meeting, …>]` | Starting a pack. Writes the page from the template with the header, theme and linked sources already filled. `sources` are the files and folders the pack describes; that's what the out-of-date check watches, so list every file the example relies on. |
| `link <path> [line] [endLine]` | Every source link in the pack body. Prints a web URL on the configured branch for Azure DevOps, GitHub, GitLab or Bitbucket, so links work from the repo and from a shared copy alike. |
| `verify <slug>` | After you've confirmed a pack matches its sources. Refuses while any `[[…]]` placeholder is left, stamps the reading time, fingerprints the sources and sets it current. |
| `check [--files f …] [--staged] [--mark]` | Lists packs whose source files changed, were added or were removed since they were verified. Compares file contents, so rebases and squash merges don't matter. `--mark` sets them to needs-review. |
| `set <slug> key=value …` | `artifact_url=<url>`, `start_here=<n>` (new-joiner reading order), `owner`, `sources` (comma-separated), etc. |
| `supersede <old> <new>` | A newer pack replaces an older one. The old one stays, so the reasoning behind past decisions can still be found. |
| `remove <slug> [--committed]` | A pack made by mistake. Refuses if another pack is superseded by it, and refuses an already-committed pack unless `--committed` is passed. Prints the pack's shared link, which it does not delete. |
| `theme <name or file.css>` | Re-themes every pack and the index. |
| `publish-copy <slug> [--out <file>]` | Writes the pack without its `<!doctype>`, `<html>`, `<head>` and `<body>` wrapper and prints the path, for hosts that add their own (the `Artifact` tool does). The library file stays the master; never hand-strip a copy. |
| `install-hook` | A git pre-commit hook that warns, never blocks, when a commit touches a pack's sources. Each teammate runs it once; git doesn't share hooks. |
| `index` / `list` | Rebuild the index / list every pack with its status. |

The owner is the person the user names, or the user themselves; ask only if neither is clear.

### First use in a project

If the project has no `.concepts/config.json`, set the library up before the first pack. Ask the user, in
one question, for anything you can't infer:

- **brand**: the line shown above every pack title, e.g. the product or team name (default: the folder name);
- **theme**: `default` (neutral indigo), `nus` (NUS blue and orange), or a `.css` file of their own made by
  copying `${CLAUDE_SKILL_DIR}/assets/themes/default.css` into the project and changing the colours;
- **library folder** (default `docs/concepts`) and the **branch** links should point at (default: the remote's
  default branch; teams that merge into `develop` usually want `develop`).

Then run `init` with those values, and offer two optional extras:

- `install-hook`, for teammates who commit outside Claude;
- pointing the whole team at the plugin: add the marketplace and plugin to the project's committed
  `.claude/settings.json` (`extraKnownMarketplaces` and `enabledPlugins`; the plugin's README has the exact
  lines). That registers the marketplace for everyone who trusts the folder, but each teammate still installs
  the plugin once, so tell the user to pass the install line on.

If the project has its own commit workflow (a commit skill, a PR checklist), suggest adding one step to it:
`python .concepts/tool/scripts/concepts.py check --files <files being committed>`. Show the user that step
rather than editing their workflow unasked.

## Writing the page

`new` writes the page from `${CLAUDE_SKILL_DIR}/assets/pack-template.html`. Replace every `[[…]]` with the
content from steps 1–5 and leave everything else in place. The template carries the six sections, the theme,
the status banner, a light/dark toggle and **Present mode**, so every pack looks the same and can be
presented straight from the page with no separate deck:

- The **Present** button (or `P`) shows one `section.slide` per screen. Arrow keys, space or a click move
  between slides; `Esc` returns to the reading view. Write for both: each slide should make sense on a
  projector by itself. **Split a long section into two slides** (copy the `<section class="slide">` element)
  rather than letting it scroll. A good slide is one heading, one diagram or a few short paragraphs, and
  nothing a presenter would skip.
- Leave the marked blocks alone: `/* theme:start */…/* theme:end */`, `<!-- concept-status -->…`,
  `<!-- read-time -->…`, `<!-- sources -->…`. The script rewrites them; change sources with `set`, and the
  header's "Built from" line follows (more than three fold behind a count).
- Pack-specific styles (diagram classes, a step list, a table) go in a second `<style>` block or just before
  the template's `</style>`, built from the theme tokens.
- Keep it **one self-contained file**: inline CSS, inline SVG, no external images or scripts (the only
  external request is the Google Fonts stylesheet, which falls back to system fonts offline).
- If the `artifact-design` and `artifact-diagramming` skills are available, load them before writing: they
  cover how to pick and draw a diagram that shows the real mechanism, legible in light and dark themes.
- Colour diagrams with the template's tokens so they follow the theme: `var(--new)` (accent), `var(--existing)`
  (slate), `var(--highlight)` (warm accent), `var(--risk)` (red), `var(--ink)` and `var(--line)` for text and
  strokes. One meaning per colour, with a legend.
- Before → after, swimlanes, sequence and component diagrams cover almost every source type above. Use a
  table instead when the content is a comparison of options.
- Code appears as short excerpts (≤ 15 lines) linked with `concepts.py link`, enough to anchor the diagram
  and never a dump.

If the user also wants another format (a slide deck, a document in their docs tool), make it from the
library page and keep the same six sections; the library page stays the master.

## The whole flow

**New pack:** set up the library if needed → steps 1–5 → `new` → fill the page → `verify` → if the
`Artifact` tool is available, run `publish-copy <slug>` and publish the file it prints (it starts private;
republish that same path for later updates) and `set <slug> artifact_url=<url>` → if it belongs in the
new-joiner path, `set <slug> start_here=<n>`.
Don't commit: leave the files for the user's normal commit, and list them in your handover.

**Updating a pack** (the code changed, the user has feedback, or `check` flagged it): read the current page and
the changed sources, revise only what's now wrong, re-run the step-5 check, `verify`, then `publish-copy` and
republish to the **same** shared URL from `meta.json` (pass it as `url` in a later session) so links people
already have keep working.

**Reviewing the library** ("which packs are out of date?"): `check`, then for each hit say what changed and
whether the pack's claims still hold. Update the ones that are wrong; `verify` the ones that still hold.
Don't mark a pack current without reading the change.

**Removing a pack** ("I didn't mean to make that", "delete the X pack"):
1. Confirm which pack, by title and slug, before touching anything.
2. Not yet committed → `remove <slug>`. That's the whole local undo.
3. Already committed → ask whether it was a mistake or has been replaced. If a newer pack replaces it, use
   `supersede` instead, so links people have still lead somewhere. If it was a mistake, run
   `remove <slug> --committed` and leave the deletion for the user's next commit; git history keeps a copy.
4. If `meta.json` had an `artifact_url`, ask whether to delete the shared copy too, and only then delete it.
   Deleting it breaks the link for everyone who has it, and it can't be undone.

**Presenting:** point the user at the shared link (or the local `index.html`) and the Present button. If the
pack's status isn't current, say so before they present it.

## Handing it over

End with a short message: the shared link, the library path, the objective in one line, the items in
*To clarify* that the user should resolve before the meeting, and the files to commit. Don't paste the pack
into the chat.
