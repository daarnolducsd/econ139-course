#!/usr/bin/env python3
"""Validate and incrementally build the course site from course.json and schedule.json.

Source paths are relative to the parent ECON139 folder. Only explicitly listed,
published files are copied. This script does not compile PowerPoint/LaTeX or push.
"""

import argparse
import datetime
import html
import io
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile

SITE = Path(__file__).resolve().parent
DOWNLOAD_EXTENSIONS = {"data": (".csv", ".dta", ".xlsx"), "code": (".py", ".r", ".do")}
PDF_FOLDERS = {"slides": "slides", "review": "slides", "guide": "slides/dataset", "assignment": "psets"}


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
    record(config, "course.json", required=("course", "materials", "syllabus"), optional=("bundles",))
    course = record(config["course"], "course", required=(
        "title", "term", "instructor", "textbook_url"))
    for key in course:
        text_field(course, key)
    web_url(course["textbook_url"])
    if not isinstance(config["materials"], dict):
        raise BuildError("materials: expected an object keyed by stable material IDs")
    for key, item in config["materials"].items():
        if not key or not isinstance(key, str):
            raise BuildError("Each material needs a nonempty ID")
        record(item, key, required=("title", "kind", "source"),
               optional=("published", "solutions", "destination", "group"))
        for field in ("title", "source"):
            text_field(item, field)
        if item["kind"] not in ("slides", "guide", "review", "assignment", "data", "code"):
            raise BuildError(f"{key}: kind must be slides, guide, review, assignment, data, or code")
        if "solutions" in item and item["kind"] != "assignment":
            raise BuildError(f"{key}: only assignments can have solutions")
        if "group" in item:
            text_field(item, "group")
            if item["kind"] not in DOWNLOAD_EXTENSIONS:
                raise BuildError(f"{key}: only data/code can have a download group")
        published(item)
        material_destination(item)
    bundles = config.get("bundles", {})
    if not isinstance(bundles, dict):
        raise BuildError("bundles: expected an object keyed by topic IDs")
    for key, bundle in bundles.items():
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key):
            raise BuildError(f"Invalid bundle ID: {key!r}")
        record(bundle, key, required=("title", "readme", "materials"))
        text_field(bundle, "title")
        text_field(bundle, "readme")
        members = bundle["materials"]
        if not isinstance(members, list) or not members:
            raise BuildError(f"{key}: bundle materials must be a nonempty list")
        seen = set()
        for member in members:
            if not isinstance(member, str) or member not in config["materials"] or config["materials"][member]["kind"] not in DOWNLOAD_EXTENSIONS:
                raise BuildError(f"{key}: bundle may only contain mapped data/code IDs")
            if member in seen:
                raise BuildError(f"{key}: repeated bundle member {member!r}")
            seen.add(member)
    return config


def web_url(value):
    if not isinstance(value, str):
        raise BuildError("Links must be HTTP(S) URLs")
    try:
        url = urlsplit(value)
    except ValueError as error:
        raise BuildError(f"Invalid HTTP(S) link: {value!r}") from error
    if url.scheme not in ("http", "https") or not url.netloc:
        raise BuildError(f"Invalid HTTP(S) link: {value!r}")
    return value


def load_schedule(path, materials):
    try:
        schedule = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BuildError(f"Cannot read {path}: {error}") from error
    return validate_schedule(schedule, materials)


def material_destination(entry):
    source = Path(entry["source"])
    kind = entry["kind"]
    if "destination" in entry:
        value = text_field(entry, "destination")
        path = Path(value)
        if (kind not in DOWNLOAD_EXTENSIONS or path.is_absolute() or ".." in path.parts
                or len(path.parts) < 2 or path.parts[0] != "downloads"
                or path.as_posix() != value or path.suffix.lower() != source.suffix.lower()):
            raise BuildError(f"Invalid data/code destination: {value!r}")
        return value
    folder = f"downloads/{kind}/{source.parent.name}" if kind in DOWNLOAD_EXTENSIONS else PDF_FOLDERS[kind]
    return f"{folder}/{source.name}"


