# spiri-docs-tooling

Tooling for Spiri documentation projects — manuals, not application docs.

Two things live here, in one repository because they are coupled by definition:
the template generates a `conf.py` that calls the extension's API.

| Path | What it is |
| --- | --- |
| [`template/`](template/) | Copier template for a new manual |
| [`packages/spiri-docs/`](packages/spiri-docs/) | Sphinx extension, published to PyPI as `spiri-docs` |

## Starting a manual

```sh
copier copy gh:spiri-robotics/spiri-docs-tooling ./my-manual
cd my-manual
uv sync --group docs
make docs
```

You get a Sphinx project with chapters in Markdown, a revision history in YAML,
a Read the Docs config, CI, and — if you asked for PDF — a release workflow that
attaches the built PDF to a GitHub release.

### Built for non-developers

The generated project assumes its contributors write prose and nothing else.
They never see uv, Sphinx, or a command line:

- **A devcontainer** carrying the whole toolchain, including the Vale binary.
  The only things a contributor installs are VS Code and Docker Desktop, and
  [`CONTRIBUTING.md`](template/CONTRIBUTING.md.jinja) walks through both on
  Windows and macOS with no prior knowledge assumed.
- **`Ctrl+Shift+B` gives a live preview** — `sphinx-autobuild` on a forwarded
  port, with autosave on, so the manual refreshes as they type.
- **Tasks, not commands** — "Check writing style", "Check the manual for
  problems", "Build a PDF" appear under Terminal → Run Task.
- **A JSON schema for `revisions.yaml`**, so a malformed revision is flagged
  while typing rather than at build time.
- **`.gitattributes` pins LF endings**, which otherwise bite Windows
  contributors the moment a shell script reaches the Linux container.
- **Art assets go to Git LFS** — screenshots, photographs and design sources are
  stored out of line, so a manual that revises a 4 MB photograph ten times does
  not hand every future contributor 40 MB of history they cannot remove. The dev
  container installs git-lfs, CI fetches it, and a `docs.yml` job fails the pull
  request if a raster was committed directly — `filter=lfs` alone is silent when
  git-lfs is missing, which is exactly when you need to hear about it. SVG stays
  in plain Git: it diffs, and the cover logo is read straight from it.

## The split, and why

**The template runs once, at generation. The extension runs on every build.**
That is the whole basis for what goes where.

Things decided once per document live in the template: theme, CSS, chapter
structure, which chapters exist. If someone edits them afterwards, that is their
project's business.

Things that must hold on *every* build live in the extension: validating
`revisions.yaml`, putting the revision into the PDF footer, naming the PDF after
the document and revision. A template physically cannot enforce these — it has
no relationship with the project after generation, and no way to detect drift.
A manual whose footer lost its revision number because someone tidied `conf.py`
eighteen months ago is exactly the failure the extension prevents.

It also means style and theme changes propagate differently from structural
ones. A theme tweak in the template reaches existing manuals only when someone
runs `copier update` and resolves the merge. A change in the extension reaches
them on the next dependency bump — which for an issued controlled document you
may want to *pin*, so its appearance cannot change under a reader. Both are
available; pick per document.

## Why this is not part of spiri-app-template

An app's documentation describes code: autodoc, an API reference, a package on
`sys.path`. A manual describes a product to someone holding it: revisions,
approvals, hazard notices, a PDF that goes in a binder. The genuinely shared
part is about fifteen lines of `conf.py`, and the two are diverging, not
converging. Layering two copier templates onto one repo was considered and
rejected — the docs template would have to own `pyproject.toml`, CI, and the
`Makefile`, all of which `spiri-app-template` already owns.

## Developing

```sh
cd packages/spiri-docs
uv sync --all-groups
uv run pytest
```

To work on the template against a local checkout of the extension, add to the
generated project's `pyproject.toml`:

```toml
[tool.uv.sources]
spiri-docs = { path = "../spiri-docs-tooling/packages/spiri-docs", editable = true }
```

## Releasing

The extension and the template version together, on one tag stream.
`packages/spiri-docs/pyproject.toml` holds the version; tagging `v<version>`
publishes to PyPI via [`.github/workflows/publish.yml`](.github/workflows/publish.yml)
and marks the template state that goes with it.

## Not here yet

- **`spiri-vale-styles`** — the house style guide as a Vale package. Generated
  projects currently fall back to the Microsoft style. When the guide is
  settled, publish it and change one line in the template's `.vale.ini`; no
  manual repo needs reopening.
- **Hazard admonitions** — DANGER / WARNING / CAUTION / NOTICE as first-class
  directives. Blocked on choosing a standard (ANSI Z535.6 or ISO 3864);
  shipping markup before that decision means migrating every manual later.
