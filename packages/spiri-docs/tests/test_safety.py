"""The safety alert symbol, and the two ways it silently disappears.

Both bugs guarded here shipped a page with space reserved for a symbol that was
never drawn -- no warning, no error, and nothing wrong with the build. On a
hazard panel that is the worst available failure mode, which is why a drawing
gets a test file.
"""

from __future__ import annotations

import xml.dom.minidom
from pathlib import Path

import pytest

from spiri_docs import safety

SYMBOL = Path(safety.__file__).parent / "static" / "safety-alert.svg"


def test_the_symbol_is_well_formed_xml() -> None:
    # Regression: the house comment style uses "--", which XML forbids inside a
    # comment. The SVG became unparseable, and an unparseable mask masks nothing.
    xml.dom.minidom.parse(str(SYMBOL))


def test_the_symbol_ships_with_the_package() -> None:
    assert SYMBOL.is_file()


def test_data_uri_encodes_spaces() -> None:
    # Regression: a literal space terminates the CSS url() token early, so the
    # mask resolves to nothing and the symbol vanishes.
    uri = safety.data_uri('<svg viewBox="0 0 24 24"><path d="M12 1.8 L23.55 21.8 Z"/></svg>')
    assert " " not in uri
    assert "%20" in uri


def test_data_uri_encodes_quotes() -> None:
    # Same failure, different character: the stylesheet wraps this in url("..."),
    # so an unencoded double quote closes the string early.
    assert '"' not in safety.data_uri('<svg xmlns="http://www.w3.org/2000/svg"/>')


@pytest.mark.parametrize("char", ["<", ">", "#"])
def test_data_uri_encodes_the_rest_of_the_hostile_characters(char: str) -> None:
    assert char not in safety.data_uri(f'<svg data-x="{char}"/>')


def test_stylesheet_defines_the_custom_property_the_css_reads() -> None:
    css = safety.stylesheet(SYMBOL)
    assert "--spiri-icon-safety-alert" in css
    assert "data:image/svg+xml" in css

    # The handwritten sheet reads the property; if the two names ever drift the
    # symbol disappears and nothing else changes.
    handwritten = (SYMBOL.parent / "spiri-safety.css").read_text()
    assert "var(--spiri-icon-safety-alert)" in handwritten


def test_stylesheet_drops_the_comment_from_the_uri() -> None:
    # The comment is for whoever edits the SVG, not for every page that loads it.
    assert "Note for editors" not in safety.stylesheet(SYMBOL)


def test_one_palette_feeds_both_formats() -> None:
    # The point of keeping the colours in Python: a manual whose PDF and web
    # build disagree about what colour a hazard is would be worse than either.
    css, tex = safety.stylesheet(SYMBOL), safety.latex_preamble()
    for signal in safety.SIGNALS:
        assert signal.colour in css
        assert signal.colour.lstrip("#").upper() in tex


def test_the_symbol_goes_on_injury_panels_only() -> None:
    tex = safety.latex_preamble()
    for signal in safety.SIGNALS:
        icon = rf"\@namedef{{sphinx{signal.latex_type}TtlIcon}}{{\spiriSafetyAlert"
        # NOTICE is property damage and SAFETY INSTRUCTIONS is guidance; marking
        # either as an injury hazard is the failure an auditor looks for first.
        assert (icon in tex) is signal.alert


def test_custom_types_define_every_flag_the_box_code_reads() -> None:
    # A missing one does not fail here -- it fails in LaTeX as "Extra \fi",
    # pointing at the admonition rather than at the missing definition.
    tex = safety.latex_preamble()
    for signal in safety.SIGNALS:
        if signal.name in safety._BUILTIN:
            continue
        for flag in safety._BOX_FLAGS:
            assert rf"\newif\ifspx@{signal.latex_type}@{flag}" in tex


def test_signal_words_are_written_in_not_taken_from_the_title() -> None:
    # docutils would supply a localised, title-cased "Danger".
    tex = safety.latex_preamble()
    for signal in safety.SIGNALS:
        assert f"{{{signal.word}}}" in tex


def test_a_missing_tikz_is_an_error_not_a_warning() -> None:
    # The whole reason the symbol is drawn rather than imported: a warning would
    # let Read the Docs publish a symbol-less manual, because its fail_on_warning
    # catches Sphinx warnings, not LaTeX ones.
    tex = safety.latex_preamble()
    assert r"\PackageError{spiri-docs}" in tex
    assert r"\PackageWarning" not in tex
