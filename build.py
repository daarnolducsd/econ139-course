#!/usr/bin/env python3
"""Validate and incrementally build the course site from course.json.

Source paths are relative to the parent ECON139 folder. Only explicitly listed,
published PDFs are copied. This script does not compile PowerPoint/LaTeX or push.
"""

import argparse
import datetime
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import unquote, urlsplit

SITE = Path(__file__).resolve().parent


class BuildError(ValueError):
    """An actionable content/configuration error, detected before writing."""


def esc(value):
    return html.escape(value, quote=True)


def fmt_date(value):
    return f"{value.strftime('%B')} {value.day}, {value.year}"


def record(value, context, required=(), optional=()):
    if not isinstance(value, dict):
        raise BuildError(f"{context}: expected an object")
    missing = set(required) - value.keys()
    unknown = value.keys() - set(required) - set(optional)
    if missing or unknown:
        raise BuildError(f"{context}: missing fields {sorted(missing)}; "
                         f"unknown fields {sorted(unknown)}")
    return value


def text_field(entry, key):
    value = entry[key]
    if not isinstance(value, str) or not value.strip():
        raise BuildError(f"{key}: expected a nonempty string")
    return value


def published(entry):
    value = entry.get("published", True)
    if not isinstance(value, bool):
        raise BuildError("published must be true or false")
    return value


def solution_status(release, today):
    if release is False or release is None:
        return "private", None
    if release is True:
        return "released", None
    if not isinstance(release, str):
        raise BuildError("solutions.release must be false, true, or YYYY-MM-DD")
    try:
        due = datetime.date.fromisoformat(release)
    except ValueError as error:
        raise BuildError(f"Invalid solution release date: {release!r}") from error
    if release != due.isoformat():
        raise BuildError("Solution release dates must use YYYY-MM-DD")
    return ("released", None) if today >= due else ("pending", due)


def load_config(path):
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BuildError(f"Cannot read {path}: {error}") from error
    record(config, "course.json", required=(
        "course", "lectures", "reviews", "datasets", "psets", "syllabus"))
    course = record(config["course"], "course", required=(
        "title", "term", "instructor", "textbook_url"))
    for key in course:
        text_field(course, key)
    url = urlsplit(course["textbook_url"])
    if url.scheme not in ("http", "https") or not url.netloc:
        raise BuildError("course.textbook_url must be an HTTP(S) URL")
    for key in ("lectures", "reviews", "datasets", "psets"):
        if not isinstance(config[key], list):
            raise BuildError(f"{key}: expected a list")
    return config


