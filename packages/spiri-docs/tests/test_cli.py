"""CI names its published files from this, so a change here renames artifacts."""

from __future__ import annotations

import pytest

from spiri_docs.__main__ import main

ISSUED = """
document_number: SPIRI-OM-001
revisions:
  - revision: "1.0"
    date: 2026-01-05
    summary: Initial issue.
  - revision: "1.2"
    date: 2026-03-02
    effective_date: 2026-03-09
    summary: Corrected torque values.
"""

DRAFT = """
document_number: SPIRI-OM-001
revisions:
  - revision: "1.3"
    date: 2026-04-01
    summary: Rewriting the pre-flight section.
    draft: true
"""


@pytest.fixture
def revisions(tmp_path):
    def write(text: str):
        path = tmp_path / "revisions.yaml"
        path.write_text(text)
        return str(path)

    return write


def run(capsys, *argv) -> tuple[int, str]:
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_name_is_the_pdf_stem(revisions, capsys):
    code, out = run(capsys, "name", "--revisions", revisions(ISSUED))
    assert code == 0
    assert out.strip() == "SPIRI-OM-001_rev1.2"


def test_a_draft_says_so_in_the_filename(revisions, capsys):
    # The whole point of the suffix: a printed draft must not be mistaken for an
    # issued revision, and the filename is what survives being emailed around.
    _, out = run(capsys, "name", "--revisions", revisions(DRAFT))
    assert out.strip() == "SPIRI-OM-001_rev1.3-DRAFT"


def test_fields_are_shell_assignments(revisions, capsys):
    code, out = run(capsys, "fields", "--revisions", revisions(ISSUED))
    assert code == 0
    fields = dict(line.split("=", 1) for line in out.strip().splitlines())
    assert fields == {
        "name": "SPIRI-OM-001_rev1.2",
        "document_number": "SPIRI-OM-001",
        "revision": "1.2",
        "draft": "false",
        "date": "2026-03-02",
        "effective_date": "2026-03-09",
    }


def test_draft_is_the_string_actions_compares_against(revisions, capsys):
    # release.yml refuses to publish on `draft == 'true'`; anything else there
    # (True, 1) silently issues a draft as a controlled document.
    _, out = run(capsys, "fields", "--revisions", revisions(DRAFT))
    assert "draft=true" in out.splitlines()


def test_effective_date_falls_back_to_the_revision_date(revisions, capsys):
    _, out = run(capsys, "fields", "--revisions", revisions(DRAFT))
    assert "effective_date=2026-04-01" in out.splitlines()


def test_a_bad_file_fails_without_a_traceback(capsys, tmp_path):
    code = main(["name", "--revisions", str(tmp_path / "nope.yaml")])
    assert code == 1
    assert "nope.yaml" in capsys.readouterr().err
