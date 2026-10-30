"""Markdown lint rules and link resolution."""

import tempfile
import unittest
from pathlib import Path

import check_links
import lint_markdown

GOOD = """# Title

Intro paragraph.

## Section Head

- one
- two

```text
fenced content
```
"""


class LintMarkdown(unittest.TestCase):
    def test_good_document(self):
        self.assertEqual(lint_markdown.lint_text(GOOD), [])

    def test_duplicate_top_heading(self):
        rules = [r for r, _, _ in lint_markdown.lint_text("# A\n\n# B\n")]
        self.assertIn("md01", rules)

    def test_heading_jump(self):
        rules = [r for r, _, _ in lint_markdown.lint_text("# A\n\n### B\n")]
        self.assertIn("md02", rules)

    def test_trailing_whitespace_and_tab(self):
        text = "# A\nline with space   \n\ttabbed line\n"
        rules = [r for r, _, _ in lint_markdown.lint_text(text)]
        self.assertIn("md03", rules)
        self.assertIn("md04", rules)

    def test_long_line(self):
        text = "# A\n" + "x" * 200 + "\n"
        rules = [r for r, _, _ in lint_markdown.lint_text(text)]
        self.assertIn("md05", rules)

    def test_open_fence(self):
        rules = [r for r, _, _ in lint_markdown.lint_text("# A\n\n```text\ncontent\n")]
        self.assertIn("md06", rules)

    def test_leftover_marker(self):
        rules = [r for r, _, _ in lint_markdown.lint_text("# A\n\nTODO: finish\n")]
        self.assertIn("md07", rules)

    def test_missing_final_newline(self):
        rules = [r for r, _, _ in lint_markdown.lint_text("# A")]
        self.assertIn("md08", rules)

    def test_blank_run(self):
        rules = [r for r, _, _ in lint_markdown.lint_text("# A\n\n\n\n")]
        self.assertIn("md09", rules)


class CheckLinks(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name: str, text: str) -> None:
        (self.root / name).write_text(text, encoding="utf-8")

    def test_relative_link_resolves(self):
        self.write("a.md", "# A\n\nSee [b](b.md).\n")
        self.write("b.md", "# B\n")
        self.assertEqual(check_links.check_file(self.root, Path("a.md"), False), [])

    def test_broken_link_reported(self):
        self.write("a.md", "# A\n\nSee [x](missing.md).\n")
        findings = check_links.check_file(self.root, Path("a.md"), False)
        self.assertTrue(any("broken link" in f for f in findings))

    def test_anchor_resolves(self):
        self.write("a.md", "# A\n\nSee [s](b.md#section-head).\n")
        self.write("b.md", "# B\n\n## Section Head\n")
        self.assertEqual(check_links.check_file(self.root, Path("a.md"), False), [])

    def test_missing_anchor_reported(self):
        self.write("a.md", "# A\n\nSee [s](b.md#nope).\n")
        self.write("b.md", "# B\n")
        findings = check_links.check_file(self.root, Path("a.md"), False)
        self.assertTrue(any("anchor" in f for f in findings))

    def test_mailto_reported(self):
        self.write("a.md", "# A\n\nWrite [us](mailto:test).\n")
        findings = check_links.check_file(self.root, Path("a.md"), False)
        self.assertTrue(any("mailto" in f for f in findings))

    def test_link_inside_fence_ignored(self):
        self.write(
            "a.md",
            "# A\n\n```text\nSee [x](missing.md).\n```\n",
        )
        self.assertEqual(check_links.check_file(self.root, Path("a.md"), False), [])


if __name__ == "__main__":
    unittest.main()
