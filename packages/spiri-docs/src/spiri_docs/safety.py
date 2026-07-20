"""ANSI Z535 signal word panels, for both output formats.

The palette lives here rather than in the stylesheet because it is now needed
twice -- once as CSS custom properties, once as LaTeX colour definitions. Two
hand-maintained copies of the same five colours would disagree eventually, and
the disagreement would be a manual whose PDF and web build show different
colours for the same hazard. Same reasoning as ``logo.py``: derive, don't copy.

-- The safety alert symbol -------------------------------------------------

The symbol is tinted per panel -- white on DANGER, black on WARNING -- so in
HTML it has to be a CSS mask rather than an ``<img>``: a mask takes its colour
from the element, an image carries its own.

``mask-image: url(safety-alert.svg)`` does not work in Firefox. With no fragment
identifier it is read as a reference to an SVG ``<mask>`` element, finds none,
and masks the element away entirely -- so the symbol does not merely fail to
tint, it vanishes, leaving a panel with a gap where the symbol should be. The
reliable form is a data URI, which is what Furo does for its own icons.

Which leaves the question of where the data URI comes from. Pasting one into the
stylesheet would make ``safety-alert.svg`` decorative: someone replacing it with
licensed artwork would rebuild, see no change, and have no way to tell why. So
it is derived from that file on every build.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from docutils.nodes import Element
from sphinx.writers.latex import LaTeXTranslator

#: The generated stylesheet's name in ``_static``. Separate from
#: ``spiri-safety.css`` because that one is handwritten and this one is not;
#: keeping them apart means nobody edits a generated file by mistake.
FILENAME = "spiri-safety-icon.css"

#: ANSI Z535.1 safety colours, sampled from the standard's colour chart. Close
#: to but not identical with the published sRGB for each Pantone reference,
#: which is the right trade for a manual. If these are ever reused on a product
#: label, check them against a real chip first: Z535.4 polices label colour far
#: more tightly than Z535.6 polices collateral.
PALETTE = {
    "red": "#b11a2a",  # 186 C
    "orange": "#d16e1c",  # 151 C
    "yellow": "#d5bc09",  # 109 C
    "green": "#006952",  # 335 C
    "blue": "#00619d",  # 285 C
    "purple": "#5f2268",  # 259 C -- radiation, no signal word attached
}

_WHITE = "#ffffff"
_BLACK = "#000000"


@dataclass(frozen=True)
class Signal:
    """One Z535.6 signal word panel."""

    #: Class on the HTML admonition, and the directive name for the two panels
    #: this extension supplies.
    name: str
    #: The word itself. Fixed by the standard, and uppercase in both formats.
    word: str
    #: Key into PALETTE for the panel fill.
    fill: str
    #: Type colour on that fill.
    ink: str
    #: Whether the panel carries the safety alert symbol. True exactly when the
    #: panel means "a person can be hurt" -- which is what the symbol says, and
    #: why NOTICE and SAFETY INSTRUCTIONS do not get one.
    alert: bool
    #: LaTeX cannot take a hyphen in an environment name built by \\csname in
    #: every context, so the two custom types get a squashed spelling.
    latex_type: str

    @property
    def colour(self) -> str:
        return PALETTE[self.fill]


#: The five panels, in descending severity. DANGER, WARNING and CAUTION are
#: docutils admonitions that already exist and are restyled; NOTICE and SAFETY
#: INSTRUCTIONS are supplied by this extension.
SIGNALS = (
    Signal("danger", "DANGER", "red", _WHITE, alert=True, latex_type="danger"),
    Signal("warning", "WARNING", "orange", _BLACK, alert=True, latex_type="warning"),
    Signal("caution", "CAUTION", "yellow", _BLACK, alert=True, latex_type="caution"),
    Signal("notice", "NOTICE", "blue", _WHITE, alert=False, latex_type="notice"),
    Signal(
        "safety-instructions",
        "SAFETY INSTRUCTIONS",
        "green",
        _WHITE,
        alert=False,
        latex_type="safetyinstructions",
    ),
)

#: The three that docutils already provides, and that are therefore restyled
#: rather than defined. The other two need environments built from scratch.
_BUILTIN = frozenset({"danger", "warning", "caution"})

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_WHITESPACE = re.compile(r"\s+")


def data_uri(svg: str) -> str:
    """Return *svg* as a ``data:`` URI usable inside a CSS ``url()``.

    Everything is percent-encoded except the handful of characters that are safe
    unquoted. The space is the one that matters: left literal it terminates the
    ``url()`` token early and the symbol silently disappears -- which is the same
    end state as every other failure here, and the reason this is a function with
    a test rather than a string written by hand.
    """
    stripped = _WHITESPACE.sub(" ", _COMMENT.sub("", svg)).strip()
    return "data:image/svg+xml;charset=utf-8," + quote(stripped, safe="")


def stylesheet(symbol: Path) -> str:
    """The generated CSS: the palette, and the symbol as a custom property."""
    lines = [
        "/* Generated by spiri-docs. Do not edit: every build overwrites it.",
        " * The colours come from safety.py, the symbol from safety-alert.svg. */",
        "body {",
    ]
    for key, value in PALETTE.items():
        lines.append(f"  --spiri-ansi-{key}: {value};")
    lines.append("")
    for signal in SIGNALS:
        lines.append(f"  --spiri-signal-{signal.name}: var(--spiri-ansi-{signal.fill});")
    lines.append("")
    for signal in SIGNALS:
        lines.append(f"  --spiri-signal-on-{signal.name}: {signal.ink};")
    lines.append("")
    lines.append(f'  --spiri-icon-safety-alert: url("{data_uri(symbol.read_text())}");')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _hex(colour: str) -> str:
    """``#b11a2a`` as LaTeX's ``HTML`` colour model wants it."""
    return colour.lstrip("#").upper()


