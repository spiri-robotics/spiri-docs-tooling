"""Load and validate ``revisions.yaml``.

A controlled document's revision history is data, not prose. It is the single
source for the cover page, the PDF footer, the PDF filename, and the revision
table -- so it is read once, here, and validated hard. A manual that reaches a
customer with a blank effective date is a worse outcome than a failed build.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class RevisionError(Exception):
    """Raised when ``revisions.yaml`` is missing, malformed, or incomplete.

    The Sphinx layer converts this into a ``ConfigError`` so the build stops.
    """


#: Values people type when they mean "not filled in yet". A regulator-facing
#: manual that ships saying "Approved by: TODO" is exactly the failure the
#: approval check exists to prevent, so a placeholder is treated as absent.
_PLACEHOLDERS = frozenset({"todo", "tbd", "tba", "xxx", "fixme", "?", "n/a", "none"})


@dataclass(frozen=True)
class Revision:
    """One entry in the revision history."""

    revision: str
    date: _dt.date
    summary: str
    author: str | None = None
    approver: str | None = None
    effective_date: _dt.date | None = None
    #: A revision still being written. Drafts skip the approval requirements --
    #: a document cannot be approved before it is finished -- and are marked as
    #: drafts on the cover page and in the PDF footer so a printed copy cannot
    #: be mistaken for an issued one.
    draft: bool = False


@dataclass(frozen=True)
class RevisionHistory:
    """The whole file: document identity plus every revision, oldest first."""

    document_number: str
    revisions: tuple[Revision, ...]
    regulator_facing: bool = False
    distribution_statement: str | None = None

    @property
    def current(self) -> Revision:
        """The revision this build represents -- the last entry in the file."""
        return self.revisions[-1]


def _as_date(value: Any, field: str, where: str) -> _dt.date:
    # PyYAML already turns an unquoted ISO date into a datetime.date. Anything
    # else means the author quoted it or typed something that is not a date, and
    # guessing at the format is how you ship a manual dated 01/02 in the wrong
    # hemisphere's convention.
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    raise RevisionError(
        f"{where}: {field} must be an unquoted ISO date (YYYY-MM-DD), got {value!r}"
    )


def _blank_if_placeholder(value: Any) -> Any:
    """Treat obvious fill-me-in text as if the field were empty."""
    if isinstance(value, str) and value.strip().lower().rstrip(".") in _PLACEHOLDERS:
        return ""
    return value


def _require(data: dict[str, Any], key: str, where: str) -> Any:
    if key not in data or data[key] in (None, ""):
        raise RevisionError(f"{where}: missing required field {key!r}")
    return data[key]


def parse(data: Any, *, source: str = "revisions.yaml") -> RevisionHistory:
    """Turn parsed YAML into a validated :class:`RevisionHistory`."""
    if not isinstance(data, dict):
        raise RevisionError(f"{source}: expected a mapping at the top level")

    document_number = str(_require(data, "document_number", source))
    regulator_facing = bool(data.get("regulator_facing", False))

    raw_revisions = data.get("revisions")
    if not isinstance(raw_revisions, list) or not raw_revisions:
        raise RevisionError(f"{source}: 'revisions' must be a non-empty list")

    revisions: list[Revision] = []
    for index, raw in enumerate(raw_revisions):
        where = f"{source}: revisions[{index}]"
        if not isinstance(raw, dict):
            raise RevisionError(f"{where}: expected a mapping")

        revision = str(_require(raw, "revision", where))
        where = f"{source}: revision {revision}"

        draft = bool(raw.get("draft", False))
        effective_raw = _blank_if_placeholder(raw.get("effective_date"))
        approver = _blank_if_placeholder(raw.get("approver"))

        # A regulator-facing document has to say when it took effect and who
        # signed it off -- once it is issued. A draft has neither yet, by
        # definition, so the requirement lands the moment `draft` is removed.
        if regulator_facing and not draft:
            for field, value in (("effective_date", effective_raw), ("approver", approver)):
                if value in (None, ""):
                    raise RevisionError(
                        f"{where}: regulator_facing documents require {field!r} before "
                        f"a revision can be issued. Set it, or mark this revision "
                        f"`draft: true` while it is still being written."
                    )

        revisions.append(
            Revision(
                revision=revision,
                date=_as_date(_require(raw, "date", where), "date", where),
                summary=str(_require(raw, "summary", where)),
                author=str(raw["author"]) if _blank_if_placeholder(raw.get("author")) else None,
                approver=str(approver) if approver else None,
                effective_date=(
                    _as_date(effective_raw, "effective_date", where) if effective_raw else None
                ),
                draft=draft,
            )
        )

    # Out-of-order history is almost always an editing mistake, and it silently
    # picks the wrong "current" revision, so refuse it rather than guess.
    for previous, current in zip(revisions, revisions[1:]):
        if current.date < previous.date:
            raise RevisionError(
                f"{source}: revision {current.revision} is dated {current.date}, "
                f"before revision {previous.revision} ({previous.date}); "
                "revisions must be listed oldest first"
            )

    return RevisionHistory(
        document_number=document_number,
        revisions=tuple(revisions),
        regulator_facing=regulator_facing,
        distribution_statement=(
            str(data["distribution_statement"]) if data.get("distribution_statement") else None
        ),
    )


def load(path: Path) -> RevisionHistory:
    """Read and validate ``revisions.yaml`` at *path*."""
    if not path.is_file():
        raise RevisionError(
            f"no revision file at {path}. Every Spiri controlled document needs one; "
            "see https://github.com/spiri-robotics/spiri-docs-tooling"
        )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RevisionError(f"{path}: could not parse YAML: {exc}") from exc
    return parse(data, source=path.name)
