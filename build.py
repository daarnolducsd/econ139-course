#!/usr/bin/env python3
"""
Build script for the ECON 139 course website.

It scans the sibling Dropbox folders (../slides, ../pset, ../syllabus),
copies the *public* PDFs into this repo, and regenerates index.html.

Run it via ./publish.sh (which also commits + pushes), or directly:
    python3 build.py

To add a new lecture: drop the PDF in ../slides/ and re-run. To give it a
nicer name on the site, add an entry to SLIDE_TITLES below.
"""

import datetime
import html
import os
import re
import shutil

# ---------------------------------------------------------------------------
# CONFIG  -- edit these
# ---------------------------------------------------------------------------

COURSE_TITLE = "ECON 139: Labor Economics"
TERM = "Fall 2025"
INSTRUCTOR = "David Arnold"
TEXTBOOK_URL = "https://daarnolducsd.github.io/econ139/index.html"

# Problem set solutions: control when each set's solutions go public.
# Map the pset folder name to a release date "YYYY-MM-DD". Solutions are
# published only once that date has arrived (checked when build.py runs).
#   - Use None (or "") to release immediately.
#   - Omit a pset entirely to keep its solutions private indefinitely.
# Before the date, the site shows a muted "solutions available <date>" note.
#
# NOTE: the site is static, so a dated release only takes effect the next time
# you run ./publish.sh on or after that date. Run it that morning (or any time
# after) and the solutions appear.
SOLUTION_RELEASE = {
    # "pset1": "2026-02-15",
    # "pset2": "2026-03-01",
    # "pset3": None,            # available now
}

# Optional nice display names for slide files (filename without .pdf).
# Anything not listed here gets an auto-generated title.
SLIDE_TITLES = {
    "00_intro": "Introduction",
    "01_perfect_competition": "Perfect Competition",
    "02_min_wage": "Minimum Wage",
    "03_monopsony_theory": "Monopsony: Theory",
    "04_monopsony_empirics": "Monopsony: Empirics",
    "05_human_capital": "Human Capital",
    "06_human_capital_part_2": "Human Capital (Part 2)",
    "07_tasks": "Tasks",
    "08_automation_part1": "Automation (Part 1)",
    "09_automation_part2": "Automation (Part 2)",
    "10_labor_supply_part1": "Labor Supply (Part 1)",
    "11_labor_supply_part2": "Labor Supply (Part 2)",
    "12_trade_part1": "Trade (Part 1)",
    "13_trade_part2": "Trade (Part 2)",
    "Midterm_Review": "Midterm Review",
    "Final_Review": "Final Review",
    "data_01_cps": "CPS — Current Population Survey",
    "data_02_acs": "ACS — American Community Survey",
    "data_03_onet": "O*NET",
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SITE = os.path.dirname(os.path.abspath(__file__))      # website/
ROOT = os.path.dirname(SITE)                            # ECON139/

SRC_SLIDES = os.path.join(ROOT, "slides")
SRC_DATASET = os.path.join(ROOT, "slides", "dataset_slides")
SRC_PSETS = os.path.join(ROOT, "pset")
SRC_SYLLABUS = os.path.join(ROOT, "syllabus", "syllabusFA25.pdf")

OUT_SLIDES = os.path.join(SITE, "slides")
OUT_DATASET = os.path.join(SITE, "slides", "dataset")
OUT_PSETS = os.path.join(SITE, "psets")
OUT_SYLLABUS = os.path.join(SITE, "syllabus")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def reset_dir(path):
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path)


def pretty_title(stem):
    """Turn a filename stem into a human title if not in SLIDE_TITLES."""
    if stem in SLIDE_TITLES:
        return SLIDE_TITLES[stem]
    parts = stem.split("_")
    if parts and re.fullmatch(r"\d+", parts[0]):
        parts = parts[1:]
    words = " ".join(parts).replace("part ", "Part ").strip()
    return words.title() if words else stem


def lecture_number(stem):
    m = re.match(r"(\d+)", stem)
    return int(m.group(1)) if m else None


def copy_pdfs(src_dir, out_dir):
    """Copy every *.pdf in src_dir (non-recursive) to out_dir. Returns stems."""
    stems = []
    if not os.path.isdir(src_dir):
        return stems
    for name in sorted(os.listdir(src_dir)):
        if name.lower().endswith(".pdf"):
            shutil.copy2(os.path.join(src_dir, name), os.path.join(out_dir, name))
            stems.append(name[:-4])
    return stems


def esc(s):
    return html.escape(s, quote=True)


# ---------------------------------------------------------------------------
# Collect content
# ---------------------------------------------------------------------------