def collect_content(config, source_root, today=None):
    """Read and validate ALL published inputs before changing any output."""
    source_root = Path(source_root).resolve()
    today = today or datetime.date.today()
    files = {}

    def pdf(entry, folder, filename=None):
        source = Path(text_field(entry, "source"))
        if source.is_absolute() or ".." in source.parts:
            raise BuildError(f"Source must be relative to ECON139: {source}")
        path = (source_root / source).resolve()
        if not path.is_relative_to(source_root) or path.suffix.lower() != ".pdf":
            raise BuildError(f"Source must be a PDF inside ECON139: {source}")
        href = f"{folder}/{filename or source.name}"
        if href in files:
            raise BuildError(f"Duplicate published path: {href}")
        try:
            data = path.read_bytes()
        except OSError as error:
            raise BuildError(f"Cannot read source {path}: {error}") from error
        if not data.startswith(b"%PDF-"):
            raise BuildError(f"Source is empty or not a PDF: {path}. "
                             "Export it as PDF or download it from Dropbox first.")
        files[href] = data
        return href

    topics = []
    for entry in config["lectures"]:
        record(entry, "lecture", required=("topic", "decks"), optional=("published",))
        title = text_field(entry, "topic")
        if not isinstance(entry["decks"], list):
            raise BuildError(f"{title}: decks must be a list")
        if not published(entry):
            continue
        items = []
        for deck in entry["decks"]:
            record(deck, title, required=("label", "source"), optional=("published",))
            label = text_field(deck, "label")
            if published(deck):
                items.append({"label": label, "href": pdf(deck, "slides")})
        if items:
            topics.append({"topic": title, "items": items})

    def materials(section, folder):
        result = []
        for entry in config[section]:
            record(entry, section, required=("title", "source"), optional=("published",))
            title = text_field(entry, "title")
            if published(entry):
                result.append({"title": title, "href": pdf(entry, folder)})
        return result

    reviews = materials("reviews", "slides")
    datasets = materials("datasets", "slides/dataset")
    psets = []
    for entry in config["psets"]:
        record(entry, "problem set", required=("title", "source"),
               optional=("published", "solutions"))
        title = text_field(entry, "title")
        if not published(entry):
            continue
        item = {"title": title, "href": pdf(entry, "psets"),
                "sol_href": None, "sol_pending": None}
        if "solutions" in entry:
            sol = record(entry["solutions"], title + " solutions",
                         required=("source", "release"))
            status, due = solution_status(sol["release"], today)
            if status == "released":
                item["sol_href"] = pdf(sol, "psets")
            elif status == "pending":
                item["sol_pending"] = fmt_date(due)
        psets.append(item)

    syllabus = record(config["syllabus"], "syllabus", required=("source",),
                      optional=("published",))
    syllabus_href = pdf(syllabus, "syllabus", "syllabus.pdf") if published(syllabus) else None
    page = render(topics, reviews, datasets, psets, syllabus_href, config["course"])
    return page, files


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if key in attrs:
                self.hrefs.append(attrs[key])


def validate_links(page, files, site):
    links = Links()
    links.feed(page)
    for href in links.hrefs:
        url = urlsplit(href)
        if url.scheme or url.netloc:
            continue
        if not url.path:
            if url.fragment and unquote(url.fragment) not in links.ids:
                raise BuildError(f"Missing section: {href}")
            continue
        relative = unquote(url.path)
        path = (site / relative).resolve()
        if not path.is_relative_to(site.resolve()):
            raise BuildError(f"Local link leaves the website: {href}")
        if relative not in files and (not path.is_file() or path.stat().st_size == 0):
            raise BuildError(f"Missing or empty local link target: {href}")


def plan_changes(site, outputs):
    changed, unchanged = [], []
    for relative, data in outputs.items():
        target = site / relative
        if not target.resolve().is_relative_to(site.resolve()):
            raise BuildError(f"Output leaves the website: {relative}")
        if target.is_file() and target.read_bytes() == data:
            unchanged.append(relative)
        else:
            changed.append(relative)
    removed = []
    for folder in ("slides", "psets", "syllabus"):
        for path in (site / folder).rglob("*"):
            relative = path.relative_to(site).as_posix()
            if path.is_file() and path.suffix.lower() == ".pdf" and relative not in outputs:
                removed.append(relative)
    return changed, unchanged, sorted(removed)


def write_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".build-", delete=False) as temp:
        temporary = Path(temp.name)
        try:
            temp.write(data)
            temp.close()
            temporary.chmod(0o644)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def build(site=SITE, source_root=None, config_path=None, check=False):
    site = Path(site)
    config = load_config(Path(config_path) if config_path else site / "course.json")
    page, files = collect_content(config, source_root or site.parent)
    validate_links(page, files, site)
    outputs = {**files, ".nojekyll": b"", "index.html": page.encode("utf-8")}
    changed, unchanged, removed = plan_changes(site, outputs)
    if not check:
        for relative in changed:
            write_atomic(site / relative, outputs[relative])
        for relative in removed:
            (site / relative).unlink()
    action = "Would update" if check else "Updated"
    for relative in changed:
        print(f"  {action}: {relative}")
    for relative in removed:
        print(f"  {'Would remove' if check else 'Removed'}: {relative}")
    print(f"Validated {len(files)} PDFs and all local links. "
          f"{len(changed)} changed, {len(removed)} removed, {len(unchanged)} unchanged.")
    if not changed and not removed:
        print("Website files are already up to date.")
    return changed, removed


