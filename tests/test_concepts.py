import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "plugins", "teach-a-concept", "skills", "teach-a-concept",
                      "scripts", "concepts.py")
spec = importlib.util.spec_from_file_location("concepts", SCRIPT)
concepts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(concepts)


def sh(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Project(unittest.TestCase):
    """A throwaway git repo whose project folder is `app/`, below the repo root, like a Unity project."""

    remote = "https://github.com/acme/widgets.git"

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.root = os.path.join(self.repo, "app")
        os.makedirs(os.path.join(self.root, "src", "net"))
        sh(self.repo, "init", "-q", "-b", "main")
        sh(self.repo, "config", "user.email", "t@example.com")
        sh(self.repo, "config", "user.name", "T")
        sh(self.repo, "config", "core.autocrlf", "false")
        sh(self.repo, "remote", "add", "origin", self.remote)
        self.put("src/score.py", "def score(): return 1\n")
        self.put("src/net/api.py", "API = 1\n")
        self.commit("start")
        self.cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.repo, ignore_errors=True)

    def put(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def commit(self, message):
        sh(self.repo, "add", "-A")
        sh(self.repo, "commit", "-q", "-m", message)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                concepts.main(list(argv))
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue() + err.getvalue()

    def read(self, rel):
        with open(os.path.join(self.root, rel), encoding="utf-8") as f:
            return f.read()

    def meta(self, slug):
        return json.loads(self.read(f"docs/concepts/{slug}/meta.json"))

    def init(self, *extra):
        code, out = self.run_cli("init", "--brand", "Acme", *extra)
        self.assertEqual(code, 0, out)

    def new(self, slug="scoring", *sources):
        code, out = self.run_cli("new", slug, "--title", "Server scoring", "--summary", "Why the server scores",
                                 "--type", "concept", "--owner", "Ana", "--audience", "devs",
                                 "--sources", *(sources or ("src/score.py", "src/net")))
        self.assertEqual(code, 0, out)

    def fill(self, slug="scoring"):
        path = os.path.join(self.root, f"docs/concepts/{slug}/index.html")
        text = concepts.PLACEHOLDER.sub("filled words here", self.read(f"docs/concepts/{slug}/index.html"))
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)


class InitTests(Project):
    def test_init_writes_config_vendors_tool_and_empty_index(self):
        self.init()
        config = json.loads(self.read(".concepts/config.json"))
        self.assertEqual(config["brand"], "Acme")
        self.assertEqual(config["branch"], "main")
        self.assertEqual(config["library"], "docs/concepts")
        self.assertTrue(os.path.isfile(os.path.join(self.root, ".concepts/tool/scripts/concepts.py")))
        self.assertTrue(os.path.isfile(os.path.join(self.root, ".concepts/tool/assets/themes/nus.css")))
        self.assertIn("*No packs yet*", self.read("docs/concepts/README.md"))

    def test_rerunning_init_keeps_existing_settings(self):
        self.init("--branch", "develop", "--theme", "nus")
        code, _ = self.run_cli("init")
        config = json.loads(self.read(".concepts/config.json"))
        self.assertEqual((config["branch"], config["theme"], config["brand"]), ("develop", "nus", "Acme"))

    def test_unknown_theme_is_refused(self):
        code, out = self.run_cli("init", "--theme", "neon")
        self.assertEqual(code, 2)
        self.assertIn("theme not found: neon", out)

    def test_commands_outside_a_library_explain_how_to_start(self):
        code, out = self.run_cli("list")
        self.assertEqual(code, 2)
        self.assertIn("Run `concepts.py init`", out)


class PackTests(Project):
    def setUp(self):
        super().setUp()
        self.init()
        self.new()

    def test_new_fills_header_and_leaves_teaching_placeholders(self):
        page = self.read("docs/concepts/scoring/index.html")
        self.assertNotIn("{{", page)
        self.assertIn("<h1>Server scoring</h1>", page)
        self.assertIn('<p class="eyebrow">Concept</p>', page)
        self.assertIn("https://github.com/acme/widgets/blob/main/app/src/score.py", page)
        self.assertIn("[[observable verb + outcome]]", page)
        self.assertIn("--accent: #3445A8", page)

    def test_verify_refuses_unfilled_placeholders(self):
        code, out = self.run_cli("verify", "scoring")
        self.assertEqual(code, 2)
        self.assertIn("unfilled placeholder", out)

    def test_verify_stamps_reading_time_and_fingerprints_sources(self):
        self.fill()
        code, out = self.run_cli("verify", "scoring")
        self.assertEqual(code, 0, out)
        self.assertIn("<!-- read-time --><b>1</b> min read<!-- /read-time -->", self.read("docs/concepts/scoring/index.html"))
        self.assertEqual(sorted(self.meta("scoring")["fingerprint"]), ["src/net/api.py", "src/score.py"])

    def test_index_lists_pack_and_start_here_order(self):
        self.run_cli("set", "scoring", "start_here=1", "artifact_url=https://claude.ai/x")
        readme = self.read("docs/concepts/README.md")
        self.assertIn("1. [Server scoring](scoring/index.html): Why the server scores", readme)
        self.assertIn("[open](https://claude.ai/x)", readme)
        self.assertIn('<h1>Concept library</h1>', self.read("docs/concepts/index.html"))

    def test_set_rejects_protected_keys(self):
        code, out = self.run_cli("set", "scoring", "fingerprint=x")
        self.assertEqual(code, 2)
        self.assertIn("cannot set fingerprint", out)