#: Every per-type parameter ``\\spx@boxes@fcolorbox@setup`` reads. A custom panel
#: type has to have all of them or the box machinery fails on an undefined
#: control sequence, so the two new types borrow WARNING's geometry wholesale
#: and override only the colours. Copying the list rather than the values keeps
#: this working if Sphinx changes its defaults.
_BOX_DIMENSIONS = (
    "border@top",
    "border@right",
    "border@bottom",
    "border@left",
    "padding@top",
    "padding@right",
    "padding@bottom",
    "padding@left",
    "radius@topleft",
    "radius@topright",
    "radius@bottomright",
    "radius@bottomleft",
    "shadow@xoffset",
    "shadow@yoffset",
)

#: The conditionals Sphinx's box code reads, across both ``sphinxheavybox`` and
#: ``\\spx@boxes@fcolorbox@setup``. These cannot be \\let from the template type:
#: they are consumed as ``\\csname ifspx@<type>@border@open\\endcsname ... \\fi``,
#: and an undefined name expands to \\relax, which leaves the \\fi unmatched. The
#: build then dies as "Extra \\fi" pointing at the admonition rather than at the
#: missing definition, so a forgotten flag here is expensive to diagnose --
#: which is why this list was read off the .sty files rather than guessed.
_BOX_FLAGS = (
    "border@open",
    "withshadow",
    "insetshadow",
    "withshadowcolor",
    "withtextcolor",
)


def _title_macro(signal: Signal, define: str) -> str:
    """The ``\\sphinxstyle<type>title`` macro for *signal*.

    The signal word is written in rather than taken from the docutils title,
    which is localised and title-cased and would give a panel reading "Danger"
    where the standard says "DANGER".

    It is also wrapped in the title colour explicitly. ``\\sphinxdotitlerow``
    colours only the icon, not the heading -- which is invisible with Sphinx's
    pale default fills and very visible on a saturated one, where it leaves
    black type on safety red.

    The size change wraps the whole title row rather than just the word, so the
    safety alert symbol grows with it: the symbol is drawn in ``em`` and would
    otherwise stay at body size beside a heading twice its height. A signal word
    is meant to be the dominant element of the panel, not a bold caption.
    """
    kind = signal.latex_type
    return (
        rf"\{define}\sphinxstyle{kind}title[1]{{{{\large"
        rf"\sphinxdotitlerow{{{kind}}}"
        rf"{{\textcolor{{sphinx{kind}TtlFgColor}}{{{signal.word}}}}}}}}}"
    )


