# ECON 139 — Course Website

A static course site published with GitHub Pages. Requires Python 3.9+ and Git;
no Python packages or JavaScript build tools are needed.

Configured site URL: https://daarnolducsd.github.io/econ139-course/
Remote: `https://github.com/daarnolducsd/econ139-course.git`

## Update slides, code, or data and publish

1. Edit the original file listed in [SOURCE_FILES.md](SOURCE_FILES.md).
   Slide edits must be **exported to PDF** in `ECON139/slides/`; code and data
   edits are picked up directly from the mapped files in `ECON139/materials/<topic>/`.
2. From the `ECON139` folder, run:

   ```sh
   ./website/publish.sh
   ```

The command validates every published file and local link, copies only changed
files, regenerates the page, commits the website files, and pushes to
`origin/main`. Existing URLs stay the same. No manual copying or HTML editing
is needed when updating an existing slide deck, code file, or dataset. PowerPoint and LaTeX compilation is
not performed by this command.

From inside `website/`, use `./publish.sh` instead. An optional commit message
works too: `./website/publish.sh "Update minimum wage slides"`.

## Check, build locally, or preview

```sh
./website/publish.sh --sources  # show exactly which original files are used
./website/publish.sh --check    # validate/report changes, without writing
./website/publish.sh --local    # build only; no commit or push
./website/publish.sh --preview  # build and serve at http://localhost:8000
```

Stop the preview with Ctrl-C. Choose a different port with
`PORT=8001 ./website/publish.sh --preview`.

A missing, empty, unsupported, or invalid published source stops the build before it changes
any generated files. If Dropbox has not downloaded a file, make it available
offline and rerun the command. A failed push leaves the local commit intact;
fix the Git error and rerun the same command, which will retry the pending push.
An unchanged build with no pending commits does not create a new commit or push.

## Two small content files

- `course.json` is the reusable file catalog: course details, material titles,
  stable IDs, source paths, and solution releases.
- `schedule.json` decides what appears in each of Weeks 1–10: material IDs,
  readings, assignments, and optional dates. Edit this file for pacing changes.

The current schedule comes from the Fall 2025 Canvas export. Canvas Weeks 0 and 1
are combined into website Week 1; Weeks 2–10 keep their original numbers. A deck
can appear in multiple weeks for a continuing topic, while its PDF is copied
only once. Old calendar dates and office-hour announcements were not imported.

### Move content between weeks

For example, move Minimum Wage from Week 2 to Week 3 by moving the string
`"minimum-wage"` between those weeks' `materials` lists in `schedule.json`:

```json
{
  "number": 3,
  "title": "Monopsony Power",
  "materials": ["minimum-wage", "monopsony-theory", "monopsony-empirics"]
}
```

Leave the ID in both lists if the topic spans two weeks. The order within each
list determines the order of PDFs within their group. Move reading or assignment
objects the same way, between the corresponding `readings` or `assignments`
lists. Then run the usual `./website/publish.sh`. No PDF renaming, copying, or
HTML editing is necessary.

Each week requires `number`, `title`, and `materials`. `readings`, `assignments`,
`resources`, and `dates` are optional. Keep exactly one entry for each number
1–10; empty weeks are allowed. Unknown IDs and duplicate IDs within one week
stop the build before it writes output. Example optional dates: `"dates": "Sep 28–Oct 2"`.

A reading has `title`, `url`, and an optional `note`. A data/code resource is a
catalog ID, for example `"resources": ["cps-csv", "cps-python"]`. Move or repeat
these IDs across weeks just like slide IDs. Assignments may reference a catalog
PDF with `"material": "pset1"`, plus an optional `note`; other activities use
`title` and an optional `note` as plain-text reminders. There are no Canvas links
or course IDs in the page or configuration. Data and code appear as direct
downloads in expandable panels to keep each week compact.

### Start a new quarter

1. Update `course.term` and `syllabus.source` in `course.json`.
2. Rearrange the IDs, readings, and assignment reminders in `schedule.json`;
   update week titles and optionally add dates.
3. Check solution releases, build locally with `./website/publish.sh --local`,
   then publish with `./website/publish.sh`. No Canvas URLs need updating.

### Where the editable code and data live

`ECON139/materials/README.md` is the instructor's starting
point. Each topic keeps the editable originals, instructions, and local results
together:

```text
materials/
  cps/
    README.md
    data/cps_aug_25.csv, cps_aug_25.dta
    code/analyze.py, analyze.R, analyze.do
    outputs/                         # local analysis results only
  acs/
    README.md
    data/acs_clean_healthcare.csv, .dta, .xlsx
    code/acs_healthcare.py, .R, .do
    outputs/
  onet/
    README.md
    data/work_activities.csv, .dta, .xlsx
```

**Edit the originals in materials/, then publish.** Files with similar names in
`pset/`, old working folders, or archives are not substituted for the mapped
sources. Problem-set data remains an assessment snapshot: the lecture and
Problem Set 1 CPS CSV files differ. The old locations of the 14 moved originals
contain migration notices, not a second editable copy. See
`ECON139/materials/MIGRATION_NOTES.md` for the audit.

The builder generates [SOURCE_FILES.md](SOURCE_FILES.md) on every successful
build, listing originals, website copies, and weekly placements. The read-only
`./website/publish.sh --sources` command shows the current configuration before
building. `--check` reports pending changes without writing or publishing.

