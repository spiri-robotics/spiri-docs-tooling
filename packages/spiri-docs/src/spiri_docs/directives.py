"""Directives that render revision data into the document, and the two signal
word panels docutils has no equivalent for.

ANSI Z535.6 uses five panels. DANGER, WARNING and CAUTION map onto docutils
admonitions that already exist, and are restyled into panels by
``static/spiri-safety.css`` rather than redefined here -- so a manual written
before this extension existed becomes compliant without its source being touched.

NOTICE and SAFETY INSTRUCTIONS have no such equivalent, so they are defined
below. What they share is as important as what they say: neither is a hazard
alert, so neither carries the safety alert symbol.

NOTICE is the one writers reach for most and get wrong most. It covers practices
risking *property damage* -- the aircraft, equipment, data -- and nothing else.
The moment a person can be hurt it is CAUTION or higher. That boundary is why it
cannot simply be ``note``: a note is not a safety message at all, and giving
property-damage warnings the weight of a friendly aside is how they get skipped.

SAFETY INSTRUCTIONS is not a hazard message in either direction. It marks
procedures and safe work practices -- how to do the thing correctly -- which is
why it is green rather than one of the alerting colours, and why it reads as
guidance rather than as an alarm.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.directives.admonitions import BaseAdmonition
from sphinx.util.docutils import SphinxDirective

if TYPE_CHECKING:
    from .revisions import RevisionHistory


class SignalWordAdmonition(BaseAdmonition):
    """Base for a Z535.6 panel that docutils does not already provide.

    Produces a generic ``admonition`` node carrying a class, rather than a node
    type of its own. That is deliberate: every builder and translation tool
    already knows what an admonition is, whereas a bespoke node would need a
    visitor written for each builder before the LaTeX side would so much as
    build.
    """

    #: The panel's signal word. Fixed by the standard, so the writer does not
    #: supply it -- a panel reading "Notice: important" is no longer a Z535.6
    #: panel, and the directive is the natural place to make that unavailable.
    signal_word: str = ""

    node_class = nodes.admonition
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {  # noqa: RUF012 - docutils' own shape for this
        "class": directives.class_option,
        "name": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        # BaseAdmonition takes the title from the first argument when the node
        # class is the generic one, and the CSS keys off the class.
        self.arguments = [self.signal_word.title()]
        css_class = self.signal_word.lower().replace(" ", "-")
        self.options["class"] = [css_class, *self.options.get("class", [])]
        return list(super().run())


class NoticeDirective(SignalWordAdmonition):
    """``:::{notice}`` -- property damage, no personal injury."""

    signal_word = "Notice"


class SafetyInstructionsDirective(SignalWordAdmonition):
    """``:::{safety-instructions}`` -- safe work practices and procedures."""

    signal_word = "Safety Instructions"


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
