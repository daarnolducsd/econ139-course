# Website agent instructions

Applies to `website/` and its subdirectories. Also follow applicable parent
instructions. Read `README.md` and `PROJECT_NOTES.md` before changing workflows.

## Layout and content

- `course.json`: course information and reusable material catalog keyed by stable
  IDs, source paths, fixed download destinations, explicit topic bundles, publication flags, and dated solution releases.
- `schedule.json`: exactly Weeks 1–10, with titles, catalog material IDs, readings,
  assignment reminders, data/code resource IDs, and optional dates. Repeat an ID across weeks
  for continuing topics; PDFs are copied only once.
- Week `locked` flags control weekly availability. Assignment `locked` flags in
  course.json are independent and default to true. Currently only Week 1 is open.
- `build.py`: standard-library Python builder. `index.html` is generated; do not
  edit it directly. Styling lives in `assets/style.css`.
- `SOURCE_FILES.md`: generated original-to-public mapping; do not edit directly.
- `slides/`, `slides/dataset/`, `psets/`, `syllabus/`, and `downloads/`: managed public output.
  Source paths in the mapping are relative to the parent ECON139 course folder.
- `publish.sh`: local build/preview and Git publishing commands. This directory
  is its own Git repository, publishing to `origin/main` for GitHub Pages.
- `tests/`: isolated build tests and publishing tests using local Git remotes.

Preserve existing public paths unless a change is requested, and update all
references when changing a path. Use course sources or user-provided information
for dates and course details. Keep edits focused on the requested task.

## Build and verify

From ECON139:

```sh
./website/publish.sh --sources
./website/publish.sh --check
./website/publish.sh --local
python3 -m unittest discover -s website/tests -v
bash -n website/publish.sh
```

`--check` does not write. `--local` writes generated output without committing or
pushing. Only mapped, published files may be copied; solutions are private unless
explicitly released. Validate all inputs before changing output, preserve
unchanged files, and remove stale managed files when their publication is revoked.
Do not treat empty Dropbox placeholders as valid PDFs. Source files are never
modified by the website build, and slides must be exported to PDF separately.
Data/code originals live in materials/<topic>/data/ and code/. Use the exact
paths in course.json, never filename searches or fallbacks to other directories.
Topic ZIPs include only published data/code members and an explicit README;
never archive an entire directory or include outputs/private files. Preserve
explicit destination paths when relocating sources. Generated copies must match their originals
byte for byte. Keep the page independent of quarter-specific Canvas URLs.

For layout changes, use `./website/publish.sh --preview` and inspect desktop and
narrow widths, navigation, readability, and download links. Publishing tests
must use temporary repositories, not the live GitHub remote.

## Publishing and documentation

### Assignment release warnings and locked content

- Before preparing a website commit or running the publisher, inspect the
  catalog, proposed build outputs, and staged/unstaged changes for new or revised
  problem-set PDFs. Include replacements at an existing URL, not just newly
  named files. Warn David before committing or publishing these files, naming
  the affected assignments and their exact public paths.
- Explain that a local commit records the PDF in Git history and a subsequent
  push to this public repository makes that history accessible. A generic request
  to change styling or pacing is not authorization to release a new assignment.
  If release intent is unclear, clarify it before including the assignment;
  continue independent, reversible preparation and checks in the meantime.
  If David already explicitly authorized that assignment's release, give the
  warning without asking for the same authorization again.
- Keep unreleased problem sets in their original course folders. When adding
  them to the catalog, use `locked: true` until release is authorized; this keeps
  the title visible while withholding the PDF. Assignment locks default to true.
  Use `published: false` to hide the title entirely; publication flags still
  default to true. Keep `solutions.release: false` independently. Unlocking a
  week must never automatically unlock its assignments.
- A visual lock or missing download button only changes the page. If the PDF is
  still deployed, anyone with its direct URL can download it. A lock must
  also withhold unreleased files from generated public output and public Git
  commits. Do not implement locks solely with CSS, JavaScript, or disabled links.
- Locked weeks must not leak content through Additional materials or topic ZIPs.
  Only open-week data/code may enter ZIPs. Shared files remain available if used
  by an open week. With any week locked, unassigned non-assignment materials must
  also be withheld. Keep locked entries in SOURCE_FILES.md with clear availability
  labels, so David can still locate their exact editable originals.
- Removing an already published PDF from the current site can stop its current
  download URL from working, but ordinary deletion leaves earlier versions in
  Git history. It cannot revoke downloaded copies or guarantee removal from
  caches. Do not describe relocking previously published assignments as making
  them confidential again. Do not rewrite history without explicit authorization.
- These instructions guide agent-assisted commits and publishing; they are not
  an automatic Git hook or publisher check. If an automatic guard is requested,
  implement and verify it separately.

Run the default `publish.sh` only when live publishing is requested. It commits
website files and pushes to `origin/main`; a successful push does not confirm
that GitHub Pages deployment has completed. Keep unrelated files out of commits.
Maintain retry behavior for pending commits after a failed push.

Update `README.md` and `PROJECT_NOTES.md` when workflows change. Report actual
checks and distinguish local verification from a live publication.
