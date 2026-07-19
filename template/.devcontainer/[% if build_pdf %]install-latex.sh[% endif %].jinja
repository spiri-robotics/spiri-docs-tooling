#!/usr/bin/env bash
#
# Installs the LaTeX toolchain, the first time someone asks for a PDF.
#
# This is not part of container setup on purpose. TeX Live is around a gigabyte,
# and most people working on this manual only ever write prose -- making every
# contributor wait for it on first open, to produce an artifact CI builds for
# them on a tag, is a bad trade. So the "Build a PDF" task calls this instead,
# and it does nothing at all once the toolchain is there.
#
# A container rebuild starts from the image again, so the first PDF build after
# a rebuild pays this cost once more.

set -euo pipefail

if command -v latexmk >/dev/null 2>&1; then
  exit 0
fi

cat <<'NOTE'

  Building a PDF needs a LaTeX toolchain, which is not in this container yet.

  Installing it now. This takes a few minutes and about a gigabyte, and only
  happens once -- the next PDF build starts immediately.

NOTE

# Kept in step with .github/workflows/release.yml so a PDF built here matches the
# one CI attaches to a release: texlive-latex-extra carries the packages Sphinx's
# LaTeX output expects (framed, titlesec, wrapfig, capt-of), latexmk drives the
# build, and tex-gyre supplies the fonts.
if ! sudo apt-get update -qq; then
  cat >&2 <<'HELP'

  Could not reach the package servers, so LaTeX was not installed.

  This is a network problem rather than something you have done wrong. The
  manual itself still builds -- only the PDF is unavailable. Tagging a
  revision builds the PDF in CI regardless.

HELP
  exit 1
fi

sudo apt-get install -y --no-install-recommends \
  latexmk texlive-latex-recommended texlive-latex-extra \
  texlive-fonts-recommended tex-gyre

echo
echo "  LaTeX installed. Building the PDF..."
echo
