"""Answer questions about a document from outside Sphinx.

CI has to name the files it publishes -- the HTML zip, the PDF, the release
assets -- and those names have to match the one Sphinx bakes into the PDF. That
name is derived from ``revisions.yaml`` by :func:`spiri_docs.latex.target_basename`,
and the only alternative to asking for it here is spelling the rule out a second
time in YAML, where it drifts silently: a workflow that publishes
``SPIRI-OM-001_rev1.1.pdf`` containing a footer reading revision 1.2 is worse
than no artifact at all.

Two commands, because CI wants one thing and a person at a terminal wants another::

    $ uv run python -m spiri_docs name
    SPIRI-OM-001_rev1.2

    $ uv run python -m spiri_docs fields >> "$GITHUB_OUTPUT"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .latex import target_basename
from .revisions import RevisionError, load


def _fields(path: Path) -> dict[str, str]:
    history = load(path)
    current = history.current
    return {
        # The stem every published file is built from.
        "name": target_basename(history),
        "document_number": history.document_number,
        "revision": current.revision,
        # Lower-case so a workflow can test it with `== 'true'`, which is how
        # GitHub Actions compares the strings it turns every output into.
        "draft": "true" if current.draft else "false",
        "date": current.date.isoformat(),
        "effective_date": (
            current.effective_date.isoformat() if current.effective_date else current.date.isoformat()
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m spiri_docs",
        description="Report document identity from revisions.yaml.",
    )
    parser.add_argument(
        "command",
        choices=("name", "fields"),
        help=(
            "'name' prints the filename stem for this revision; "
            "'fields' prints KEY=value lines, for appending to $GITHUB_OUTPUT"
        ),
    )
    parser.add_argument(
        "--revisions",
        type=Path,
        default=Path("revisions.yaml"),
        help="path to revisions.yaml (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    try:
        fields = _fields(args.revisions)
    except RevisionError as exc:
        # The audience for this message is someone reading a CI log, not a
        # Python traceback.
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.command == "name":
        print(fields["name"])
    else:
        for key, value in fields.items():
            print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