def _custom_type(signal: Signal, template: str = "warning") -> list[str]:
    """LaTeX defining a panel type Sphinx does not ship."""
    kind = signal.latex_type
    lines = [f"% {signal.word}: geometry cloned from `{template}`, colours our own."]
    lines += [
        rf"\expandafter\let\csname spx@{kind}@{param}\expandafter\endcsname"
        rf"\csname spx@{template}@{param}\endcsname"
        for param in _BOX_DIMENSIONS
    ]
    lines += [rf"\newif\ifspx@{kind}@{flag}" for flag in _BOX_FLAGS]
    lines += [
        rf"\definecolor{{sphinx{kind}BorderColor}}{{HTML}}{{{_hex(signal.colour)}}}",
        rf"\definecolor{{sphinx{kind}BgColor}}{{HTML}}{{FFFFFF}}",
        rf"\definecolor{{sphinx{kind}TtlBgColor}}{{HTML}}{{{_hex(signal.colour)}}}",
        rf"\definecolor{{sphinx{kind}TtlFgColor}}{{HTML}}{{{_hex(signal.ink)}}}",
        rf"\definecolor{{sphinx{kind}ShadowColor}}{{HTML}}{{000000}}",
        # Sphinx drops the space after the icon when the icon box is empty, so
        # an empty definition is how a panel says "no symbol" rather than
        # "symbol missing".
        rf"\newcommand\sphinx{kind}TtlIcon{{}}",
        # Read by the sphinxadmonition wrapper. An undefined \csname expands to
        # \relax and would survive, but only by luck; define it.
        rf"\newcommand\spx@{kind}@TeXextras{{}}",
        _title_macro(signal, "newcommand"),
        rf"\newenvironment{{sphinx{kind}}}[1]",
        rf"  {{\def\spx@noticetype{{{kind}}}\begin{{sphinxheavybox}}\sphinxstyle{kind}title{{#1}}}}",
        r"  {\end{sphinxheavybox}}",
    ]
    return lines


def _alert_symbol() -> list[str]:
    """The safety alert symbol for the PDF, drawn rather than imported.

    pdflatex cannot read SVG, so the shipped ``safety-alert.svg`` is unusable
    here. Converting it would mean an external binary (as ``logo.py`` needs for
    the cover) *and* one converted file per type colour, because the symbol is
    white on DANGER and black on WARNING. Drawing it in TikZ costs one package
    and recolours for free, so the geometry is transcribed from the SVG instead:
    same equilateral triangle, same knocked-out exclamation, y flipped because
    TikZ counts upwards and SVG counts down.

    A missing TikZ is a hard error rather than a warning. The failure it guards
    against is a PDF that builds cleanly and ships without a mandated symbol,
    which no reader can notice is absent -- and a LaTeX warning would not stop
    it, because Read the Docs' ``fail_on_warning`` covers Sphinx warnings only.
    Same stance the template already takes on the cover logo, where a missing
    converter fails the release rather than issuing an unbranded document.
    """
    lines = [
        r"% The safety alert symbol. Geometry transcribed from safety-alert.svg,",
        r"% with y flipped: TikZ counts upwards, SVG counts down.",
        r"%",
        r"% The test goes through a boolean rather than defining the command",
        r"% inside \IfFileExists: LaTeX \def's that argument internally, so a #1",
        r"% in the branch dies as `Illegal parameter number in \reserved@a`.",
        r"\newif\ifspiri@tikz",
        r"\IfFileExists{tikz.sty}{\spiri@tikztrue}{\spiri@tikzfalse}",
        r"\ifspiri@tikz",
        r"  \usepackage{tikz}",
        r"  % The triangle's base sits at y=0 and the picture's baseline at 0,",
        r"  % so the symbol stands on the text baseline exactly as the capitals",
        r"  % beside it do. Offsetting the baseline instead leaves it floating.",
        r"  \newcommand\spiriSafetyAlert[1]{%",
        r"    \begin{tikzpicture}[x=0.046em,y=0.046em,baseline=0pt]",
        r"      \fill[#1,even odd rule]",
        r"        (12,20.0) -- (23.55,0) -- (0.45,0) -- cycle",
        r"        (10.7,6.2) rectangle (13.3,13.8)",
        r"        (12,3.2) circle (1.45);",
        r"    \end{tikzpicture}%",
        r"  }",
        r"\else",
        r"  \newcommand\spiriSafetyAlert[1]{}",
        r"  \PackageError{spiri-docs}{%",
        r"    TikZ is missing, so the ANSI Z535 safety alert symbol cannot be"
        r" drawn%",
        r"  }{%",
        r"    Install texlive-pictures. Continuing would produce a manual whose"
        r" DANGER,\MessageBreak WARNING and CAUTION panels carry no safety alert"
        r" symbol, which is\MessageBreak not something a reader could notice was"
        r" missing.%",
        r"  }",
        r"\fi",
    ]
    # Sphinx defines these already when an icon package is in use; \@namedef
    # overwrites either way, so this does not depend on which happened.
    for signal in SIGNALS:
        if not signal.alert:
            continue
        kind = signal.latex_type
        lines.append(
            rf"\@namedef{{sphinx{kind}TtlIcon}}{{\spiriSafetyAlert{{sphinx{kind}TtlFgColor}}}}"
        )
    return lines


