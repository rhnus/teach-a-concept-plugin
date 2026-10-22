# teach-a-concept

A Claude Code plugin that turns a design, proposal, piece of code or work process into a short, visual,
presentable **teaching pack** for your team, and keeps every pack in a **concept library** inside your repo.

Each pack has:

1. a learning objective,
2. a plain explanation with diagrams,
3. a real example from your project with links to the code,
4. discussion questions tagged *decision*, *application* or *risk*,
5. a list of assumptions, open points and items to clarify.

It is sized to fit a meeting (15, 30 or 60 minutes).

- **Presentable.** Every pack is one HTML file with a **Present** button. Press `P` for full-screen slides,
  use the arrow keys to move between them, and press `Esc` to return to the page. It has light and dark
  modes and opens by double-clicking, with no build step.
- **One source of truth.** Packs live in the repo next to the code. They're reviewed in PRs and indexed in
  `README.md` and `index.html`, and there's a "Start here" reading order for new joiners.
- **Stays honest.** Each pack records a fingerprint of the source files it describes. When those files
  change, the pack is flagged *needs review*, both in the index and in a banner on the pack itself. This
  works through rebases and squash merges.
- **Works with any git host.** Code links are built for Azure DevOps, GitHub, GitLab and Bitbucket, or
  from a link template you supply.

## Install

In the Claude Code CLI:

```
/plugin marketplace add rhnus/teach-a-concept-plugin
/plugin install teach-a-concept@teach-a-concept
```

In VS Code, type `/plugins` to open **Manage plugins**. Add `rhnus/teach-a-concept-plugin` on the **Marketplaces** tab, then
install **teach-a-concept** from the **Plugins** tab. Updates arrive when the plugin's version number changes.
Turn on auto-update for this marketplace in the same dialog, or run
`claude plugin update teach-a-concept@teach-a-concept`.

Then, in any project, ask Claude:

> set up the concept library here

Claude asks for a brand line and a theme (`default`, `nus`, or your own CSS), then runs `init`. The `init`
step writes `.concepts/config.json` and a copy of the tool to `.concepts/tool/`, so teammates, git hooks
and CI can run the check without the plugin. Commit both.

### Point the whole team at it

Add this to the project's committed `.claude/settings.json`. It registers the marketplace for every teammate
who trusts the project folder and marks the plugin as wanted. Each teammate still installs the plugin once,
using the install line above or `claude plugin install teach-a-concept@teach-a-concept --scope project`.
Until they do, Claude Code reports that the plugin is enabled but not installed.

```json
{
  "extraKnownMarketplaces": {
    "teach-a-concept": { "source": { "source": "github", "repo": "rhnus/teach-a-concept-plugin" } }
  },
  "enabledPlugins": { "teach-a-concept@teach-a-concept": true }
}
```

## Use

Ask in plain words. You don't need to name the skill.

| You want to… | Say something like |
|---|---|
| Explain code you just wrote | "Make a teaching pack from my last commit for a 15-min standup" |
| Explain a proposal or advice | "Turn that recommendation into a pack for Thursday's design review" |
| Document a new process | "Walk the team through the new release process" |
| Present | "Open the caching pack", then press **P** |
| Update a pack | "The auth code changed, update the session-tokens pack" |
| Find out-of-date packs | "Which concept packs are out of date?" |
| Build onboarding | "Put the architecture overview first in Start here" |
| Remove a pack | "Delete the pack I just made" (Claude confirms first) |
| Change the look | "Switch the concept library to the nus theme" |

Say the **meeting length** and the **decisions the meeting needs to reach** to get the best result.

## Run the tool directly

You don't need Claude for this. From anywhere in the project:

```sh
python .concepts/tool/scripts/concepts.py list          # every pack and its status
python .concepts/tool/scripts/concepts.py check         # packs whose sources changed
python .concepts/tool/scripts/concepts.py check --mark  # ...and flag them needs-review
python .concepts/tool/scripts/concepts.py install-hook  # warn (never block) on commits that touch a pack's sources
python .concepts/tool/scripts/concepts.py publish-copy <slug>  # the pack without its <html>/<head> wrapper, for hosts that add one
```

`check` exits 0 either way, so it's safe in CI as an informational step. `--help` lists every command.

## Themes

The built-in themes are `default` (neutral indigo with an amber highlight) and `nus` (NUS blue `#003D7C`
with orange `#EF7C00`). To make your own:

1. Copy `plugins/teach-a-concept/skills/teach-a-concept/assets/themes/default.css` into your project.
2. Change the colours.
3. Run `concepts.py theme path/to/your.css`. This re-themes every pack and the index.

## Layout in your project

```
.concepts/config.json        library folder, brand, theme, link branch
.concepts/tool/              copy of the tool (updated automatically when the plugin is newer)
docs/concepts/README.md      generated index
docs/concepts/index.html     generated, searchable index page
docs/concepts/<slug>/index.html   a pack
docs/concepts/<slug>/meta.json    its owner, sources, fingerprints and status
```

## Develop

The tool uses only the Python 3.8+ standard library and git.

```sh
python -m unittest discover -s tests
```

Bump `VERSION` in `concepts.py` and `version` in both `plugin.json` and `.claude-plugin/marketplace.json`
together. Projects pick up the new tool copy the next time the skill runs there.

## Licence

[MIT](LICENSE)
