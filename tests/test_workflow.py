"""Behavior checks using temporary course folders and local Git remotes."""
import contextlib
import datetime
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

WEBSITE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("site_build", WEBSITE / "build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
PDF = b"%PDF-1.4\noriginal test material\n%%EOF\n"


class CourseFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.site = self.root / "website"
        (self.site / "assets").mkdir(parents=True)
        (self.site / "assets/style.css").write_text("body { color: black; }\n")
        self.config = {
            "course": {"title": "Test Course", "term": "Test Term",
                       "instructor": "Test Instructor", "textbook_url": "https://example.org/"},
            "lectures": [{"topic": "Intro", "decks": [
                {"label": "Slides", "source": "slides/00_intro.pdf"}]}],
            "reviews": [], "datasets": [],
            "psets": [{"title": "Problem Set 1", "source": "pset/pset1/pset1.pdf",
                       "solutions": {"source": "pset/pset1/pset1_solutions.pdf", "release": False}}],
            "syllabus": {"source": "syllabus/current.pdf"},
        }
        for relative in ("slides/00_intro.pdf", "pset/pset1/pset1.pdf",
                         "pset/pset1/pset1_solutions.pdf", "syllabus/current.pdf"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(PDF)
        self.save_config()

    def save_config(self):
        (self.site / "course.json").write_text(json.dumps(self.config))

    def build(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return builder.build(self.site, **kwargs)

    def snapshot(self):
        return {p.relative_to(self.site).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.site.rglob("*") if p.is_file() and ".git" not in p.parts}


class BuildTests(CourseFixture):
    def test_incremental_copy_detects_same_size_same_timestamp_changes(self):
        self.build()
        before = self.snapshot()
        self.assertEqual(self.build(), ([], []))
        self.assertEqual(before, self.snapshot())
        source = self.root / "slides/00_intro.pdf"
        timestamp = source.stat().st_mtime_ns
        replacement = PDF.replace(b"original", b"modified")
        source.write_bytes(replacement)
        os.utime(source, ns=(timestamp, timestamp))
        changed, removed = self.build()
        self.assertEqual(changed, ["slides/00_intro.pdf"])
        self.assertEqual(removed, [])
        self.assertEqual((self.site / changed[0]).read_bytes(), replacement)
        self.assertEqual(before["index.html"], self.snapshot()["index.html"])

    def test_missing_empty_and_non_pdf_source_preserve_all_existing_output(self):
        self.build()
        before = self.snapshot()
        source = self.root / "syllabus/current.pdf"
        for bad_data in (None, b"", b"not a PDF"):
            with self.subTest(bad_data=bad_data):
                if bad_data is None:
                    source.unlink()
                else:
                    source.write_bytes(bad_data)
                with self.assertRaises(builder.BuildError):
                    self.build()
                self.assertEqual(before, self.snapshot())

    def test_check_mode_reports_changes_without_writes(self):
        before = self.snapshot()
        changed, removed = self.build(check=True)
        self.assertIn("index.html", changed)
        self.assertEqual(removed, [])
        self.assertEqual(before, self.snapshot())

    def test_unmapped_and_unreleased_materials_are_never_copied(self):
        (self.root / "slides/unlisted.pdf").write_bytes(PDF)
        (self.root / "pset/pset1/pset1_solutions.pdf").unlink()
        self.build()
        self.assertFalse((self.site / "slides/unlisted.pdf").exists())
        self.assertFalse((self.site / "psets/pset1_solutions.pdf").exists())

    def test_hiding_materials_removes_stale_pdf_and_link(self):
        self.build()
        self.config["lectures"][0]["published"] = False
        self.save_config()
        _, removed = self.build()
        self.assertEqual(removed, ["slides/00_intro.pdf"])
        self.assertNotIn("slides/00_intro.pdf", (self.site / "index.html").read_text())
        self.assertEqual((self.root / "slides/00_intro.pdf").read_bytes(), PDF)

    def test_solution_release_boundary_and_revocation(self):
        self.config["psets"][0]["solutions"]["release"] = "2030-10-15"
        page, files = builder.collect_content(self.config, self.root, datetime.date(2030, 10, 14))
        self.assertNotIn("psets/pset1_solutions.pdf", files)
        self.assertIn("solutions available October 15, 2030", page)
        page, files = builder.collect_content(self.config, self.root, datetime.date(2030, 10, 15))
        self.assertIn("psets/pset1_solutions.pdf", files)
        self.assertIn('href="psets/pset1_solutions.pdf"', page)
        self.config["psets"][0]["solutions"]["release"] = True
        self.save_config()
        self.build()
        self.config["psets"][0]["solutions"]["release"] = False
        self.save_config()
        _, removed = self.build()
        self.assertEqual(removed, ["psets/pset1_solutions.pdf"])

    def test_bad_mapping_and_release_dates_are_rejected(self):
        for source in ("../outside.pdf", "/outside.pdf"):
            with self.subTest(source=source):
                self.config["syllabus"]["source"] = source
                with self.assertRaises(builder.BuildError):
                    builder.collect_content(self.config, self.root)
        self.config["syllabus"]["source"] = "syllabus/current.pdf"
        self.config["psets"][0]["solutions"]["release"] = "2030-02-30"
        with self.assertRaises(builder.BuildError):
            builder.collect_content(self.config, self.root)
        self.config["psets"][0]["solutions"]["release"] = False
        self.config["reviews"] = [{"title": "Duplicate", "source": "slides/00_intro.pdf"}]
        with self.assertRaises(builder.BuildError):
            builder.collect_content(self.config, self.root)

    def test_missing_stylesheet_blocks_build_before_copying_pdfs(self):
        (self.site / "assets/style.css").unlink()
        before = self.snapshot()
        with self.assertRaises(builder.BuildError):
            self.build()
        self.assertEqual(before, self.snapshot())


class PublishTests(CourseFixture):
    def setUp(self):
        super().setUp()
        self.env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
                    "GIT_TERMINAL_PROMPT": "0", "PYTHONDONTWRITEBYTECODE": "1"}
        for name in ("build.py", "publish.sh", "AGENTS.md", "README.md", "PROJECT_NOTES.md", ".gitignore"):
            shutil.copy2(WEBSITE / name, self.site / name)
        (self.site / "tests").mkdir()
        (self.site / "tests/placeholder.txt").write_text("test fixture\n")
        self.git("init", "--quiet", "-b", "main")
        self.git("config", "user.name", "Workflow Test")
        self.git("config", "user.email", "test@example.org")
        self.git("config", "commit.gpgsign", "false")
        self.remote = self.root / "remote.git"
        self.git("init", "--quiet", "--bare", str(self.remote))
        self.git("remote", "add", "origin", str(self.remote))

    def git(self, *args, check=True):
        return subprocess.run(["git", *args], cwd=self.site, env=self.env,
                              capture_output=True, text=True, check=check, timeout=30)

    def publish(self, *args, check=True, cwd=None):
        return subprocess.run(["bash", str(self.site / "publish.sh"), *args],
                              cwd=cwd or self.root, env=self.env,
                              capture_output=True, text=True, check=check, timeout=30)

    def test_first_push_changed_pdf_and_unchanged_noop(self):
        (self.site / "unrelated.txt").write_text("Do not publish me\n")
        self.publish()
        self.assertEqual(self.git("rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "origin/main")
        self.assertNotIn("unrelated.txt", self.git("ls-files").stdout)
        head = self.git("rev-parse", "HEAD").stdout
        result = self.publish()
        self.assertEqual(head, self.git("rev-parse", "HEAD").stdout)
        self.assertIn("No local commits waiting", result.stdout)
        (self.root / "slides/00_intro.pdf").write_bytes(PDF + b"updated\n")
        self.publish("Update intro")
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), "Update intro")
        self.assertEqual(self.git("show", "--format=", "--name-only", "HEAD").stdout.strip(), "slides/00_intro.pdf")

    def test_failed_push_is_retried_without_another_commit(self):
        self.publish()
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        (self.root / "slides/00_intro.pdf").write_bytes(PDF + b"update\n")
        result = self.publish(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local commit is saved", result.stderr)
        pending_head = self.git("rev-parse", "HEAD").stdout
        hook.unlink()
        self.publish()
        self.assertEqual(pending_head, self.git("rev-parse", "HEAD").stdout)
        self.assertEqual(pending_head, self.git("rev-parse", "origin/main").stdout)

    def test_failed_first_push_is_retried_and_establishes_upstream(self):
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        self.assertNotEqual(self.publish(check=False).returncode, 0)
        pending_head = self.git("rev-parse", "HEAD").stdout
        hook.unlink()
        self.publish()
        self.assertEqual(pending_head, self.git("rev-parse", "HEAD").stdout)
        self.assertEqual(self.git("rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "origin/main")

    def test_validation_failure_never_commits_or_pushes(self):
        self.publish()
        before = self.snapshot()
        head = self.git("rev-parse", "HEAD").stdout
        (self.root / "slides/00_intro.pdf").write_bytes(b"")
        result = self.publish(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(head, self.git("rev-parse", "HEAD").stdout)
        self.assertEqual(before, self.snapshot())

    def test_unrelated_staged_file_blocks_publish_before_build(self):
        self.publish()
        (self.site / "unrelated.txt").write_text("private draft\n")
        self.git("add", "unrelated.txt")
        before = self.snapshot()
        head = self.git("rev-parse", "HEAD").stdout
        (self.root / "slides/00_intro.pdf").write_bytes(PDF + b"update\n")
        result = self.publish(check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unrelated file is staged", result.stderr)
        self.assertEqual(head, self.git("rev-parse", "HEAD").stdout)
        self.assertEqual(before, self.snapshot())

    def test_check_and_local_work_without_repository_and_from_other_directory(self):
        shutil.rmtree(self.site / ".git")
        before = self.snapshot()
        self.publish("--check", cwd=Path(tempfile.gettempdir()))
        self.assertEqual(before, self.snapshot())
        self.publish("--local", cwd=Path(tempfile.gettempdir()))
        self.assertTrue((self.site / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