For example, edit `ECON139/materials/cps/code/analyze.py`, then run
`./website/publish.sh`. Both its existing individual download at
`website/downloads/code/cps/analyze.py` and `website/downloads/bundles/cps.zip`
update from that exact original. Never edit generated website copies; an
output-only edit will be overwritten by the next build. File contents are
compared, so same-size/timestamp edits are detected, and unchanged ZIPs are not
rewritten just because a source timestamp changed.

The Python examples locate data relative to their script; Rscript does likewise.
In RStudio or Stata, run from the topic folder as described in its README. Figures
are written to `outputs/` instead of input directories. The website builder does
not run analyses or modify input data. Preparation scripts under `code/` still
use raw inputs under `data/`; the ACS healthcare and O*NET work-activities
preparation scripts now write their teaching exports into materials/.

### Topic ZIP downloads

Each week's Data & code panel offers the relevant topic ZIP and instructions,
plus the existing individual downloads. A ZIP contains one folder (`cps/`,
`acs/`, or `onet/`) with README, data, and any mapped teaching code. Students can
unzip it and use the documented commands without changing your personal paths.

`course.json` defines each ZIP explicitly, for example:

```json
"bundles": {
  "cps": {
    "title": "CPS",
    "readme": "materials/cps/README.md",
    "materials": ["cps-csv", "cps-stata", "cps-python", "cps-stata-code", "cps-r"]
  }
}
```

Only these published catalog members and that README enter the ZIP. Outputs,
logs, caches, raw data, private solutions, and other unlisted files are never
included through directory scanning. Hiding a member removes it from its
individual download and ZIP on the next build. Hiding all members removes the
ZIP and its instructions download. Update the README if changing a topic's files.

### Add data or code

Supported data formats are CSV, Stata DTA, and Excel XLSX; code formats are
Python, R, and Stata scripts. Add the original in materials/<topic>/data/ or
code/, then add a catalog entry:

```json
"cps-python": {
  "title": "CPS analysis (Python)",
  "kind": "code",
  "source": "materials/cps/code/analyze.py",
  "destination": "downloads/code/cps/analyze.py"
}
```

`source` is relative to ECON139; `destination` is relative to website/ and must
stay under downloads/. The explicit destination preserves its URL even if the
original moves. Set one for every new topic resource. Then add the material ID
to a week's `resources` list and, if appropriate, its topic's bundle member list.
Reusing an ID across weeks shares one individual download and topic ZIP.
These files are served by the course website itself, with no Canvas dependency.

### Add or hide a PDF

Every `source` is relative to the **ECON139 folder**, regardless of where you
run the command. PDF bytes are copied exactly; source files are never modified.

| Configured source | Published destination |
| --- | --- |
| `slides/01_perfect_competition.pdf` | `website/slides/01_perfect_competition.pdf` |
| `slides/dataset_slides/data_01_cps.pdf` | `website/slides/dataset/data_01_cps.pdf` |
| `pset/pset1/pset1.pdf` | `website/psets/pset1.pdf` |
| `syllabus/syllabusFA25.pdf` | `website/syllabus/syllabus.pdf` |

Add a named entry to `course.json`'s `materials` object:

```json
"new-topic": {
  "title": "New Topic",
  "kind": "slides",
  "source": "slides/14_new_topic.pdf"
}
```

Then put `"new-topic"` in the appropriate week's `materials` list. Supported
kinds are `slides`, `guide`, `review`, `assignment`, `data`, and `code`. Assignments go in weekly
`assignments` lists using their material ID, and also appear in the Problem sets
section. Published slides without a week appear under Additional materials.

Only explicitly listed, published files are copied. Dropping a new PDF into a
source folder does **not** automatically publish it. Add `"published": false`
to a catalog entry or the syllabus to hide it. Omitting `published` means it is
visible. Removing/hiding an entry also removes its old public PDF on the next
build. Remove schedule references before deleting its catalog entry. These
output folders, including `website/downloads/`, are managed by the builder;
do not store hand-maintained files in them.

### Release problem-set solutions

Each assignment can include a `solutions` object:

```json
"solutions": {
  "source": "pset/pset1/pset1_solutions.pdf",
  "release": false
}
```

- `false`: private; no solution file is copied or linked. This is the current
  setting for every assignment. Omitting `solutions` also keeps solutions private.
- `true`: publish on the next run.
- `"2026-10-15"`: publish on the next run on or after that date, using the
  computer's local date. Before then, show an availability note.

This is a static site: a scheduled date does not itself trigger a build.
Run the publish command on/after the date. Set `release` back to `false` and
publish to remove the solution file and link from the current site. Previously
published files may remain accessible in Git history or caches.

## Hosting setup

The site is its own Git repository inside `ECON139/website/`. The configured
GitHub repository must exist, and your Git credentials must permit pushes.
The repository is now created. HTTPS authentication uses the existing GitHub
CLI login through a repository-local Git credential helper. If that login expires,
run `gh auth login --hostname github.com --git-protocol https` and retry publishing.
The publishing command establishes `origin/main` as the upstream on its first
successful push; it expects the local branch to be `main`.

In the GitHub repository, enable **Settings → Pages → Deploy from a branch →
main / root**. After a push, allow a few minutes for deployment. A successful
push does not verify that Pages is enabled or that deployment has finished.

`index.html` is generated by `build.py`; change the mapping or renderer instead
of editing it directly. Styles live in `assets/style.css`.

## Developer checks

From `ECON139`:

```sh
python3 -m unittest discover -s website/tests -v
bash -n website/publish.sh
./website/publish.sh --check
```

Tests use temporary source folders and local Git repositories, including a local
bare remote. They never publish to GitHub or modify the actual course sources.
