"""End-to-end checks against a real Sphinx build.

The unit tests cover the validation rules. These cover the wiring, which is
where the subtle failures live -- notably that ``latex_documents`` cannot be
tested for emptiness to find out whether a project set it.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from sphinx.application import Sphinx
from sphinx.errors import ConfigError

CONF_PY = """
project = "Test Manual"
author = "Spiri"
extensions = ["myst_parser", "spiri_docs"]
"""

INDEX_MD = """
# Test Manual

Document {{ document_number }} revision {{ revision }}, status {{ document_status }},
approved by {{ approver }}.

```{revision-history}
```
"""

REVISIONS = """
document_number: SPIRI-OM-001
regulator_facing: true
revisions:
  - revision: "1.0"
    date: 2026-01-05
    effective_date: 2026-02-01
    author: A. Author
    approver: B. Approver
    summary: Initial issue.
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "conf.py").write_text(CONF_PY)
    (docs / "index.md").write_text(INDEX_MD)
    (tmp_path / "revisions.yaml").write_text(REVISIONS)
    return tmp_path


def build(project: Path, builder: str) -> Sphinx:
    out = project / "_build" / builder
    shutil.rmtree(out, ignore_errors=True)
    app = Sphinx(
        srcdir=str(project / "docs"),
        confdir=str(project / "docs"),
        outdir=str(out),
        doctreedir=str(project / "_build" / "doctrees"),
        buildername=builder,
        warningiserror=True,
        status=None,
    )
    app.build()
    return app


def test_release_comes_from_the_revision_file(project: Path) -> None:
    app = build(project, "html")
    assert app.config.release == "1.0"
    assert app.config.version == "1.0"


def test_substitutions_reach_the_page(project: Path) -> None:
    build(project, "html")
    html = (project / "_build" / "html" / "index.html").read_text()
    assert "SPIRI-OM-001" in html
    assert "B. Approver" in html
    assert "Issued" in html


def test_revision_history_directive_renders_a_table(project: Path) -> None:
    build(project, "html")
    html = (project / "_build" / "html" / "index.html").read_text()
    assert "spiri-revision-history" in html
    assert "Initial issue." in html
    assert "Approved by" in html


def test_pdf_is_named_for_the_document_not_the_project(project: Path) -> None:
    # Regression: `latex_documents` has a lazy default, so reading it
    # materialises an entry named after the project ("testmanual.tex") and it
    # never looks unset. Guarding on emptiness silently did nothing.
    app = build(project, "latex")
    assert (project / "_build" / "latex" / "SPIRI-OM-001_rev1.0.tex").is_file()
    assert app.config.latex_documents[0][1] == "SPIRI-OM-001_rev1.0.tex"


def test_a_project_may_still_name_its_own_pdf(project: Path) -> None:
    (project / "docs" / "conf.py").write_text(
        CONF_PY + '\nlatex_documents = [("index", "custom.tex", "T", "A", "manual", False)]\n'
    )
    app = build(project, "latex")
    assert app.config.latex_documents[0][1] == "custom.tex"


def test_document_control_reaches_the_latex_preamble(project: Path) -> None:
    build(project, "latex")
    tex = (project / "_build" / "latex" / "SPIRI-OM-001_rev1.0.tex").read_text()
    assert "SPIRI-OM-001" in tex
    assert "Effective 2026-02-01" in tex
    assert r"\pageref{LastPage}" in tex


def test_an_unapprovable_revision_fails_the_build(project: Path) -> None:
    (project / "revisions.yaml").write_text(REVISIONS.replace("approver: B. Approver", ""))
    with pytest.raises(ConfigError, match="approver"):
        build(project, "html")


def test_a_missing_revision_file_fails_the_build(project: Path) -> None:
    (project / "revisions.yaml").unlink()
    with pytest.raises(ConfigError, match="no revision file"):
        build(project, "html")
