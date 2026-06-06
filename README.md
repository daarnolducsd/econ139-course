# ECON 139 — Course Website

A small static site for ECON 139 (Labor Economics). It links to the online
textbook and hosts the lecture slides, dataset guides, problem sets, and
syllabus. Published with **GitHub Pages**.

Live site: https://daarnolducsd.github.io/econ139-course

## How it works

This folder lives inside the Dropbox `ECON139` course folder. `build.py`
reaches up into the sibling folders and copies only the **public** PDFs into
this repo, then regenerates `index.html`:

| Source (in `../`)                | Published here       |
| -------------------------------- | -------------------- |
| `slides/*.pdf`                   | `slides/`            |
| `slides/dataset_slides/*.pdf`    | `slides/dataset/`    |
| `pset/psetN/psetN.pdf`           | `psets/`             |
| `pset/psetN/psetN_solutions.pdf` | `psets/` *(only if released — see below)* |
| `syllabus/syllabusFA25.pdf`      | `syllabus/`          |

Grades, exams, and unreleased solutions live in the parent folder and are
**never** copied here, so they cannot leak to the public site.

## Everyday use

After editing slides or psets in the usual Dropbox folders, just run:

```sh
./publish.sh
```

That rebuilds the site, copies the latest PDFs, commits, and pushes. GitHub
Pages refreshes within about a minute. **Add a new lecture** by dropping its
PDF in `../slides/` and running `./publish.sh` — it appears automatically.

Optional commit message: `./publish.sh "Add automation lecture"`

## Common edits (all in `build.py`)

- **Release a pset's solutions (with a date):** add the pset to
  `SOLUTION_RELEASE` with a date, e.g.

  ```python
  SOLUTION_RELEASE = {
      "pset1": "2026-02-15",   # auto-publishes on/after this date
      "pset2": None,           # publish immediately
      # pset3 omitted          # stays private
  }
  ```

  Before the date, the site shows a muted "solutions available February 15,
  2026" note next to that pset. Because the site is static, a dated release
  takes effect the next time you run `./publish.sh` **on or after** that date —
  run it that morning (or any time after) and the solutions go live. Remove a
  pset from the map to take its solutions down again.
- **Nicer slide titles:** add a `"filename_stem": "Display Name"` entry to
  `SLIDE_TITLES`. Files not listed get an auto-generated title.
- **Course info / textbook link:** edit the constants at the top.

## First-time setup (already done once)

```sh
git init
git remote add origin git@github.com:daarnolducsd/econ139-course.git
./publish.sh "Initial site"
```

Then on GitHub: **Settings → Pages → Build and deployment → Deploy from a
branch → `main` / root**.