def collect_slides():
    reset_dir(OUT_SLIDES)
    os.makedirs(OUT_DATASET, exist_ok=True)

    stems = copy_pdfs(SRC_SLIDES, OUT_SLIDES)
    lectures, reviews = [], []
    for stem in stems:
        item = {"stem": stem, "title": pretty_title(stem), "href": f"slides/{stem}.pdf"}
        if lecture_number(stem) is not None:
            item["num"] = lecture_number(stem)
            lectures.append(item)
        else:
            reviews.append(item)
    lectures.sort(key=lambda x: x["num"])
    # Midterm review before Final review.
    reviews.sort(key=lambda x: ("final" in x["stem"].lower(), x["stem"].lower()))

    dataset_stems = copy_pdfs(SRC_DATASET, OUT_DATASET)
    datasets = [
        {"title": pretty_title(s), "href": f"slides/dataset/{s}.pdf"}
        for s in dataset_stems
    ]
    return lectures, reviews, datasets


def fmt_date(d):
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def solution_status(name):
    """Return ('released', None) / ('pending', date) / ('private', None)."""
    if name not in SOLUTION_RELEASE:
        return "private", None
    when = SOLUTION_RELEASE[name]
    if not when:
        return "released", None
    due = datetime.date.fromisoformat(when)
    if datetime.date.today() >= due:
        return "released", None
    return "pending", due


def collect_psets():
    reset_dir(OUT_PSETS)
    psets = []
    if not os.path.isdir(SRC_PSETS):
        return psets
    for name in sorted(os.listdir(SRC_PSETS)):
        folder = os.path.join(SRC_PSETS, name)
        q = os.path.join(folder, f"{name}.pdf")
        if not (os.path.isdir(folder) and os.path.isfile(q)):
            continue
        shutil.copy2(q, os.path.join(OUT_PSETS, f"{name}.pdf"))
        m = re.search(r"(\d+)", name)
        entry = {
            "title": f"Problem Set {m.group(1)}" if m else name,
            "href": f"psets/{name}.pdf",
            "sol_href": None,
            "sol_pending": None,
        }
        sol = os.path.join(folder, f"{name}_solutions.pdf")
        status, due = solution_status(name)
        if status == "released" and os.path.isfile(sol):
            shutil.copy2(sol, os.path.join(OUT_PSETS, f"{name}_solutions.pdf"))
            entry["sol_href"] = f"psets/{name}_solutions.pdf"
        elif status == "pending":
            entry["sol_pending"] = fmt_date(due)
        entry["status"] = status
        psets.append(entry)
    return psets


def collect_syllabus():
    reset_dir(OUT_SYLLABUS)
    if os.path.isfile(SRC_SYLLABUS):
        shutil.copy2(SRC_SYLLABUS, os.path.join(OUT_SYLLABUS, "syllabus.pdf"))
        return "syllabus/syllabus.pdf"
    return None


# ---------------------------------------------------------------------------
# Render HTML
# ---------------------------------------------------------------------------

def li_link(title, href, extra=""):
    return (
        f'      <li><a href="{esc(href)}">{esc(title)}</a>{extra}</li>'
    )


def render(lectures, reviews, datasets, psets, syllabus):
    lecture_items = "\n".join(
        li_link(f'{it["num"]}. {it["title"]}', it["href"]) for it in lectures
    )
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

    syllabus_link = (
        f'<a href="{esc(syllabus)}">Syllabus (PDF)</a>' if syllabus else ""
    )

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
      <p class="sub">{esc(TERM)} &middot; {esc(INSTRUCTOR)}
        {(" &middot; " + syllabus_link) if syllabus_link else ""}</p>
    </div>
  </header>

  <main class="wrap">
    <section class="card highlight">
      <h2>Textbook</h2>
      <p>The full course textbook is available online and updated continuously.</p>
      <p><a class="button" href="{esc(TEXTBOOK_URL)}">Open the textbook &rarr;</a></p>
    </section>

    <section class="card">
      <h2>Lecture Slides</h2>
      <ul class="materials">
{lecture_items}
      </ul>{review_block}{dataset_block}
    </section>

    <section class="card">
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
    lectures, reviews, datasets = collect_slides()
    psets = collect_psets()
    syllabus = collect_syllabus()
    page = render(lectures, reviews, datasets, psets, syllabus)
    with open(os.path.join(SITE, "index.html"), "w") as f:
        f.write(page)
    # .nojekyll keeps GitHub Pages from ignoring files; harmless if present.
    open(os.path.join(SITE, ".nojekyll"), "w").close()

    print(f"Built index.html")
    print(f"  lectures : {len(lectures)}")
    print(f"  reviews  : {len(reviews)}")
    print(f"  datasets : {len(datasets)}")
    released = [p["title"] for p in psets if p["sol_href"]]
    pending = [f'{p["title"]} -> {p["sol_pending"]}'
               for p in psets if p["sol_pending"]]
    print(f"  psets    : {len(psets)}")
    print(f"    released  : {released or 'none'}")
    print(f"    pending   : {pending or 'none'}")
    print(f"  syllabus : {'yes' if syllabus else 'missing'}")


if __name__ == "__main__":
    main()
