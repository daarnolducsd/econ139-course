# ECON 139 Website — Project Notes

## Current workflow

- `website/` is a separate Git repository; branch `main`.
- Origin: `https://github.com/daarnolducsd/econ139-course.git`.
- Configured site URL: https://daarnolducsd.github.io/econ139-course/.
- Textbook: https://daarnolducsd.github.io/econ139/index.html (separate Quarto repo).
- `course.json` is a reusable material catalog keyed by semantic IDs. It retains
  the Fall 2025 course information and all existing PDF sources/public URLs.
  All problem-set solutions remain private.
- `schedule.json` is the quarter-specific weekly arrangement. Move IDs or
  reading/assignment objects between weeks to change pacing, without moving PDFs.
  Exactly Weeks 1–10 are required; IDs may repeat across weeks.
- `build.py` reads only explicitly mapped, published files from the parent course
  folder, validates all inputs/local links before writing, and updates only
  changed bytes. It removes managed files no longer included in the mapping.
- `SOURCE_FILES.md` is generated from the same catalog and destination function
  used by the builder. `--sources` prints the current map without writes.
- `materials/<topic>/` holds authoritative teaching originals, grouped by topic
  with data/, code/, and README.md. Preparation scripts/raw inputs remain under
  code/ and data/. Topic outputs/ directories contain local results only.
- `downloads/` holds generated public copies, README downloads, and topic ZIPs.
  Explicit destination fields preserve all pre-migration download URLs.
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

## Canvas schedule import and weekly layout

The Fall 2025 `.imscc` export in `ECON139/canvas_page/` contains weekly modules
whose plan pages supply the slide, reading, assignment, and data/code links.
Only the metadata and plan pages were read; the archive was not extracted into
the public site. The local `canvas_page/weekly-import-report.json` records the
mapping and is outside the website repository.

Website Week 1 combines Canvas Weeks 0 and 1, deduplicating the introductory
slides and keeping their readings/activities. Canvas Weeks 2–10 retain their
numbers. Continuation decks (CPS, monopsony theory, and trade) appear in all
referencing weeks. There are still exactly 23 public PDFs, with unchanged bytes
and URLs. No private exam or solution PDFs were added from the export.

Old specific calendar dates and one-off announcements were omitted. The site
continues to identify this schedule as Fall 2025; adopting it for another quarter
requires updating the term, syllabus, and pacing. All Canvas links were subsequently
removed; assignment and practice titles remain plain-text reminders, and mapped
problem sets retain direct PDF downloads. Week 3's Chapter 4 reading originally
pointed to Chapter 3 in Canvas; its link now targets `04.html`, matching the local
textbook's Monopsony Theory chapter.

The generated page uses separate week cards, compact PDF rows, numbered sticky
navigation, a problem-set download section, and four consistently placed panels.
The palette is warm off-white, charcoal, and muted green. Reading/textbook links open new tabs with accessible labels; data/code links
download files directly.

## Independent data/code downloads and source clarity

Fourteen public resources from the weekly plan are now explicitly mapped to
current local originals: CPS CSV/DTA and Python/Stata/R code; ACS healthcare
CSV/DTA/XLSX and Python/Stata/R code; O*NET work activities CSV/DTA/XLSX.
The six code files initially read as zero-byte Dropbox placeholders. After the
user made the entire course folder available offline, they became readable;
no archive fallback or duplicate source copies were created. The builder does
not modify the code, its internal analysis paths, or any source data.

The site/configuration have no Canvas links or course IDs. Assignment URLs were
removed; non-PDF activities remain reusable plain-text reminders. No additional
exam or solution PDFs were published. The 23 existing public PDF paths/bytes
remain unchanged; there are now 37 published files in total, plus generated HTML,
source documentation, and .nojekyll.

The publisher includes generated downloads and SOURCE_FILES.md. The source map
lists originals, generated website copies, and weekly placements. Original files
are authoritative: an output-only edit is overwritten, while editing a similarly
named unmapped file cannot affect the site. Duplicate catalog mappings to one
resolved source are rejected; weekly ID reuse remains supported.

