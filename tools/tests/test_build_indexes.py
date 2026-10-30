"""Catalog building: index lines, domain pages, determinism."""

import json
import tempfile
import unittest
from pathlib import Path

import build_indexes

REGISTRY = """domains:
  - name: libraries
    display: Libraries
    count: 0
"""


def manifest() -> dict:
    return {
        "id": "AB12CD34",
        "slug": "demo-tool",
        "title": "Demo Tool",
        "summary": "A small demonstration of the catalog layout.",
        "domain": "libraries",
        "tags": ["demo"],
        "stack": ["python"],
        "status": "active",
        "version": "0.1.0",
        "created_at": "2026-10-30T01:02:03Z",
    }


class BuildIndexes(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "registry").mkdir()
        (self.root / "registry" / "domains.yaml").write_text(REGISTRY, encoding="utf-8")
        pdir = self.root / "projects" / "2026" / "10" / "demo-tool-AB12CD34"
        pdir.mkdir(parents=True)
        (pdir / "project.json").write_text(json.dumps(manifest()), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_index_line_written(self):
        build_indexes.build(self.root)
        lines = (self.root / "catalog" / "index.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["id"], "AB12CD34")
        self.assertEqual(entry["path"], "projects/2026/10/demo-tool-AB12CD34")

    def test_domain_page_written(self):
        build_indexes.build(self.root)
        page = self.root / "catalog" / "by-domain" / "libraries.md"
        text = page.read_text(encoding="utf-8")
        self.assertIn("Demo Tool", text)
        self.assertIn(
            "(../../projects/2026/10/demo-tool-AB12CD34/README.md)", text
        )

    def test_landing_page_written(self):
        build_indexes.build(self.root)
        text = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn("# Incubator", text)
        self.assertIn("Total projects: 1", text)

    def test_rebuild_is_deterministic(self):
        build_indexes.build(self.root)
        first = (
            (self.root / "README.md").read_bytes(),
            (self.root / "catalog" / "index.jsonl").read_bytes(),
            (self.root / "CATALOG.md").read_bytes(),
        )
        build_indexes.build(self.root)
        second = (
            (self.root / "README.md").read_bytes(),
            (self.root / "catalog" / "index.jsonl").read_bytes(),
            (self.root / "CATALOG.md").read_bytes(),
        )
        self.assertEqual(first, second)

    def test_empty_tree_writes_keep_files(self):
        import shutil

        shutil.rmtree(self.root / "projects")
        build_indexes.build(self.root)
        self.assertTrue((self.root / "catalog" / "by-domain" / ".gitkeep").exists())
        self.assertIn(
            "No projects yet.",
            (self.root / "README.md").read_text(encoding="utf-8"),
        )

    def test_page_names(self):
        self.assertEqual(build_indexes.page_names("x", 1), ["x.md"])
        self.assertEqual(
            build_indexes.page_names("x", 3), ["x.md", "x-2.md", "x-3.md"]
        )

    def test_summary_cell_is_truncated(self):
        project = manifest()
        project["path"] = "projects/2026/10/demo-tool-AB12CD34"
        project["summary"] = "word " * 40
        row = build_indexes.row_for(project, include_tags=True)
        self.assertIn("...", row)
        self.assertLessEqual(len(row), 300)


if __name__ == "__main__":
    unittest.main()
