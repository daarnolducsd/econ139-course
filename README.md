# ECON 139 — Course Website

A static course site published with GitHub Pages. Requires Python 3.9+ and Git;
no Python packages or JavaScript build tools are needed.

Configured site URL: https://daarnolducsd.github.io/econ139-course/
Remote: `https://github.com/daarnolducsd/econ139-course.git`

## Update slides and publish

1. Edit your slides in the usual course folder and **export them to PDF**,
   replacing the corresponding file in `ECON139/slides/`.
2. From the `ECON139` folder, run:

   ```sh
   ./website/publish.sh
   ```

The command validates every published PDF and local link, copies only changed
files, regenerates the page, commits the website files, and pushes to
`origin/main`. Existing URLs stay the same. No manual copying or HTML editing
is needed when updating an existing PDF. PowerPoint and LaTeX compilation is
not performed by this command.

From inside `website/`, use `./publish.sh` instead. An optional commit message
works too: `./website/publish.sh "Update minimum wage slides"`.

## Check, build locally, or preview

```sh
./website/publish.sh --check    # validate/report changes, without writing
./website/publish.sh --local    # build only; no commit or push
./website/publish.sh --preview  # build and serve at http://localhost:8000
```

Stop the preview with Ctrl-C. Choose a different port with
`PORT=8001 ./website/publish.sh --preview`.

A missing, empty, or non-PDF published source stops the build before it changes
any generated files. If Dropbox has not downloaded a file, make it available
offline and rerun the command. A failed push leaves the local commit intact;
fix the Git error and rerun the same command, which will retry the pending push.
An unchanged build with no pending commits does not create a new commit or push.

## Content and source-file mapping: course.json

All content settings live in `website/course.json`, not in Python:

| Setting | Meaning |
| --- | --- |
| `course` | Course title, term, instructor, and textbook URL |
| `lectures` | Ordered topic groups, with a source path and label for each deck |
| `reviews` | Ordered exam-review materials |
| `datasets` | Ordered dataset guides |
| `psets` | Ordered assignments and their solution-release settings |
| `syllabus.source` | Source syllabus; always published at `syllabus/syllabus.pdf` |

Every `source` is relative to the **ECON139 folder**, regardless of where you
run the command. PDF bytes are copied exactly; source files are never modified.

| Configured source | Published destination |
| --- | --- |
| `slides/01_perfect_competition.pdf` | `website/slides/01_perfect_competition.pdf` |
| `slides/dataset_slides/data_01_cps.pdf` | `website/slides/dataset/data_01_cps.pdf` |
| `pset/pset1/pset1.pdf` | `website/psets/pset1.pdf` |
| `syllabus/syllabusFA25.pdf` | `website/syllabus/syllabus.pdf` |

Only explicitly listed, published files are copied. Dropping a new PDF into a
source folder does **not** automatically publish it. To add a lecture, add an
entry to `lectures` in the desired position:

```json
{
  "topic": "New Topic",
  "decks": [
    {"label": "Slides", "source": "slides/14_new_topic.pdf"}
  ]
}
```

Group multiple decks by adding more entries to `decks`. To hide a topic, deck,
review, dataset, assignment, or syllabus, add `"published": false` to its object.
Omitting `published` means it is visible. Reordering entries changes their order
on the website. Removing/hiding an entry also removes its old published PDF on
the next build. These output folders are managed by the builder; do not store
hand-maintained files in them.

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