Twenty-five tests pass, including content changes to the exact mapped code/data
sources, unchanged-size/timestamp updates, ignoring unmapped duplicates, failure
before writes for unavailable/invalid files, shared weekly downloads, revocation,
source listing without Git/writes, and publishing edited code/data with the same
command using a temporary local Git remote. At that stage, the local build
validated all 37 published files and local links. Browser visual verification was unavailable
because no connected browser was exposed and native Computer Use permissions
were not granted; the user requested proceeding without a Safari preview. This
revision has been built locally and has not been pushed to GitHub.

No scheduled builds or automatic slide compilation are configured.

## Topic folders and complete downloads

The user approved moving the currently published originals into materials/cps/,
materials/acs/, and materials/onet/, with data/, code/, and short topic READMEs.
All 14 originals were moved rather than left as duplicate editable sources.
All eight dataset hashes remain unchanged; six teaching scripts gained portable
input paths and write figures to outputs/ instead of data directories. Rscript
also handles R's encoded spaces in --file paths. CPS/ACS Python scripts locate
the topic relative to __file__; RStudio and Stata instructions explain working
directories, and Stata accepts an optional topic-directory argument.

The source/destination distinction is now explicit in course.json. Every moved
resource retains its previous individual download URL. Bundles list data/code IDs
and an explicit README; the builder creates deterministic CPS, ACS, and O*NET
ZIPs from those approved bytes, without scanning topic folders. Published members
that are hidden are excluded from ZIPs; a fully hidden topic loses its ZIP/README.
Each relevant weekly Data & code panel offers its ZIP and instructions download.

The duplicate audit found a different Problem Set 1 CPS CSV, an identical CPS
DTA assessment snapshot, and different ACS/O*NET working versions. These were
retained outside the teaching source mapping. Remaining old code/data folders
have notices directing edits to materials/. materials/MIGRATION_NOTES.md records
moves, checksums, and references updated. CPS helper scripts now read the new
source; ACS and O*NET preparation scripts write teaching exports to materials/.
Only two dataset path literals were updated in textbook/cps.qmd and acs.qmd;
the textbook's other pre-existing edits and generated output were preserved.

Thirty workflow tests pass. New coverage checks URL preservation through a move,
exact ZIP membership, content-based updates to both individual files and ZIPs,
README updates, unchanged timestamp-only edits, hidden-member removal, unsafe
destinations, and rejection of assignments in data/code bundles. All six CPS/ACS
examples (Python, R, Stata) also ran successfully from extracted ZIPs in a new
folder containing spaces, producing the expected PNG/HTML outputs and leaving
inputs unchanged. Stata logs were checked for end-of-file completion and errors.
Plotly was installed only in a temporary verification environment. Existing local
NumPy accelerator incompatibilities were bypassed in that verification harness
by disabling optional numexpr/bottleneck; the teaching algorithms were run with
real pandas data and real plotting libraries. Analysis inputs remain unchanged.

The final local build validates 43 public files: 23 PDFs, 14 data/code files,
three README downloads, and three ZIPs. An unchanged rebuild reports zero changes.
The migration was committed as 7704a70 and pushed; its GitHub Pages build was
verified as complete.

## Consistent weekly panels and navigation

The selected two-by-two layout is now implemented in the actual site renderer
and stylesheet. Every week retains Slides, Readings, Assignments, and Data & code
in that order, with an explicit empty state when needed. On narrow screens the
panels stack. The selected soft stone palette uses a #F0F0EC page background and
the same lighter #FAFAF7 background for every week card. Headers use slate gray,
sand, dusty mauve, and eucalyptus;
data/code downloads remain visible without a dropdown.

Optional data/code `group` labels in course.json combine alternate formats into
one row while preserving every source and public URL. Topic ZIPs and instructions
remain prominent above the individual links. Navigation uses a small deferred
script to mark the week at the top of the reading area with aria-current; it does
not require changes when content moves between weeks. At the user's request,
the header omits the term and the Canvas submission note; the term is retained
only as internal course metadata. The user approved this complete layout and
palette for publication.

Validation: 31 isolated workflow tests pass, all 43 approved public files and
local links validate, and an unchanged rebuild writes nothing. A separate
headless Chrome session verified the grid at 1280px, stacked panels at 375px and
320px, no horizontal overflow, all ten active-week states, and clearing the
highlight through the Problem sets navigation. Native anchors and the ACS
download links also work with JavaScript disabled. Desktop and mobile screenshots
were inspected; the local browser-check artifacts are outside the website repo.
