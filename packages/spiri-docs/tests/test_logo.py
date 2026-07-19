"""Checks on turning the SVG logo into something LaTeX can include."""

from __future__ import annotations

import re
from pathlib import Path

from spiri_docs import logo

SVG = (
    '<svg height="3.1in" viewBox="0 0 222.32 222.84" width="3.09in" '
    'xmlns="http://www.w3.org/2000/svg"><path d="m0 0"/></svg>'
)


def _root(svg: str) -> str:
    match = re.search(r"<svg\b[^>]*>", svg)
    assert match is not None
    return match.group(0)


def test_resize_sets_the_document_size_in_inches() -> None:
    root = _root(logo.resize(SVG, 1.5))
    assert 'width="1.5in"' in root

    # Height follows the viewBox aspect rather than the original attribute.
    height = re.search(r'height="([\d.]+)in"', root)
    assert height is not None
    assert float(height.group(1)) == round(1.5 * 222.84 / 222.32, 5)


def test_resize_leaves_the_viewbox_alone() -> None:
    # Regression: scaling the dots and the logotype independently is a brand
    # violation, and rewriting the viewBox is how that would happen by accident.
    assert 'viewBox="0 0 222.32 222.84"' in logo.resize(SVG, 1.5)


def test_resize_does_not_duplicate_existing_dimensions() -> None:
    root = _root(logo.resize(SVG, 1.5))
    assert root.count("width=") == 1
    assert root.count("height=") == 1


def test_resize_declines_to_guess_without_a_viewbox() -> None:
    # No viewBox means no aspect ratio, and forcing a width would stretch the
    # mark. Better to emit it at its natural size than distorted.
    svg = '<svg width="10" height="20" xmlns="http://www.w3.org/2000/svg"/>'
    assert logo.resize(svg, 1.5) == svg


def test_a_missing_logo_warns_rather_than_raising(tmp_path: Path) -> None:
    assert logo.to_pdf(tmp_path / "absent.svg", tmp_path / "out.pdf") is None


def test_no_converter_installed_is_survivable(tmp_path: Path, monkeypatch) -> None:
    # The document must still build for a writer whose machine has no SVG
    # renderer; they lose the cover logo, not their afternoon.
    monkeypatch.setattr(logo, "CONVERTERS", ())
    source = tmp_path / "logo.svg"
    source.write_text(SVG)
    assert logo.to_pdf(source, tmp_path / "out.pdf") is None