def source_map(config, schedule):
    """Derive the editing guide from the same catalog/paths used by the build."""
    rows = []
    ordered = sorted(config["materials"].items(), key=lambda pair: pair[1]["kind"] not in DOWNLOAD_EXTENSIONS)
    for key, entry in ordered:
        if not published(entry):
            continue
        weeks = []
        for week in schedule["weeks"]:
            assignments = [a.get("material") for a in week.get("assignments", [])]
            if key in week["materials"] + week.get("resources", []) + assignments:
                weeks.append(str(week["number"]))
        rows.append((key, entry["source"], material_destination(entry), ", ".join(weeks) or "Additional materials"))
        sol = entry.get("solutions")
        if sol and solution_status(sol["release"], datetime.date.today())[0] == "released":
            rows.append((key + " solutions", sol["source"], "psets/" + Path(sol["source"]).name, "Problem sets"))
    if published(config["syllabus"]):
        rows.append(("syllabus", config["syllabus"]["source"], "syllabus/syllabus.pdf", "Header"))
    for key, bundle in config.get("bundles", {}).items():
        members = [m for m in bundle["materials"] if published(config["materials"][m])]
        if members:
            rows.append((key + " instructions", bundle["readme"], f"downloads/guides/{key}-README.md", "Topic ZIP"))
            rows.append((key + " ZIP", f"Generated from {', '.join(members)} and README", f"downloads/bundles/{key}.zip", "Topic resources"))
    result = ["# Website source files", "", "Generated by build.py from course.json and schedule.json; do not edit this guide.", "",
              "Edit the **source** files below, relative to the ECON139 folder. Run `./website/publish.sh` to publish your edits.", "",
              "The website copies are generated output. Editing files under `website/slides/`, `website/downloads/`, `website/psets/`, or `website/syllabus/` will be overwritten by the next build.", "",
              "To change which file is used, edit its `source` in `website/course.json`. To move it between weeks, edit `website/schedule.json`.", "",
              "| Material ID | Source to edit (ECON139/) | Website copy (website/) | Weeks |", "| --- | --- | --- | --- |"]
    for key, source, destination, weeks in rows:
        cells = [key, source, destination, weeks]
        result.append("| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")
    return "\n".join(result) + "\n"


def validate_schedule(schedule, materials):
    record(schedule, "schedule.json", required=("weeks",))
    if not isinstance(schedule["weeks"], list):
        raise BuildError("weeks: expected a list")
    numbers = []
    for week in schedule["weeks"]:
        record(week, "week", required=("number", "title", "materials"),
               optional=("readings", "assignments", "resources", "dates"))
        number = week["number"]
        if type(number) is not int:
            raise BuildError("Week numbers must be integers from 1 to 10")
        numbers.append(number)
        text_field(week, "title")
        if "dates" in week:
            text_field(week, "dates")
        if not isinstance(week["materials"], list):
            raise BuildError(f"Week {number}: materials must be a list of IDs")
        seen = set()
        for key in week["materials"]:
            if not isinstance(key, str) or key not in materials:
                raise BuildError(f"Week {number}: unknown material ID {key!r}")
            if key in seen:
                raise BuildError(f"Week {number}: repeated material {key!r}")
            if materials[key]["kind"] not in ("slides", "guide", "review"):
                raise BuildError(f"Week {number}: put {key!r} in assignments or resources")
            seen.add(key)
        for section in ("readings", "resources", "assignments"):
            entries = week.get(section, [])
            if not isinstance(entries, list):
                raise BuildError(f"Week {number}: {section} must be a list")
            for entry in entries:
                if section == "resources":
                    if not isinstance(entry, str) or entry not in materials or materials[entry]["kind"] not in DOWNLOAD_EXTENSIONS:
                        raise BuildError(f"Week {number}: unknown data/code material ID {entry!r}")
                    if entries.count(entry) > 1:
                        raise BuildError(f"Week {number}: repeated resource {entry!r}")
                    continue
                if section == "assignments":
                    record(entry, section, optional=("title", "material", "note"))
                    if ("title" in entry) == ("material" in entry):
                        raise BuildError("Each assignment needs either a title or a material ID")
                    if "material" in entry:
                        key = entry["material"]
                        if not isinstance(key, str) or key not in materials or materials[key]["kind"] != "assignment":
                            raise BuildError(f"Week {number}: unknown assignment material {key!r}")
                    else:
                        text_field(entry, "title")
                else:
                    record(entry, section, required=("title", "url"), optional=("note",))
                    text_field(entry, "title")
                if "url" in entry:
                    web_url(entry["url"])
                if "note" in entry:
                    text_field(entry, "note")
    if sorted(numbers) != list(range(1, 11)):
        raise BuildError("Schedule must contain each week from 1 through 10 exactly once")
    return {"weeks": sorted(schedule["weeks"], key=lambda week: week["number"])}