class CheckTests(Project):
    def setUp(self):
        super().setUp()
        self.init()
        self.new()

    def test_unchanged_sources_report_nothing_even_after_commits(self):
        self.commit("add library")
        self.put("src/other.py", "x = 1\n")
        self.commit("unrelated")
        code, out = self.run_cli("check")
        self.assertEqual(out.strip(), "no packs affected")

    def test_edit_add_and_delete_are_each_reported(self):
        self.put("src/score.py", "def score(): return 2\n")
        self.put("src/net/new.py", "N = 1\n")
        os.remove(os.path.join(self.root, "src/net/api.py"))
        code, out = self.run_cli("check")
        self.assertIn("changed  src/score.py", out)
        self.assertIn("added    src/net/new.py", out)
        self.assertIn("removed  src/net/api.py", out)

    def test_line_ending_changes_alone_are_not_drift(self):
        with open(os.path.join(self.root, "src/score.py"), "w", encoding="utf-8", newline="\r\n") as f:
            f.write("def score(): return 1\n")
        _, out = self.run_cli("check")
        self.assertEqual(out.strip(), "no packs affected")

    def test_files_filter_limits_report_to_those_files(self):
        self.put("src/score.py", "def score(): return 2\n")
        _, out = self.run_cli("check", "--files", "src/net/api.py")
        self.assertEqual(out.strip(), "no packs affected")
        _, out = self.run_cli("check", "--files", "src/score.py")
        self.assertIn("scoring (Ana)", out)

    def test_staged_filter_uses_the_index(self):
        self.commit("library")
        self.put("src/score.py", "def score(): return 2\n")
        _, out = self.run_cli("check", "--staged")
        self.assertEqual(out.strip(), "no packs affected")
        sh(self.repo, "add", "app/src/score.py")
        _, out = self.run_cli("check", "--staged")
        self.assertIn("changed  src/score.py", out)

    def test_mark_sets_needs_review_and_rewrites_the_banner(self):
        self.put("src/score.py", "def score(): return 2\n")
        self.run_cli("check", "--mark")
        self.assertEqual(self.meta("scoring")["status"], "needs-review")
        self.assertIn("concept-status--needs-review", self.read("docs/concepts/scoring/index.html"))
        self.assertIn("| needs-review |", self.read("docs/concepts/README.md"))

    def test_verify_after_review_clears_the_drift(self):
        self.put("src/score.py", "def score(): return 2\n")
        self.run_cli("check", "--mark")
        self.fill()
        self.run_cli("verify", "scoring")
        _, out = self.run_cli("check")
        self.assertEqual(out.strip(), "no packs affected")
        self.assertEqual(self.meta("scoring")["status"], "current")


class LifecycleTests(Project):
    def setUp(self):
        super().setUp()
        self.init()
        self.new("old")
        self.new("new")

    def test_supersede_points_old_at_new(self):
        self.run_cli("supersede", "old", "new")
        meta = self.meta("old")
        self.assertEqual((meta["status"], meta["superseded_by"]), ("superseded", "new"))
        self.assertIn('href="../new/index.html"', self.read("docs/concepts/old/index.html"))

    def test_remove_refuses_a_pack_that_supersedes_another(self):
        self.run_cli("supersede", "old", "new")
        code, out = self.run_cli("remove", "new")
        self.assertEqual(code, 2)
        self.assertIn("new supersedes old", out)
        self.assertTrue(os.path.isdir(os.path.join(self.root, "docs/concepts/new")))

    def test_remove_uncommitted_pack_deletes_it_and_reindexes(self):
        code, out = self.run_cli("remove", "old")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "docs/concepts/old")))
        self.assertNotIn("old/index.html", self.read("docs/concepts/README.md"))

    def test_remove_committed_pack_needs_the_flag(self):
        self.commit("library")
        code, out = self.run_cli("remove", "old")
        self.assertEqual(code, 2)
        self.assertIn("--committed", out)
        code, _ = self.run_cli("remove", "old", "--committed")
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.root, "docs/concepts/old")))

    def test_theme_switch_rethemes_every_pack_and_the_index(self):
        code, out = self.run_cli("theme", "nus")
        self.assertEqual(code, 0, out)
        for rel in ("docs/concepts/old/index.html", "docs/concepts/new/index.html", "docs/concepts/index.html"):
            self.assertIn("--accent: #003D7C", self.read(rel))
            self.assertNotIn("--accent: #3445A8", self.read(rel))

    def test_custom_theme_file_in_the_project(self):
        self.put("brand.css", ":root { --accent: #123456; }")
        self.run_cli("theme", "brand.css")
        self.assertIn("--accent: #123456", self.read("docs/concepts/old/index.html"))


