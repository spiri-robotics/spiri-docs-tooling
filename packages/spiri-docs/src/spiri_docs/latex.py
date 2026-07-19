"""The LaTeX side of document control.

This is the code that most justifies the extension existing. Putting a document
number and revision in a PDF footer means fancyhdr overrides, ``lastpage``, and
``\\AtBeginDocument`` ordering -- fiddly TeX that is got right once and then
never thought about again. Copied into every manual's ``conf.py`` it would
drift, and the symptom of drift is a shipped PDF with a wrong footer.
"""

from __future__ import annotations

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


def escape(text: str) -> str:
    """Escape *text* for use in LaTeX body copy."""
    return "".join(_LATEX_SPECIAL.get(char, char) for char in text)


def safe_filename(text: str) -> str:
    """Reduce *text* to something safe as a filename stem for latexmk."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-.")
    return cleaned or "manual"


def target_basename(history: RevisionHistory) -> str:
    """The PDF filename stem: document number and revision, no spaces.

    A controlled document should be identifiable from its filename alone, after
    someone has emailed it around and lost the page it came from -- which is
    also why a draft says so in the filename.
    """
    suffix = "-DRAFT" if history.current.draft else ""
    return safe_filename(f"{history.document_number}_rev{history.current.revision}{suffix}")


def preamble(history: RevisionHistory) -> str:
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
    footer = (
        r"\fancyhf{}"
        rf"\fancyfoot[L]{{\footnotesize {document_number}}}"
        r"\fancyfoot[C]{\footnotesize Page \thepage\ of \pageref{LastPage}}"
        rf"\fancyfoot[R]{{\footnotesize Revision {revision} \textperiodcentered\ {escape(effective)}}}"
        r"\renewcommand{\headrulewidth}{0pt}"
        r"\renewcommand{\footrulewidth}{0.4pt}"
    )

    lines = [
        r"% --- spiri-docs document control ---",
        r"\usepackage{lastpage}",
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
    lines += [
        r"\AtBeginDocument{%",
        rf"  \hypersetup{{pdfsubject={{{escape(subject)}}},"
        rf"pdfkeywords={{{escape(history.document_number)}}}}}%",
        r"}",
        r"% --- end spiri-docs document control ---",
    ]

    return "\n".join(lines)
