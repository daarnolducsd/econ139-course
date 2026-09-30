# Website agent instructions

Applies to `website/` and its subdirectories. Also follow applicable parent
instructions. Read `README.md` and `PROJECT_NOTES.md` before changing workflows.

## Layout and content

- `course.json`: course information, ordered topic/deck mapping, source PDF paths,
  publication flags, and dated problem-set solution releases.
- `build.py`: standard-library Python builder. `index.html` is generated; do not
  edit it directly. Styling lives in `assets/style.css`.
- `slides/`, `slides/dataset/`, `psets/`, and `syllabus/`: managed public PDF output.
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
./website/publish.sh --check
./website/publish.sh --local
python3 -m unittest discover -s website/tests -v
bash -n website/publish.sh
```

`--check` does not write. `--local` writes generated output without committing or
pushing. Only mapped, published files may be copied; solutions are private unless
explicitly released. Validate all inputs before changing output, preserve
unchanged files, and remove stale PDFs when their publication is revoked.
Do not treat empty Dropbox placeholders as valid PDFs. Source files are never
modified by the website build, and slides must be exported to PDF separately.

For layout changes, use `./website/publish.sh --preview` and inspect desktop and
narrow widths, navigation, readability, and download links. Publishing tests
must use temporary repositories, not the live GitHub remote.

## Publishing and documentation

Run the default `publish.sh` only when live publishing is requested. It commits
website files and pushes to `origin/main`; a successful push does not confirm
that GitHub Pages deployment has completed. Keep unrelated files out of commits.
Maintain retry behavior for pending commits after a failed push.

Update `README.md` and `PROJECT_NOTES.md` when workflows change. Report actual
checks and distinguish local verification from a live publication.