class HookTests(Project):
    def setUp(self):
        super().setUp()
        self.init()

    def test_install_hook_writes_a_non_blocking_hook_that_enters_the_project(self):
        self.run_cli("install-hook")
        with open(os.path.join(self.repo, ".git/hooks/pre-commit"), encoding="utf-8") as f:
            hook = f.read()
        self.assertIn('cd "$(git rev-parse --show-toplevel)/app/"', hook)
        self.assertIn("check --staged --hook || true", hook)

    def test_existing_hook_is_left_alone(self):
        path = os.path.join(self.repo, ".git/hooks/pre-commit")
        with open(path, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\necho mine\n")
        _, out = self.run_cli("install-hook")
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "#!/bin/sh\necho mine\n")
        self.assertIn("left alone", out)


class SyncTests(Project):
    def test_older_vendored_copy_is_upgraded(self):
        self.init()
        script = os.path.join(self.root, ".concepts/tool/scripts/concepts.py")
        with open(script, encoding="utf-8") as f:
            text = f.read()
        with open(script, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace(f'VERSION = "{concepts.VERSION}"', 'VERSION = "0.0.1"'))
        _, out = self.run_cli("list")
        self.assertIn(f"updated .concepts/tool to {concepts.VERSION} (was 0.0.1)", out)


class LinkTests(Project):
    def link_with(self, remote, *args):
        sh(self.repo, "remote", "set-url", "origin", remote)
        code, out = self.run_cli("link", "src/score.py", *args)
        return out.strip()

    def setUp(self):
        super().setUp()
        self.init("--branch", "develop")

    def test_azure_https(self):
        self.assertEqual(
            self.link_with("https://me@dev.azure.com/org/My%20Proj/_git/My%20Repo", "10", "20"),
            "https://dev.azure.com/org/My%20Proj/_git/My%20Repo?path=/app/src/score.py&version=GBdevelop"
            "&line=10&lineEnd=20&lineStartColumn=1&lineEndColumn=1&lineStyle=plain&_a=contents")

    def test_azure_ssh(self):
        self.assertEqual(self.link_with("git@ssh.dev.azure.com:v3/org/proj/repo"),
                         "https://dev.azure.com/org/proj/_git/repo?path=/app/src/score.py&version=GBdevelop")

    def test_github_ssh_with_lines(self):
        self.assertEqual(self.link_with("git@github.com:acme/widgets.git", "3", "9"),
                         "https://github.com/acme/widgets/blob/develop/app/src/score.py#L3-L9")

    def test_gitlab_nested_group(self):
        self.assertEqual(self.link_with("https://gitlab.com/acme/tools/widgets.git", "4"),
                         "https://gitlab.com/acme/tools/widgets/-/blob/develop/app/src/score.py#L4-4")

    def test_bitbucket(self):
        self.assertEqual(self.link_with("git@bitbucket.org:acme/widgets.git", "2", "5"),
                         "https://bitbucket.org/acme/widgets/src/develop/app/src/score.py#lines-2:5")

    def test_unknown_host_exits_with_advice(self):
        out = self.link_with("https://git.example.org/acme/widgets.git")
        self.assertIn("isn't a recognised host", out)

    def test_custom_link_template(self):
        config_path = os.path.join(self.root, ".concepts/config.json")
        config = json.loads(self.read(".concepts/config.json"))
        config["link"] = "https://code.example.org/{branch}/{path}#{line}"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f)
        code, out = self.run_cli("link", "src/score.py", "7")
        self.assertEqual(out.strip(), "https://code.example.org/develop/app/src/score.py#7")


if __name__ == "__main__":
    unittest.main()