def collect_content(config, source_root, today=None, schedule=None):
    """Read and validate ALL published inputs before changing any output."""
    source_root = Path(source_root).resolve()
    today = today or datetime.date.today()
    if schedule is None:
        raise BuildError("A weekly schedule is required")
    schedule = validate_schedule(schedule, config["materials"])
    files, catalog, sources = {}, {}, set()

    def copy_file(entry, folder, filename=None, allowed=(".pdf",)):
        source = Path(text_field(entry, "source"))
        if source.is_absolute() or ".." in source.parts:
            raise BuildError(f"Source must be relative to ECON139: {source}")
        path = (source_root / source).resolve()
        if not path.is_relative_to(source_root) or path.suffix.lower() not in allowed:
            raise BuildError(f"Source must be inside ECON139 with extension {allowed}: {source}")
        if path in sources:
            raise BuildError(f"Duplicate source mapping: {source}. Reuse one material ID across weeks.")
        sources.add(path)
        href = f"{folder}/{filename or source.name}"
        if href in files:
            raise BuildError(f"Duplicate published path: {href}")
        try:
            data = path.read_bytes()
        except OSError as error:
            raise BuildError(f"Cannot read source {path}: {error}") from error
        if not data:
            raise BuildError(f"Source is empty: {path}. Download it from Dropbox first.")
        if path.suffix.lower() == ".pdf" and not data.startswith(b"%PDF-"):
            raise BuildError(f"Source is not a PDF: {path}. Export it as PDF first.")
        if path.suffix.lower() in (".csv", ".py", ".r", ".do", ".md"):
            try:
                data.decode("utf-8-sig")
            except UnicodeDecodeError as error:
                raise BuildError(f"Source must be UTF-8 text: {path}") from error
            if b"\0" in data:
                raise BuildError(f"Source contains binary data instead of text: {path}")
        if path.suffix.lower() == ".xlsx" and not data.startswith(b"PK\x03\x04"):
            raise BuildError(f"Source is not an XLSX workbook: {path}")
        files[href] = data
        return href

    for key, entry in config["materials"].items():
        if not published(entry):
            continue
        kind = entry["kind"]
        destination = Path(material_destination(entry))
        href = copy_file(entry, destination.parent.as_posix(), filename=destination.name,
                         allowed=DOWNLOAD_EXTENSIONS.get(kind, (".pdf",)))
        item = {"title": entry["title"], "kind": kind, "group": entry.get("group", entry["title"]),
                "href": href,
                "sol_href": None, "sol_pending": None}
        if "solutions" in entry:
            sol = record(entry["solutions"], key + " solutions", required=("source", "release"))
            status, due = solution_status(sol["release"], today)
            if status == "released":
                item["sol_href"] = copy_file(sol, "psets")
            elif status == "pending":
                item["sol_pending"] = fmt_date(due)
        catalog[key] = item

    syllabus = record(config["syllabus"], "syllabus", required=("source",), optional=("published",))
    syllabus_href = copy_file(syllabus, "syllabus", "syllabus.pdf") if published(syllabus) else None
    bundles = []
    for key, bundle in config.get("bundles", {}).items():
        members = [m for m in bundle["materials"] if m in catalog]
        if not members:
            continue
        readme_href = copy_file({"source": bundle["readme"]}, "downloads/guides",
                               filename=f"{key}-README.md", allowed=(".md",))
        entries = {f"{key}/README.md": files[readme_href]}
        for member in members:
            item = catalog[member]
            name = f"{key}/{item['kind']}/{Path(config['materials'][member]['source']).name}"
            if name in entries:
                raise BuildError(f"Duplicate path inside {key} ZIP: {name}")
            entries[name] = files[item["href"]]
        href = f"downloads/bundles/{key}.zip"
        files[href] = topic_zip(entries)
        bundles.append({"title": bundle["title"], "href": href, "readme": readme_href, "members": members})
    page = render(schedule["weeks"], catalog, syllabus_href, config["course"], bundles)
    return page, files