def li_link(title, href, extra=""):
    return (
        f'      <li><a href="{esc(href)}">{esc(title)}</a>{extra}</li>'
    )


def render(topics, reviews, datasets, psets, syllabus, course):
    COURSE_TITLE = course["title"]
    TERM = course["term"]
    INSTRUCTOR = course["instructor"]
    TEXTBOOK_URL = course["textbook_url"]
    rows = []
    for t in topics:
        links = '<span class="sep">/</span>'.join(
            f'<a href="{esc(it["href"])}">{esc(it["label"])}</a>'
            for it in t["items"]
        )
        rows.append(f'        <tr><th scope="row">{esc(t["topic"])}</th>'
                    f'<td>{links}</td></tr>')
    topic_rows = "\n".join(rows)

    review_items = "\n".join(li_link(it["title"], it["href"]) for it in reviews)
    dataset_items = "\n".join(li_link(it["title"], it["href"]) for it in datasets)

    pset_items = []
    for p in psets:
        extra = ""
        if p["sol_href"]:
            extra = f' &nbsp;<a class="sol" href="{esc(p["sol_href"])}">solutions</a>'
        elif p["sol_pending"]:
            extra = (f' &nbsp;<span class="sol pending">solutions available '
                     f'{esc(p["sol_pending"])}</span>')
        pset_items.append(li_link(p["title"], p["href"], extra))
    pset_items = "\n".join(pset_items)

    review_block = ""
    if review_items:
        review_block = f"""
    <h3>Exam Review</h3>
    <ul class="materials">
{review_items}
    </ul>"""

    dataset_block = ""
    if dataset_items:
        dataset_block = f"""
    <h3>Dataset Guides</h3>
    <ul class="materials">
{dataset_items}
    </ul>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(COURSE_TITLE)}</title>
  <link rel="stylesheet" href="assets/style.css">
</head>
<body>
  <header>
    <div class="wrap">
      <h1>{esc(COURSE_TITLE)}</h1>
      <p class="sub">{esc(TERM)} &middot; {esc(INSTRUCTOR)}</p>
    </div>
  </header>

  <nav class="topnav">
    <div class="wrap">
      <a href="#textbook">Textbook</a>
      <a href="#slides">Lecture Slides</a>
      <a href="#psets">Problem Sets</a>
      <a href="{esc(TEXTBOOK_URL)}" target="_blank" rel="noopener noreferrer" aria-label="Textbook site (opens in a new tab)">Textbook Site &#8599;</a>
      {(f'<a href="{esc(syllabus)}">Syllabus</a>') if syllabus else ""}
    </div>
  </nav>

  <main class="wrap">
    <section id="textbook" class="card highlight">
      <h2>Textbook</h2>
      <p>The full course textbook is available online and updated continuously.</p>
      <p><a class="button" href="{esc(TEXTBOOK_URL)}" target="_blank" rel="noopener noreferrer" aria-label="Open the textbook (opens in a new tab)">Open the textbook &#8599;</a></p>
    </section>

    <section id="slides" class="card">
      <h2>Lecture Slides</h2>
      <table class="slides">
        <thead>
          <tr><th scope="col">Topic</th><th scope="col">Slides</th></tr>
        </thead>
        <tbody>
{topic_rows}
        </tbody>
      </table>{review_block}{dataset_block}
    </section>

    <section id="psets" class="card">
      <h2>Problem Sets</h2>
      <ul class="materials">
{pset_items}
      </ul>
    </section>
  </main>

  <footer>
    <div class="wrap">
      <p>{esc(COURSE_TITLE)} &middot; {esc(INSTRUCTOR)} &middot; UC San Diego</p>
    </div>
  </footer>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="validate and report changes without writing files")
    args = parser.parse_args()
    try:
        build(check=args.check)
    except (BuildError, OSError) as error:
        parser.exit(1, f"Build stopped: {error}\nNo commit or push was attempted.\n")


if __name__ == "__main__":
    main()
