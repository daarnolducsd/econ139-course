# ECON 139 Website — Project Notes (for resuming work)

> Tell Claude: **"read website/PROJECT_NOTES.md"** to pick up where we left off.

## Goal

Replace the clunky Canvas workflow with a static course site on **GitHub
Pages**. The instructor edits slides/psets in the usual Dropbox folders, runs
one command (`./publish.sh`), and the live site refreshes. No re-uploading, no
broken links.

## Where things live

- **Working folder:** `/Users/davidarnold/Dropbox/Teaching/ECON139/website/`
  (its own git repo, a sibling of the `slides/`, `pset/`, `syllabus/` folders).
- **Target GitHub repo:** `git@github.com:daarnolducsd/econ139-course.git`
  (remote `origin` already added locally).
- **Target live URL:** https://daarnolducsd.github.io/econ139-course
- **Textbook (separate, already live):** https://daarnolducsd.github.io/econ139/index.html
  — its source is the `../textbook/` Quarto repo (`econ139` repo, gh-pages branch).

## Key decisions

- **Separate repo** for the site (not folded into the textbook repo) so nothing
  sensitive can leak.
- **Sensitive material stays in the parent Dropbox folder** (`../grades`,
  `../midterm`, `../final`, `../pset/*/*_solutions.pdf`) and is NEVER copied
  into this repo. `build.py` only copies specific public files.
- **Materials published:** lecture slide PDFs, dataset-guide PDFs, pset question
  PDFs, syllabus PDF. No `.pptx`.
- **Pset solutions:** released by date via `SOLUTION_RELEASE` in `build.py`.

## How it works

- `build.py` scans `../slides`, `../pset`, `../syllabus`, copies the public PDFs
  into `slides/`, `psets/`, `syllabus/`, and regenerates `index.html`.
- `publish.sh` runs `build.py`, then `git add/commit/push`.
- `index.html` is generated — do not hand-edit it; change `build.py` instead.
- Lecture slides render as a **Topic | Slides table**, grouped via the `TOPICS`
  list in `build.py` (e.g. Monopsony = Theory + Empirics on one row).
- Styling in `assets/style.css`; current theme is **light blue** (CSS variables
  at the top of the file). There is a sticky top **nav** bar.

## Status (as of last session)

- [x] Site built; `index.html`, slides, psets, syllabus all generated.
- [x] Light-blue theme + sticky nav + grouped slides table.
- [x] Dated pset-solution releases implemented and tested.
- [x] Committed locally (`main` branch). Remote `origin` added.
- [ ] **NOT pushed yet** — the GitHub repo `econ139-course` still needs to be
      created, and GitHub Pages enabled.

## To go live (remaining steps)

1. Create an **empty** repo at https://github.com/new named `econ139-course`
   (Public, no README).
2. From this folder: `git push -u origin main`
3. Repo **Settings → Pages → Deploy from a branch → `main` / `/ (root)` → Save**.
4. Wait ~1 minute; visit https://daarnolducsd.github.io/econ139-course

After that, the only recurring command is `./publish.sh`.

## Common edits (all in build.py)

- New lecture: drop the PDF in `../slides/`, run `./publish.sh`. Add it to
  `TOPICS` (and optionally `SLIDE_TITLES`) for nice grouping/naming.
- Release pset solutions on a date: set e.g. `SOLUTION_RELEASE = {"pset1":
  "2026-02-15"}`. Run `./publish.sh` on/after that date.
- Course title / term / textbook link: constants at the top of `build.py`.
- Colors: CSS variables at the top of `assets/style.css`.

## Ideas not yet done (possible future work)

- A "Schedule" section / weekly calendar table.
- Auto-running `publish.sh` on a daily local schedule so dated solution
  releases publish themselves (discussed; not set up).
- Lecture dates shown next to each topic.
