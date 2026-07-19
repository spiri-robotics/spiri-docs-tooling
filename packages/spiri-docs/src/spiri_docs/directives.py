"""Directives that render revision data into the document.

Only one for now. Hazard admonitions (DANGER/WARNING/CAUTION/NOTICE, per
ANSI Z535.6 or ISO 3864) are the obvious next addition, but which standard Spiri
follows is a decision for the head of documents, and guessing at it would mean
shipping markup that has to be migrated later. Sphinx's built-in ``danger``,
``warning``, ``caution`` and ``note`` are fine until then.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes
from sphinx.util.docutils import SphinxDirective

if TYPE_CHECKING:
    from .revisions import RevisionHistory


def _cell(text: str) -> nodes.entry:
    return nodes.entry("", nodes.paragraph(text=text))


class RevisionHistoryDirective(SphinxDirective):
    """``.. revision-history::`` -- the revision table, generated from data.

    Newest first, because the reader of a manual wants to know what changed most
    recently, not how it began.
    """

    has_content = False
    option_spec = {}

    def run(self) -> list[nodes.Node]:
        history: RevisionHistory | None = getattr(self.env, "spiri_docs_history", None)
        if history is None:  # pragma: no cover - only if setup() did not run
            return [
                self.state.document.reporter.error(
                    "revision-history: no revision data loaded", line=self.lineno
                )
            ]

        # Only show the columns this document actually populates, so a
        # customer-facing manual with no approvals is not a table of empty cells.
        show_effective = any(rev.effective_date for rev in history.revisions)
        show_author = any(rev.author for rev in history.revisions)
        show_approver = any(rev.approver for rev in history.revisions)

        headers = ["Revision", "Date"]
        if show_effective:
            headers.append("Effective")
        headers.append("Summary")
        if show_author:
            headers.append("Author")
        if show_approver:
            headers.append("Approved by")

        # Summary is the column that actually holds prose, so give it the slack.
        widths = [max(3, 12 - len(h)) if h != "Summary" else 30 for h in headers]

        table = nodes.table(classes=["spiri-revision-history"])
        tgroup = nodes.tgroup(cols=len(headers))
        table += tgroup
        for width in widths:
            tgroup += nodes.colspec(colwidth=width)

        head_row = nodes.row()
        for header in headers:
            head_row += _cell(header)
        tgroup += nodes.thead("", head_row)

        tbody = nodes.tbody()
        for revision in reversed(history.revisions):
            row = nodes.row()
            row += _cell(
                f"{revision.revision} (draft)" if revision.draft else revision.revision
            )
            row += _cell(revision.date.isoformat())
            if show_effective:
                row += _cell(
                    revision.effective_date.isoformat() if revision.effective_date else "--"
                )
            row += _cell(revision.summary)
            if show_author:
                row += _cell(revision.author or "--")
            if show_approver:
                row += _cell(revision.approver or "--")
            tbody += row
        tgroup += tbody

        return [table]
