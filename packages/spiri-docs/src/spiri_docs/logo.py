"""Making the HTML logo usable by the LaTeX builder.

pdflatex cannot read SVG and the brand assets are SVG only, so the PDF needs a
raster or vector-PDF copy of the mark. Committing one alongside the SVG would
mean two files that say the same thing and can disagree -- and they would, the
first time someone updates the mark and forgets the derived copy. So the PDF
version is produced during the build from the same file the HTML uses.

That is the point of doing this here rather than in each manual's conf.py: a
document is rebranded by replacing the SVGs in ``docs/_static`` and nothing
else. The converter is a container dependency, not a Python one, because every
usable SVG renderer is a binding to a C library; see ``.devcontainer/setup.sh``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from sphinx.util import logging

logger = logging.getLogger(__name__)

#: Width of the logo on the PDF title page, in inches. Comfortably above the
#: 0.5in floor the Spiri guidelines set, and small enough to leave the title
#: room on a letter page.
DEFAULT_WIDTH = 1.5

_VIEWBOX = re.compile(r'viewBox\s*=\s*"\s*([-\d.eE]+)\s+([-\d.eE]+)\s+([-\d.eE]+)\s+([-\d.eE]+)\s*"')
_SVG_TAG = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)
_DIMENSION = re.compile(r'\s(?:width|height)\s*=\s*"[^"]*"', re.IGNORECASE)


def resize(svg: str, width: float) -> str:
    """Return *svg* with its rendered size set to *width* inches.

    The size has to be baked into the file rather than passed to the converter:
    ``--export-width`` is a raster option in Inkscape and is quietly ignored when
    the output is PDF, so asking each converter nicely gives a logo whose size
    depends on which one happened to be installed. The document's own width and
    height are the one thing every renderer agrees on.

    Only the root element's ``width`` and ``height`` change. ``viewBox`` is left
    exactly as it is, so nothing inside moves relative to anything else -- the
    guidelines forbid scaling the dots and the logotype independently, and this
    is the whole artwork scaled uniformly, which they allow.
    """
    box = _VIEWBOX.search(svg)
    if box is None:
        # Without a viewBox there is no aspect ratio to preserve, and forcing a
        # width would stretch the mark. Leave it alone.
        return svg

    _, _, box_width, box_height = (float(value) for value in box.groups())
    if box_width <= 0 or box_height <= 0:
        return svg
    height = width * box_height / box_width

    def rewrite(match: re.Match[str]) -> str:
        tag = _DIMENSION.sub("", match.group(0))
        return f'{tag[:-1].rstrip()} width="{width:g}in" height="{height:g}in">'

    return _SVG_TAG.sub(rewrite, svg, count=1)


def _rsvg(source: Path, destination: Path) -> list[str]:
    return ["rsvg-convert", "--format=pdf", f"--output={destination}", str(source)]


def _inkscape(source: Path, destination: Path) -> list[str]:
    return [
        "inkscape",
        str(source),
        "--export-type=pdf",
        f"--export-filename={destination}",
    ]


#: Tried in order. rsvg-convert is what the container installs -- it is small and
#: does one job. Inkscape is accepted as well because anyone who works on the
#: artwork already has it, and it is what the design-assets repo builds with.
CONVERTERS = (("rsvg-convert", _rsvg), ("inkscape", _inkscape))


def to_pdf(source: Path, destination: Path, width: float = DEFAULT_WIDTH) -> Path | None:
    """Render *source* SVG to a PDF at *destination*, or return ``None``.

    Returning ``None`` rather than raising is deliberate. A missing converter
    should cost the cover its logo, not stop a writer from building their
    document -- but it warns, so it is fatal under ``-W`` where a released PDF
    is being built and a silently unbranded cover would be the worse outcome.
    """
    if not source.is_file():
        logger.warning("spiri-docs: logo %s does not exist; the PDF will have none", source)
        return None

    for name, argv in CONVERTERS:
        if shutil.which(name) is None:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        # The sized copy is a temporary: the asset in _static is the one someone
        # replaces to rebrand the document, and it should stay as they left it.
        with tempfile.TemporaryDirectory() as scratch:
            sized = Path(scratch) / source.name
            sized.write_text(resize(source.read_text(encoding="utf-8"), width), encoding="utf-8")
            try:
                subprocess.run(argv(sized, destination), check=True, capture_output=True)
            except subprocess.CalledProcessError as exc:
                logger.warning(
                    "spiri-docs: %s could not convert %s; the PDF will have no logo.\n%s",
                    name,
                    source.name,
                    exc.stderr.decode(errors="replace").strip(),
                )
                return None
        return destination

    logger.warning(
        "spiri-docs: no SVG converter found, so the PDF will have no logo. "
        "Install one of: %s. In the devcontainer this means rebuilding it.",
        ", ".join(name for name, _ in CONVERTERS),
    )
    return None
