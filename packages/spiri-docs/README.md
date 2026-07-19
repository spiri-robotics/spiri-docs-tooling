# spiri-docs

Sphinx extension for Spiri controlled documents — operational manuals and
anything else with a revision number that someone outside the company relies on.

```python
# docs/conf.py
extensions = ["myst_parser", "spiri_docs"]
```

Everything follows from a `revisions.yaml` beside `docs/`:

```yaml
document_number: SPIRI-OM-001
regulator_facing: true
distribution_statement: Uncontrolled when printed.

revisions:
  - revision: "1.0"
    date: 2026-07-19
    effective_date: 2026-08-01
    author: A. Author
    approver: B. Approver
    summary: Initial issue.
```

On every build the extension:

- **validates** the file — a `regulator_facing` document without an
  `effective_date` or `approver` fails the build rather than shipping;
- sets `version` and `release` to the current revision;
- exposes `{{ document_number }}`, `{{ revision }}`, `{{ effective_date }}`,
  `{{ approver }}` and friends as MyST substitutions for the cover page;
- stamps document number, revision and `Page N of M` into the **PDF footer**;
- names the PDF `SPIRI-OM-001_rev1.0.pdf`.

And provides one directive:

```markdown
```{revision-history}
```
```

which renders the history newest-first, showing only the columns the document
actually populates.

## Why an extension and not the template

`spiri-doc-template` runs once, at project generation. This runs on every build.
Validation, revision plumbing, and PDF document control have to hold every time
the docs are built — a template can only put a correct file down on day one and
has no way to detect drift afterwards. Theme, CSS and structure stay in the
template, where being decided once is the point.

## Configuration

| Option | Default | Meaning |
| --- | --- | --- |
| `spiri_docs_revisions` | `"../revisions.yaml"` | Path to the revision file, relative to `conf.py`. |

## Not here yet

Hazard admonitions (DANGER / WARNING / CAUTION / NOTICE). Which standard to
follow — ANSI Z535.6, ISO 3864 — is an editorial decision, and shipping markup
before it is made means migrating every manual later. Sphinx's built-in
`danger`, `warning`, `caution` and `note` are fine in the meantime.
