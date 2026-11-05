"""The LaTeX side of document control.

This is the code that most justifies the extension existing. Putting a document
number and revision in a PDF footer means fancyhdr overrides, ``lastpage``, and
``\\AtBeginDocument`` ordering -- fiddly TeX that is got right once and then
never thought about again. Copied into every manual's ``conf.py`` it would
drift, and the symptom of drift is a shipped PDF with a wrong footer.
"""

from __future__ import annotations

import os
import re

from .revisions import RevisionHistory

#: Characters TeX treats specially in ordinary text. Document numbers are exactly
#: the kind of string that contains underscores.
_LATEX_SPECIAL = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def software_version() -> str | None:
    """The software version this build documents, from ``SPIRI_DOCS_SOFTWARE_VERSION``.

    The revision says which edition of the document this is; this says which
    release of the software it describes. They move separately, so both have to
    show. Set by the build rather than worked out from git, because a manual for
    hardware has no software version, and must keep its name and footer as they
    are. Read from the environment so that Sphinx and ``python -m spiri_docs``,
    which CI uses to find the PDF, can't disagree.
    """
    return os.environ.get("SPIRI_DOCS_SOFTWARE_VERSION", "").strip() or None


def escape(text: str) -> str:
    """Escape *text* for use in LaTeX body copy."""
    return "".join(_LATEX_SPECIAL.get(char, char) for char in text)


def safe_filename(text: str) -> str:
    """Reduce *text* to something safe as a filename stem for latexmk."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-.")
    return cleaned or "manual"


def target_basename(history: RevisionHistory, software: str | None = None) -> str:
    """The PDF filename stem: document number, revision and any software version.

    A controlled document should be identifiable from its filename alone, after
    someone has emailed it around and lost the page it came from -- which is
    also why a draft says so in the filename. The software version is there
    because two releases can share a revision: without it, their PDFs have the
    same name and, where an API reference is generated from the code, different
    contents.
    """
    suffix = "-DRAFT" if history.current.draft else ""
    stem = f"{history.document_number}_rev{history.current.revision}{suffix}"
    return safe_filename(f"{stem}_{software}" if software else stem)


def preamble(history: RevisionHistory, software: str | None = None) -> str:
    """LaTeX preamble fragment putting document control into every page footer."""
    current = history.current
    document_number = escape(history.document_number)
    revision = escape(current.revision)

    if current.draft:
        # A printed draft that does not say so is the thing most likely to end
        # up in an operator's hands as if it were issued.
        effective = f"DRAFT -- {current.date.isoformat()} -- not for operational use"
    elif current.effective_date:
        effective = f"Effective {current.effective_date.isoformat()}"
    else:
        effective = f"Issued {current.date.isoformat()}"

    # Sphinx uses fancyhdr already and defines two styles: `normal` for body
    # pages and `plain` for the first page of each chapter. A manual wants the
    # control block on both -- a page torn out of a binder should still identify
    # itself -- so redefine each.
    #
    # The three fancyhdr slots (L/C/R) each typeset at their natural width and
    # do not push each other apart, so a long revision line silently overprints
    # the page count. Two stacked full-width lines cannot collide: identifiers
    # on the first, the revision and status -- the part that grows -- alone on
    # the second.
    status = rf"Revision {revision} \textperiodcentered\ {escape(effective)}"
    if software:
        status += rf" \textperiodcentered\ Software {escape(software)}"
    footer = (
        r"\fancyhf{}"
        r"\fancyfoot[C]{\footnotesize"
        rf"\makebox[\textwidth][l]{{{document_number}\hfill "
        r"Page \thepage\ of \pageref{LastPage}}\\"
        rf"\footnotesize\makebox[\textwidth][c]{{{status}}}}}"
        r"\renewcommand{\headrulewidth}{0pt}"
        r"\renewcommand{\footrulewidth}{0.4pt}"
    )

    lines = [
        r"% --- spiri-docs document control ---",
        r"\usepackage{lastpage}",
        # Room for the second footer line; without this fancyhdr warns and the
        # body text runs into the footer.
        r"\addtolength{\footskip}{\baselineskip}",
        r"\makeatletter",
        rf"\fancypagestyle{{normal}}{{{footer}}}",
        rf"\fancypagestyle{{plain}}{{{footer}}}",
        r"\makeatother",
    ]

    if history.distribution_statement:
        # Rendered by the template's cover page via the `distribution_statement`
        # substitution; also stamped into the PDF metadata below.
        lines.append(
            rf"\newcommand{{\spiridistribution}}{{{escape(history.distribution_statement)}}}"
        )

    # hyperref is loaded by sphinx.sty after this preamble is inserted, so defer
    # the metadata until the document actually begins.
    subject = f"{history.document_number} Revision {current.revision}"
    if software:
        subject += f" for software {software}"
    lines += [
        r"\AtBeginDocument{%",
        rf"  \hypersetup{{pdfsubject={{{escape(subject)}}},"
        rf"pdfkeywords={{{escape(history.document_number)}}}}}%",
        r"}",
        r"% --- end spiri-docs document control ---",
    ]

    return "\n".join(lines)
