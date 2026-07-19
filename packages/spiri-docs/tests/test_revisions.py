"""The validation rules are the reason this package exists, so they get tests."""

from __future__ import annotations

import datetime as dt

import pytest
import yaml

from spiri_docs import latex
from spiri_docs.revisions import RevisionError, parse

CUSTOMER_FACING = """
document_number: SPIRI-UM-002
revisions:
  - revision: "1.0"
    date: 2026-01-05
    summary: Initial issue.
  - revision: "1.1"
    date: 2026-03-02
    summary: Corrected torque values.
"""

REGULATOR_FACING = """
document_number: SPIRI-OM-001
regulator_facing: true
distribution_statement: Uncontrolled when printed.
revisions:
  - revision: "1.0"
    date: 2026-01-05
    effective_date: 2026-02-01
    author: A. Author
    approver: B. Approver
    summary: Initial issue.
"""


def load(text: str):
    return parse(yaml.safe_load(text))


def test_current_is_the_last_revision() -> None:
    history = load(CUSTOMER_FACING)
    assert history.current.revision == "1.1"
    assert history.current.date == dt.date(2026, 3, 2)


def test_customer_facing_does_not_require_approval() -> None:
    history = load(CUSTOMER_FACING)
    assert history.regulator_facing is False
    assert history.current.approver is None


DRAFT_REGULATOR = """
document_number: SPIRI-OM-001
regulator_facing: true
revisions:
  - revision: "0.1"
    date: 2026-01-05
    summary: Initial draft.
    draft: true
"""


def test_draft_skips_the_approval_requirements() -> None:
    # A document cannot be approved before it is written, so a scaffolded
    # regulator-facing manual has to build on the first try.
    history = load(DRAFT_REGULATOR)
    assert history.current.draft is True
    assert history.current.approver is None


def test_issuing_a_draft_triggers_the_approval_requirements() -> None:
    text = DRAFT_REGULATOR.replace("    draft: true\n", "")
    with pytest.raises(RevisionError, match="effective_date"):
        load(text)


def test_placeholder_approver_does_not_count_as_approval() -> None:
    # The whole point of the check is that a manual cannot ship saying
    # "Approved by: TODO".
    text = REGULATOR_FACING.replace("approver: B. Approver", "approver: TODO")
    with pytest.raises(RevisionError, match="approver"):
        load(text)


@pytest.mark.parametrize("placeholder", ["TODO", "tbd", "N/A", "FIXME", "'?'", "TODO."])
def test_placeholder_spellings_are_all_rejected(placeholder: str) -> None:
    text = REGULATOR_FACING.replace("approver: B. Approver", f"approver: {placeholder}")
    with pytest.raises(RevisionError, match="approver"):
        load(text)


def test_draft_is_marked_in_the_pdf_filename_and_footer() -> None:
    history = load(DRAFT_REGULATOR)
    assert latex.target_basename(history) == "SPIRI-OM-001_rev0.1-DRAFT"
    assert "DRAFT" in latex.preamble(history)


def test_regulator_facing_requires_effective_date() -> None:
    text = REGULATOR_FACING.replace("    effective_date: 2026-02-01\n", "")
    with pytest.raises(RevisionError, match="effective_date"):
        load(text)


def test_regulator_facing_requires_approver() -> None:
    text = REGULATOR_FACING.replace("    approver: B. Approver\n", "")
    with pytest.raises(RevisionError, match="approver"):
        load(text)


def test_quoted_date_is_rejected() -> None:
    # A quoted date is a string, and silently accepting it means guessing at the
    # format later. Better to say so at build time.
    text = CUSTOMER_FACING.replace("date: 2026-01-05", 'date: "05/01/2026"')
    with pytest.raises(RevisionError, match="ISO date"):
        load(text)


def test_out_of_order_revisions_are_rejected() -> None:
    text = CUSTOMER_FACING.replace("date: 2026-03-02", "date: 2025-12-01")
    with pytest.raises(RevisionError, match="oldest first"):
        load(text)


def test_empty_revision_list_is_rejected() -> None:
    with pytest.raises(RevisionError, match="non-empty"):
        parse({"document_number": "X", "revisions": []})


def test_missing_document_number_is_rejected() -> None:
    with pytest.raises(RevisionError, match="document_number"):
        parse({"revisions": [{"revision": "1.0", "date": dt.date.today(), "summary": "x"}]})


def test_pdf_is_named_for_document_and_revision() -> None:
    assert latex.target_basename(load(CUSTOMER_FACING)) == "SPIRI-UM-002_rev1.1"


def test_underscores_in_document_number_are_escaped_for_latex() -> None:
    history = parse(
        {
            "document_number": "SPIRI_OM_1",
            "revisions": [{"revision": "1.0", "date": dt.date(2026, 1, 1), "summary": "x"}],
        }
    )
    preamble = latex.preamble(history)
    assert r"SPIRI\_OM\_1" in preamble
    assert "lastpage" in preamble


def test_preamble_falls_back_to_issue_date_without_an_effective_date() -> None:
    assert "Issued 2026-03-02" in latex.preamble(load(CUSTOMER_FACING))
    assert "Effective 2026-02-01" in latex.preamble(load(REGULATOR_FACING))
