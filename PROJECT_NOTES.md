# ECON 139 Website — Project Notes

## Current workflow

- `website/` is a separate Git repository; branch `main`.
- Origin: `https://github.com/daarnolducsd/econ139-course.git`.
- Configured site URL: https://daarnolducsd.github.io/econ139-course/.
- Textbook: https://daarnolducsd.github.io/econ139/index.html (separate Quarto repo).
- `course.json` is the content and source-file mapping. Its initial entries
  preserve the existing Fall 2025 term, topic grouping, titles, ordering, and
  public URLs. All problem-set solutions remain private.
- `build.py` reads only explicitly mapped, published PDFs from the parent course
  folder, validates all inputs/local links before writing, and updates only
  changed bytes. It removes PDFs no longer included in the published mapping.
- `index.html` is generated. Styling remains in `assets/style.css`.
- `./website/publish.sh` works from the ECON139 folder; `./publish.sh` works from
  inside website. Both build, commit website files, and push to origin/main.
- `--check` validates without writing; `--local` builds without Git operations;
  `--preview` builds and serves at localhost:8000.
- Publishing establishes the upstream on the first successful push and retries
  an existing local commit after a failed push. Unrelated root files are not
  automatically staged; unrelated pre-staged files block publishing.

## Current validation and hosting status

At inspection on September 30, 2026, source PDFs became available after Dropbox
finished downloading them. A local build updated the website syllabus from its
source; a second check reported zero changes. All 23 public PDFs and local links
validated, and the generated HTML and CSS remained unchanged.
The course repository has now been created. SSH authentication returned
`Permission denied (publickey)`, so origin uses HTTPS with the existing GitHub
CLI login via a repository-local credential helper. HTTPS access is verified.
The publishing command establishes the upstream and retries saved commits.
GitHub Pages is configured to deploy from main / root. The live deployment and
sample lecture, problem-set, and syllabus downloads were verified. The textbook
repository is separate. Both outbound textbook links open in a new tab and
include accessible labels indicating that behavior.

Tests cover incremental builds, missing/empty sources, publishing controls,
solution release dates, local-link validation, and publish/retry behavior with a
local bare Git remote. See README.md for commands and content-editing examples.

## Future work

The current light-blue theme, sticky navigation, and grouped lecture table are
preserved. The visual redesign and a possible weekly schedule remain separate
future tasks. No scheduled builds or automatic slide compilation are configured.
