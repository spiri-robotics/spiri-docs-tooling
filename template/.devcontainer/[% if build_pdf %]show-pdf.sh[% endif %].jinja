#!/usr/bin/env bash
# Find the PDF that was just built, say where it is, and open it.
#
# This exists because the writer cannot guess the filename. spiri_docs names the
# file after the document number and the current revision -- SPIRI-OM-001_rev2.1
# -- so it is correct, unique, and different after every revision. Printing the
# directory and leaving someone to work it out is how you get "I built it, where
# is it?", which is a fair question to ask of a button labelled "Build a PDF".
#
# Called by the Makefile and by the VS Code task, so both say the same thing.
set -euo pipefail

latex_dir="docs/_build/latex"

# Newest, not first: an old PDF from a previous revision number can still be
# sitting in the directory, and opening last month's document would be worse
# than opening none.
pdf=$(ls -t "$latex_dir"/*.pdf 2>/dev/null | head -1 || true)

if [ -z "$pdf" ]; then
  echo
  echo "No PDF was produced. The LaTeX output above will say why -- look for"
  echo "the first line containing '!', which is where pdflatex gave up."
  exit 1
fi

echo
echo "Your PDF:  $pdf"

# The desktop handler first, and `code` only as the container fallback.
#
# That order matters: VS Code cannot display a PDF on its own. Handed one it
# shows a "binary file" placeholder unless tomoki1207.pdf is installed, so
# calling `code` on a machine with a real PDF viewer would take a working
# double-click and make it worse. Inside the devcontainer there is no desktop
# handler and no viewer to take it to, and devcontainer.json installs that
# extension for exactly this moment -- so there, `code` is the best available.
#
# If nothing matches -- a CI runner, a bare ssh session -- the path printed
# above is the whole answer, which is why none of this is an error.
if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$pdf" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open "$pdf" 2>/dev/null || true
elif command -v code >/dev/null 2>&1; then
  code "$pdf" 2>/dev/null || true
fi
