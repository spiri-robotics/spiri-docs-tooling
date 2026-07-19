"""Sphinx extension for Spiri controlled documents.

Add it to a manual's ``conf.py``::

    extensions = ["myst_parser", "spiri_docs"]

Everything else follows from ``revisions.yaml`` sitting next to ``docs/``. The
extension reads it on every build and, from that one file:

* validates it, failing the build rather than shipping a manual with a blank
  effective date or an unnamed approver;
* sets ``version`` and ``release`` to the current revision;
* exposes ``{{ document_number }}``, ``{{ revision }}`` and friends as MyST
  substitutions, so the cover page is written in Markdown by whoever owns the
  prose rather than in Python;
* stamps the document number, revision and page-of-total into the PDF footer;
* names the PDF after the document and revision.

The deliberate split with ``spiri-doc-template``: the template owns what is
decided once per project (theme, CSS, structure), this owns what has to be true
on every build. A template cannot enforce anything after generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.errors import ConfigError

from . import latex
from .directives import RevisionHistoryDirective
from .revisions import Revision, RevisionError, RevisionHistory, load, parse

__version__ = "0.1.0"

__all__ = [
    "Revision",
    "RevisionError",
    "RevisionHistory",
    "load",
    "parse",
    "setup",
]


#: Shown where a value is legitimately absent -- an unapproved draft, say. Every
#: substitution is always defined, because a cover page referencing {{ approver }}
#: must render whether or not there is one yet; an undefined name is a build
#: error, and "the document has no approver" is not an error, it is a fact.
EMPTY = "—"


def _substitutions(history: RevisionHistory) -> dict[str, str]:
    """The values a writer can drop into Markdown with ``{{ ... }}``."""
    current = history.current
    values = {
        "document_number": history.document_number,
        "revision": current.revision,
        # Written into the cover page unconditionally, so a draft is visibly a
        # draft without the author having to remember to say so.
        "document_status": "DRAFT -- not for operational use" if current.draft else "Issued",
        "revision_date": current.date.isoformat(),
        "effective_date": (
            current.effective_date.isoformat() if current.effective_date else current.date.isoformat()
        ),
        "revision_summary": current.summary,
        "author": current.author or EMPTY,
        "approver": current.approver or EMPTY,
        # Not a person or a date: absent means "print nothing", not "print a dash".
        "distribution_statement": history.distribution_statement or "",
    }
    return values


def _on_config_inited(app: Sphinx, config: Config) -> None:
    revisions_path = (Path(app.confdir) / config.spiri_docs_revisions).resolve()
    try:
        history = load(revisions_path)
    except RevisionError as exc:
        # ConfigError is what Sphinx renders as a clean error instead of a
        # traceback -- the audience here includes people who do not write Python.
        raise ConfigError(str(exc)) from exc

    app.spiri_docs_history = history  # type: ignore[attr-defined]

    # The revision *is* the version. Nothing else should be setting these.
    config.version = history.current.revision
    config.release = history.current.revision

    # Writer-facing values. User-defined substitutions win, so a project can
    # override any of these locally without patching the extension.
    existing = dict(getattr(config, "myst_substitutions", {}) or {})
    config.myst_substitutions = {**_substitutions(history), **existing}

    # Substitutions are inert unless MyST's `substitution` extension is on, and
    # the failure is silent: the cover page renders a literal "{{ revision }}"
    # instead of a revision number. Since this extension is what supplies them,
    # it turns the parser feature on rather than relying on every conf.py.
    if hasattr(config, "myst_enable_extensions"):
        enabled = set(config.myst_enable_extensions or ())
        config.myst_enable_extensions = sorted(enabled | {"substitution"})

    # Name the PDF after the document number and revision.
    #
    # `latex_documents` cannot be tested for emptiness to decide whether the
    # project set it: Sphinx's default is a lazy factory, so merely reading the
    # value materialises a default entry (`spirimuoperationalmanual.tex`) and it
    # never looks unset. Ask the raw conf.py namespace instead, and otherwise
    # rewrite just the target filename -- leaving title, author and theme as
    # whatever Sphinx worked out.
    if "latex_documents" not in getattr(config, "_raw_config", {}):
        target = f"{latex.target_basename(history)}.tex"
        config.latex_documents = [
            (entry[0], target, *entry[2:]) for entry in config.latex_documents
        ]

    elements = dict(config.latex_elements or {})
    elements["preamble"] = "\n".join(
        part for part in (elements.get("preamble", ""), latex.preamble(history)) if part
    )
    config.latex_elements = elements


def _on_builder_inited(app: Sphinx) -> None:
    # Directives reach the history through the environment; set it fresh each
    # build so a pickled environment from an older run cannot go stale.
    app.env.spiri_docs_history = app.spiri_docs_history  # type: ignore[attr-defined]


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_config_value("spiri_docs_revisions", "../revisions.yaml", "env", str)
    app.connect("config-inited", _on_config_inited)
    app.connect("builder-inited", _on_builder_inited)
    app.add_directive("revision-history", RevisionHistoryDirective)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
