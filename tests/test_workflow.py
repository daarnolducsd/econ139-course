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
import zipfile

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
            "materials": {
                "intro": {"title": "Intro", "kind": "slides", "source": "slides/00_intro.pdf"},
                "pset1": {"title": "Problem Set 1", "kind": "assignment", "source": "pset/pset1/pset1.pdf",
                          "solutions": {"source": "pset/pset1/pset1_solutions.pdf", "release": False}},
            },
            "syllabus": {"source": "syllabus/current.pdf"},
        }
        self.schedule = {"weeks": [
            {"number": number, "title": f"Topic {number}",
             "materials": ["intro"] if number == 1 else [],
             "assignments": [{"material": "pset1"}] if number == 1 else []}
            for number in range(1, 11)]}
        for relative in ("slides/00_intro.pdf", "pset/pset1/pset1.pdf",
                         "pset/pset1/pset1_solutions.pdf", "syllabus/current.pdf"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(PDF)
        self.save_config()

    def save_config(self):
        (self.site / "course.json").write_text(json.dumps(self.config))
        (self.site / "schedule.json").write_text(json.dumps(self.schedule))

    def build(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return builder.build(self.site, **kwargs)

    def add_downloads(self):
        for key, kind, source, data in (
            ("sample-data", "data", "data/cps/sample.csv", b"age,wage\n25,100\n"),
            ("sample-code", "code", "code/cps/analyze.py", b"print('original')\n"),
        ):
            path = self.root / source
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            self.config["materials"][key] = {"title": key, "kind": kind, "source": source}
        self.schedule["weeks"][0]["resources"] = ["sample-data", "sample-code"]
        self.save_config()

    def add_topic_bundle(self):
        self.add_downloads()
        for key in ("sample-data", "sample-code"):
            entry = self.config["materials"][key]
            entry["destination"] = builder.material_destination(entry)
            old = self.root / entry["source"]
            new = self.root / "materials/cps" / entry["kind"] / old.name
            new.parent.mkdir(parents=True, exist_ok=True)
            old.rename(new)
            entry["source"] = new.relative_to(self.root).as_posix()
        (self.root / "materials/cps/README.md").write_text("# CPS instructions\n")
        (self.root / "materials/cps/code/unlisted_answer_key.do").write_text("PRIVATE\n")
        (self.root / "materials/cps/outputs").mkdir()
        (self.root / "materials/cps/outputs/results.csv").write_text("not a public input\n")
        self.config["bundles"] = {"cps": {"title": "CPS", "readme": "materials/cps/README.md",
                                          "materials": ["sample-data", "sample-code"]}}
        self.save_config()

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
        self.config["materials"]["intro"]["published"] = False
        self.save_config()
        _, removed = self.build()
        self.assertEqual(removed, ["slides/00_intro.pdf"])
        self.assertNotIn("slides/00_intro.pdf", (self.site / "index.html").read_text())
        self.assertEqual((self.root / "slides/00_intro.pdf").read_bytes(), PDF)

    def test_solution_release_boundary_and_revocation(self):
        self.config["materials"]["pset1"]["solutions"]["release"] = "2030-10-15"
        page, files = builder.collect_content(self.config, self.root, datetime.date(2030, 10, 14), schedule=self.schedule)
        self.assertNotIn("psets/pset1_solutions.pdf", files)
        self.assertIn("solutions available October 15, 2030", page)
        page, files = builder.collect_content(self.config, self.root, datetime.date(2030, 10, 15), schedule=self.schedule)
        self.assertIn("psets/pset1_solutions.pdf", files)
        self.assertIn('href="psets/pset1_solutions.pdf"', page)
        self.config["materials"]["pset1"]["solutions"]["release"] = True
        self.save_config()
        self.build()
        self.config["materials"]["pset1"]["solutions"]["release"] = False
        self.save_config()
        _, removed = self.build()
        self.assertEqual(removed, ["psets/pset1_solutions.pdf"])

    def test_bad_mapping_and_release_dates_are_rejected(self):
        for source in ("../outside.pdf", "/outside.pdf"):
            with self.subTest(source=source):
                self.config["syllabus"]["source"] = source
                with self.assertRaises(builder.BuildError):
                    builder.collect_content(self.config, self.root, schedule=self.schedule)
        self.config["syllabus"]["source"] = "syllabus/current.pdf"
        self.config["materials"]["pset1"]["solutions"]["release"] = "2030-02-30"
        with self.assertRaises(builder.BuildError):
            builder.collect_content(self.config, self.root, schedule=self.schedule)
        self.config["materials"]["pset1"]["solutions"]["release"] = False
        self.config["materials"]["duplicate"] = {"title": "Duplicate", "kind": "review", "source": "slides/00_intro.pdf"}
        with self.assertRaises(builder.BuildError):
            builder.collect_content(self.config, self.root, schedule=self.schedule)

    def test_missing_stylesheet_blocks_build_before_copying_pdfs(self):
        (self.site / "assets/style.css").unlink()
        before = self.snapshot()
        with self.assertRaises(builder.BuildError):
            self.build()
        self.assertEqual(before, self.snapshot())

    def test_moving_material_changes_week_without_changing_pdf(self):
        self.build()
        original = self.snapshot()["slides/00_intro.pdf"]
        self.schedule["weeks"][0]["materials"] = []
        self.schedule["weeks"][2]["materials"] = ["intro"]
        self.save_config()
        self.assertEqual(self.build(), (["index.html", "SOURCE_FILES.md"], []))
        page = (self.site / "index.html").read_text()
        week1 = page.split('<section id="week-1"')[1].split('</section>')[0]
        week3 = page.split('<section id="week-3"')[1].split('</section>')[0]
        self.assertNotIn("slides/00_intro.pdf", week1)
        self.assertIn("slides/00_intro.pdf", week3)
        self.assertEqual(original, self.snapshot()["slides/00_intro.pdf"])

    def test_continuation_deck_is_linked_twice_and_copied_once(self):
        self.schedule["weeks"][1]["materials"] = ["intro"]
        page, files = builder.collect_content(self.config, self.root, schedule=self.schedule)
        self.assertEqual(page.count('href="slides/00_intro.pdf"'), 2)
        self.assertEqual(list(files).count("slides/00_intro.pdf"), 1)

    def test_invalid_schedule_preserves_existing_output(self):
        self.build()
        valid = json.dumps(self.schedule)
        for change in ("missing_week", "duplicate_week", "unknown_id", "duplicate_id", "bad_url"):
            with self.subTest(change=change):
                self.schedule = json.loads(valid)
                weeks = self.schedule["weeks"]
                if change == "missing_week":
                    weeks.pop()
                elif change == "duplicate_week":
                    weeks[-1]["number"] = 1
                elif change == "unknown_id":
                    weeks[0]["materials"] = ["typo"]
                elif change == "duplicate_id":
                    weeks[0]["materials"] = ["intro", "intro"]
                else:
                    weeks[0]["readings"] = [{"title": "Bad link", "url": "javascript:alert(1)"}]
                self.save_config()
                before = self.snapshot()
                with self.assertRaises(builder.BuildError):
                    self.build()
                self.assertEqual(before, self.snapshot())

    def test_week_order_and_textbook_links(self):
        self.schedule["weeks"].reverse()
        self.schedule["weeks"][0]["readings"] = [{"title": "Chapter 1", "url": "https://example.org/chapter1"}]
        self.save_config()
        self.build()
        page = (self.site / "index.html").read_text()
        positions = [page.index(f'<section id="week-{n}"') for n in range(1, 11)]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('href="https://example.org/" target="_blank" rel="noopener noreferrer"', page)
        self.assertIn('href="https://example.org/chapter1" target="_blank" rel="noopener noreferrer"', page)

    def test_download_updates_use_only_exact_mapped_sources(self):
        self.add_downloads()
        self.build()
        duplicate = self.root / "archive/analyze.py"
        duplicate.parent.mkdir()
        duplicate.write_text("print('unmapped duplicate')\n")
        self.assertEqual(self.build(), ([], []))
        source = self.root / "code/cps/analyze.py"
        original_time = source.stat().st_mtime_ns
        updated = source.read_bytes().replace(b"original", b"modified")
        source.write_bytes(updated)
        os.utime(source, ns=(original_time, original_time))
        self.assertEqual(self.build(), (["downloads/code/cps/analyze.py"], []))
        self.assertEqual((self.site / "downloads/code/cps/analyze.py").read_bytes(), updated)
        data = self.root / "data/cps/sample.csv"
        data.write_bytes(data.read_bytes().replace(b"100", b"200"))
        self.assertEqual(self.build(), (["downloads/data/cps/sample.csv"], []))
        guide = (self.site / "SOURCE_FILES.md").read_text()
        self.assertIn("code/cps/analyze.py | downloads/code/cps/analyze.py | 1", guide)
        self.assertNotIn("archive/analyze.py", guide)

    def test_download_validation_failure_preserves_output(self):
        self.add_downloads()
        self.build()
        before = self.snapshot()
        source = self.root / "code/cps/analyze.py"
        for data in (None, b"", b"invalid\0code", b"\xff"):
            with self.subTest(data=data):
                if data is None:
                    source.unlink()
                else:
                    source.write_bytes(data)
                with self.assertRaises(builder.BuildError):
                    self.build()
                self.assertEqual(before, self.snapshot())

    def test_shared_downloads_are_copied_once_and_can_be_revoked(self):
        self.add_downloads()
        self.schedule["weeks"][1]["resources"] = ["sample-code"]
        self.save_config()
        self.build()
        page = (self.site / "index.html").read_text()
        self.assertEqual(page.count('href="downloads/code/cps/analyze.py"'), 2)
        self.assertIn('aria-label="sample-code (PY)" download', page)
        self.config["materials"]["sample-code"]["published"] = False
        self.save_config()
        _, removed = self.build()
        self.assertEqual(removed, ["downloads/code/cps/analyze.py"])
        self.assertNotIn("analyze.py", (self.site / "index.html").read_text())
        self.assertTrue((self.root / "code/cps/analyze.py").exists())

    def test_unlinked_assignment_reminders_render_without_canvas(self):
        self.schedule["weeks"][0]["assignments"].append({"title": "Reading reflection", "note": "Due this week"})
        self.save_config()
        self.build()
        page = (self.site / "index.html").read_text()
        self.assertIn("Reading reflection", page)
        self.assertIn("Due this week", page)
        self.assertNotIn("Canvas", page)

    def test_topic_migration_preserves_urls_and_bundles_only_explicit_members(self):
        self.add_topic_bundle()
        self.build()
        self.assertFalse((self.root / "code/cps/analyze.py").exists())
        self.assertTrue((self.site / "downloads/code/cps/analyze.py").exists())
        with zipfile.ZipFile(self.site / "downloads/bundles/cps.zip") as archive:
            self.assertEqual(archive.namelist(), ["cps/README.md", "cps/code/analyze.py", "cps/data/sample.csv"])
            self.assertEqual(archive.read("cps/code/analyze.py"), (self.root / "materials/cps/code/analyze.py").read_bytes())
        self.assertIn('href="downloads/bundles/cps.zip" download', (self.site / "index.html").read_text())
        self.assertEqual(self.build(), ([], []))
        source = self.root / "materials/cps/code/analyze.py"
        timestamp = source.stat().st_mtime_ns
        os.utime(source, ns=(timestamp + 10_000_000, timestamp + 10_000_000))
        self.assertEqual(self.build(), ([], []))
        source.write_text("print('updated')\n")
        self.assertEqual(self.build(), (["downloads/code/cps/analyze.py", "downloads/bundles/cps.zip"], []))
        with zipfile.ZipFile(self.site / "downloads/bundles/cps.zip") as archive:
            self.assertEqual(archive.read("cps/code/analyze.py"), source.read_bytes())

    def test_readme_updates_refresh_zip_and_missing_readme_blocks_all_writes(self):
        self.add_topic_bundle()
        self.build()
        readme = self.root / "materials/cps/README.md"
        readme.write_text("# Updated instructions\n")
        self.assertEqual(self.build(), (["downloads/guides/cps-README.md", "downloads/bundles/cps.zip"], []))
        before = self.snapshot()
        readme.unlink()
        with self.assertRaises(builder.BuildError):
            self.build()
        self.assertEqual(before, self.snapshot())

    def test_hidden_resources_disappear_from_zip_and_all_hidden_removes_bundle(self):
        self.add_topic_bundle()
        self.build()
        self.config["materials"]["sample-code"]["published"] = False
        self.save_config()
        self.build()
        with zipfile.ZipFile(self.site / "downloads/bundles/cps.zip") as archive:
            self.assertNotIn("cps/code/analyze.py", archive.namelist())
        self.config["materials"]["sample-data"]["published"] = False
        self.save_config()
        _, removed = self.build()
        self.assertIn("downloads/bundles/cps.zip", removed)
        self.assertIn("downloads/guides/cps-README.md", removed)
        self.assertNotIn("cps.zip", (self.site / "index.html").read_text())

    def test_unsafe_destinations_and_assignment_bundle_members_are_rejected(self):
        self.add_topic_bundle()
        self.build()
        valid = json.dumps(self.config)
        for value in ("../escaped.py", "downloads/../escaped.py", "/absolute.py", "slides/escaped.py", "downloads/code/wrong.csv"):
            with self.subTest(destination=value):
                self.config = json.loads(valid)
                self.config["materials"]["sample-code"]["destination"] = value
                self.save_config()
                before = self.snapshot()
                with self.assertRaises(builder.BuildError):
                    self.build()
                self.assertEqual(before, self.snapshot())
        self.config = json.loads(valid)
        self.config["bundles"]["cps"]["materials"].append("pset1")
        self.save_config()
        with self.assertRaises(builder.BuildError):
            self.build()


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

    def test_schedule_only_change_is_published(self):
        self.publish()
        self.schedule["weeks"][0]["materials"] = []
        self.schedule["weeks"][1]["materials"] = ["intro"]
        self.save_config()
        self.publish("Move intro to week 2")
        changed = self.git("show", "--format=", "--name-only", "HEAD").stdout.split()
        self.assertEqual(sorted(changed), ["SOURCE_FILES.md", "index.html", "schedule.json"])
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, self.git("rev-parse", "origin/main").stdout)

    def test_data_and_code_source_changes_publish_with_existing_command(self):
        self.add_downloads()
        self.publish()
        source = self.root / "code/cps/analyze.py"
        source.write_text("print('updated code')\n")
        data = self.root / "data/cps/sample.csv"
        data.write_text("age,wage\n25,200\n")
        self.publish("Update data and code")
        changed = self.git("show", "--format=", "--name-only", "HEAD").stdout.split()
        self.assertEqual(sorted(changed), ["downloads/code/cps/analyze.py", "downloads/data/cps/sample.csv"])
        self.assertEqual(self.git("show", "HEAD:downloads/code/cps/analyze.py").stdout, source.read_text())

    def test_source_listing_works_without_git_and_without_writes(self):
        self.add_downloads()
        shutil.rmtree(self.site / ".git")
        before = self.snapshot()
        result = self.publish("--sources", cwd=Path(tempfile.gettempdir()))
        self.assertIn("code/cps/analyze.py | downloads/code/cps/analyze.py", result.stdout)
        self.assertEqual(before, self.snapshot())

    def test_topic_edit_publishes_individual_copy_and_zip_together(self):
        self.add_topic_bundle()
        self.publish()
        source = self.root / "materials/cps/code/analyze.py"
        source.write_text("print('new teaching code')\n")
        self.publish("Update CPS package")
        changed = self.git("show", "--format=", "--name-only", "HEAD").stdout.split()
        self.assertEqual(sorted(changed), ["downloads/bundles/cps.zip", "downloads/code/cps/analyze.py"])
        self.assertEqual(self.git("show", "HEAD:downloads/code/cps/analyze.py").stdout, source.read_text())

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
