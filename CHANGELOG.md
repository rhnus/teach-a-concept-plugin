# Changelog

## 1.0.1 (2026-10-22)

- **`publish-copy <slug>`** writes a pack without its `<!doctype>`, `<html>`, `<head>` and `<body>` wrapper,
  for hosts such as Claude Artifacts that add their own. The skill publishes that copy instead of the library
  file.
- **Long source lists fold.** A pack built from more than three sources shows "Built from N sources" in its
  header, expanding to the full list on click. The list is a generated block, so `set <slug> sources=…`
  now refreshes the header too.
- **Present mode keys** no longer stop working when a key event targets the document itself (no focused
  element), and clicking a "Built from" toggle while presenting no longer changes slide.

Projects pick up the new tool copy in `.concepts/tool/` the next time the skill runs there. Packs made with
1.0.0 keep their old header and script until they are recreated or edited by hand.

## 1.0.0 (2026-10-22)

First release: the teach-a-concept skill, the pack template with Present mode, `default` and `nus` themes,
and `concepts.py` (init, new, verify, check, set, supersede, remove, link, theme, install-hook, index, list).