def topic_zip(entries):
    """Only explicit members; fixed metadata avoids rebuilding unchanged ZIPs."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.getvalue()


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
    for folder in ("slides", "psets", "syllabus", "downloads"):
        for path in (site / folder).rglob("*"):
            relative = path.relative_to(site).as_posix()
            managed = path.suffix.lower() == ".pdf" or (folder == "downloads" and path.suffix.lower() in (".csv", ".dta", ".xlsx", ".py", ".r", ".do", ".md", ".zip"))
            if path.is_file() and managed and relative not in outputs:
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
    schedule = load_schedule(site / "schedule.json", config["materials"])
    page, files = collect_content(config, source_root or site.parent, schedule=schedule)
    validate_links(page, files, site)
    outputs = {**files, ".nojekyll": b"", "index.html": page.encode("utf-8"),
               "SOURCE_FILES.md": source_map(config, schedule).encode("utf-8")}
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
    print(f"Validated {len(files)} published files and all local links. "
          f"{len(changed)} changed, {len(removed)} removed, {len(unchanged)} unchanged.")
    if not changed and not removed:
        print("Website files are already up to date.")
    return changed, removed


def external_link(title, url, css=""):
    return (f'<a class="{esc(css)}" href="{esc(url)}" target="_blank" '
            f'rel="noopener noreferrer" aria-label="{esc(title)} (opens in a new tab)">'
            f'{esc(title)} <span aria-hidden="true">&#8599;</span></a>')


def material_row(item):
    download = item["kind"] in DOWNLOAD_EXTENSIONS
    label = Path(item["href"]).suffix[1:].upper() if download else {"slides": "Slides PDF", "guide": "Guide PDF", "review": "Review PDF", "assignment": "PDF"}[item["kind"]]
    attribute = " download" if download else ""
    return (f'<li class="material-row"><span>{esc(item["title"])}</span>'
            f'<a class="pdf-link" href="{esc(item["href"])}" '
            f'aria-label="{esc(item["title"])} ({label})"{attribute}>{label}</a></li>')


def solution_link(item):
    if item["sol_href"]:
        return f'<a class="pdf-link" href="{esc(item["sol_href"])}">Solutions PDF</a>'
    if item["sol_pending"]:
        return f'<span class="pending">solutions available {esc(item["sol_pending"])}</span>'
    return ""


def week_panel(kind, title, content):
    content = content or '<p class="empty-section">None this week.</p>'
    return (f'<div class="week-group panel panel-{kind}"><h3>{title}</h3>'
            f'<div class="panel-content">{content}</div></div>')


def download_rows(items):
    groups = {}
    formats = {".csv": "CSV", ".dta": "Stata", ".xlsx": "Excel",
               ".py": "Python", ".r": "R", ".do": "Stata"}
    order = {".csv": 0, ".dta": 1, ".xlsx": 2, ".py": 0, ".r": 1, ".do": 2}
    for item in items:
        groups.setdefault((item["kind"], item["group"]), []).append(item)
    rows = []
    for (_, title), members in groups.items():
        links = []
        for item in sorted(members, key=lambda item: order[Path(item["href"]).suffix.lower()]):
            label = formats[Path(item["href"]).suffix.lower()]
            links.append(f'<a href="{esc(item["href"])}" aria-label="{esc(title)} ({label})" download>{label}</a>')
        links = '<span class="format-separator" aria-hidden="true">&middot;</span>'.join(links)
        rows.append(f'<li class="material-row download-row"><span>{esc(title)}</span>'
                    f'<div class="download-formats">{links}</div></li>')
    return f'<ul class="material-list">{"".join(rows)}</ul>' if rows else ""


def render(weeks, catalog, syllabus, course, bundles=()):
    jump_links = "\n".join(f'<a href="#week-{week["number"]}" aria-label="Week {week["number"]}">{week["number"]}</a>' for week in weeks)
    week_sections, used = [], set()
    for week in weeks:
        used.update(week["materials"])
        items = [material_row(catalog[key]) for key in week["materials"] if key in catalog]
        slides = f'<ul class="material-list">{"".join(items)}</ul>' if items else ""
        groups = [week_panel("slides", "Slides", slides)]
        readings = []
        for entry in week.get("readings", []):
            note = f'<span class="item-note">{esc(entry["note"])}</span>' if entry.get("note") else ""
            readings.append(f'<li>{external_link(entry["title"], entry["url"])}{note}</li>')
        readings = f'<ul class="reading-list">{"".join(readings)}</ul>' if readings else ""
        groups.append(week_panel("readings", "Readings", readings))
        assignments = []
        for entry in week.get("assignments", []):
            actions = []
            if "material" in entry:
                key = entry["material"]
                used.add(key)
                if key not in catalog:
                    continue
                item = catalog[key]
                title = item["title"]
                actions.append(f'<a class="pdf-link" href="{esc(item["href"])}">PDF</a>')
                actions.append(solution_link(item))
            else:
                title = entry["title"]
            note = f'<span class="item-note">{esc(entry["note"])}</span>' if entry.get("note") else ""
            assignments.append(f'<li><div class="assignment-title">{esc(title)}{note}</div>'
                               f'<div class="assignment-actions">{"".join(actions)}</div></li>')
        assignments = f'<ul class="assignment-list">{"".join(assignments)}</ul>' if assignments else ""
        groups.append(week_panel("assignments", "Assignments", assignments))
        resources = [key for key in week.get("resources", []) if key in catalog]
        used.update(week.get("resources", []))
        downloads = ""
        if resources:
            packages = []
            for bundle in bundles:
                if set(resources).intersection(bundle["members"]):
                    packages.append(f'<a class="pdf-link bundle-download" href="{esc(bundle["href"])}" download>Download {esc(bundle["title"])} ZIP</a>'
                                    f'<a href="{esc(bundle["readme"])}" download>{esc(bundle["title"])} instructions</a>')
            downloads = f'<div class="bundle-links">{"".join(packages)}</div>' if packages else ""
            for kind, heading in (("data", "Data files"), ("code", "Code")):
                rows = download_rows([catalog[key] for key in resources if catalog[key]["kind"] == kind])
                if rows:
                    downloads += f'<div class="download-group"><h4>{heading}</h4>{rows}</div>'
        groups.append(week_panel("downloads", "Data &amp; code", downloads))
        content = "".join(groups)
        dates = f'<p class="week-dates">{esc(week["dates"])}</p>' if week.get("dates") else ""
        week_sections.append(f'''<section id="week-{week["number"]}" class="week" aria-labelledby="week-{week["number"]}-title">
      <div class="week-heading"><p class="week-number">Week {week["number"]}</p><h2 id="week-{week["number"]}-title">{esc(week["title"])}</h2>{dates}</div>
      <div class="week-content">{content}</div>
    </section>''')
    assignments = []
    extras = []
    for key, item in catalog.items():
        if item["kind"] == "assignment":
            assignments.append(f'<li class="material-row"><span>{esc(item["title"])}</span><div class="assignment-actions">'
                               f'<a class="pdf-link" href="{esc(item["href"])}">PDF</a>{solution_link(item)}</div></li>')
        elif key not in used:
            extras.append(material_row(item))
    assignment_section = (f'<section id="psets" class="resource-section"><h2>Problem sets</h2><ul class="material-list">{"".join(assignments)}</ul></section>'
                          if assignments else '<div id="psets"></div>')
    extra_section = (f'<section class="resource-section"><h2>Additional materials</h2><ul class="material-list">{"".join(extras)}</ul></section>' if extras else "")
    syllabus_link = f'<a class="resource-link" href="{esc(syllabus)}">Syllabus PDF</a>' if syllabus else ""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(course["title"])}</title>
  <link rel="stylesheet" href="assets/style.css">
  <script src="assets/navigation.js" defer></script>
</head>
<body>
  <a class="skip-link" href="#schedule">Skip to weekly schedule</a>
  <header class="course-header">
    <div class="wrap">
      <p class="eyebrow">UC San Diego &middot; Economics</p>
      <h1>{esc(course["title"])}</h1>
      <p class="course-meta">{esc(course["instructor"])}</p>
      <div id="textbook" class="course-resources">{syllabus_link}{external_link("Textbook", course["textbook_url"], "resource-link")}</div>
    </div>
  </header>
  <nav class="week-nav" aria-label="Course navigation">
    <div class="wrap"><a class="schedule-nav" href="#schedule">Weekly schedule</a><div class="week-jumps" aria-label="Jump to a week">{jump_links}</div><a class="pset-nav" href="#psets">Problem sets</a></div>
  </nav>
  <main class="wrap" id="slides">
    <div id="schedule" class="schedule-heading"><h2>Weekly schedule</h2><p>Slides, readings, assignments, and data &amp; code for each week.</p></div>
    {"".join(week_sections)}
    {assignment_section}{extra_section}
  </main>
  <footer><div class="wrap">{esc(course["title"])} &middot; {esc(course["instructor"])} &middot; UC San Diego</div></footer>
</body>
</html>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="validate and report changes without writing files")
    parser.add_argument("--sources", action="store_true",
                        help="show exact editable sources and website copies; no writes")
    args = parser.parse_args()
    try:
        if args.sources:
            config = load_config(SITE / "course.json")
            print(source_map(config, load_schedule(SITE / "schedule.json", config["materials"])), end="")
            return
        build(check=args.check)
    except (BuildError, OSError) as error:
        parser.exit(1, f"Build stopped: {error}\nNo commit or push was attempted.\n")


if __name__ == "__main__":
    main()