def latex_preamble() -> str:
    """The LaTeX half of the signal word panels.

    Inserted after ``sphinx.sty``, so the box machinery it builds on is already
    defined, and after any ``sphinxsetup`` the project set for itself -- which is
    deliberate, and the same ordering the CSS uses. A project's house style is
    its own business right up until it would repaint a hazard panel.
    """
    lines = [
        r"% --- spiri-docs ANSI Z535 safety panels ---",
        r"%",
        r"% Sphinx draws admonition icons from fontawesome, and picks a radiation",
        r"% symbol for DANGER and a lightning bolt for CAUTION. Neither is the",
        r"% safety alert symbol, and the font is a fragile dependency besides.",
        r"% Turn the icons off rather than ship the wrong ones.",
        r"\sphinxsetup{iconpackage=none}",
        r"",
    ]

    # The three docutils already has: colours through the documented keys.
    for signal in SIGNALS:
        if signal.name not in _BUILTIN:
            continue
        fill, ink = _hex(signal.colour), _hex(signal.ink)
        lines += [
            rf"\sphinxsetup{{%",
            rf"  div.{signal.name}_border-TeXcolor={{HTML}}{{{fill}}},",
            rf"  div.{signal.name}_background-TeXcolor={{HTML}}{{FFFFFF}},",
            rf"  div.{signal.name}_title-background-TeXcolor={{HTML}}{{{fill}}},",
            rf"  div.{signal.name}_title-foreground-TeXcolor={{HTML}}{{{ink}}},",
            rf"}}",
        ]

    lines.append("")
    lines.append(r"\makeatletter")

    for signal in SIGNALS:
        if signal.name not in _BUILTIN:
            continue
        lines.append(_title_macro(signal, "renewcommand"))

    lines.append("")
    for signal in SIGNALS:
        if signal.name in _BUILTIN:
            continue
        lines += _custom_type(signal)
        lines.append("")

    lines += _alert_symbol()

    lines += [r"\makeatother", r"% --- end spiri-docs ANSI Z535 safety panels ---"]
    return "\n".join(lines)


#: Sphinx's own handler, captured before we replace it. Kept so the fallback
#: path stays whatever Sphinx does rather than a copy of it that can drift.
_SPHINX_VISIT_ADMONITION = LaTeXTranslator.visit_admonition
_SPHINX_DEPART_ADMONITION = LaTeXTranslator.depart_admonition


def latex_visit_admonition(translator: LaTeXTranslator, node: Element) -> None:
    """Route NOTICE and SAFETY INSTRUCTIONS to their own LaTeX environments.

    Sphinx writes ``\\begin{sphinxadmonition}{note}`` for every generic
    admonition, with the class dropped -- so without this the two custom panels
    come out of a PDF looking like each other and like a plain note, which is
    exactly the distinction the standard exists to draw. The HTML side needs no
    equivalent because CSS can see the class.
    """
    classes = set(node.get("classes", ()))
    for signal in SIGNALS:
        if signal.name in _BUILTIN or signal.name not in classes:
            continue
        translator.body.append("\n" + rf"\begin{{sphinxadmonition}}{{{signal.latex_type}}}")
        translator.no_latex_floats += 1
        return
    _SPHINX_VISIT_ADMONITION(translator, node)


def latex_depart_admonition(translator: LaTeXTranslator, node: Element) -> None:
    _SPHINX_DEPART_ADMONITION(translator, node)
