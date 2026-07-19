#!/usr/bin/env bash
#
# Makes sure the style rules named in .vale.ini are on disk, before anything
# tries to check prose against them.
#
# The rules are not in this repository. .vale.ini names a package and `vale
# sync` downloads it into styles/ -- which means there is a moment, in every
# fresh clone and after every container rebuild, when the style checker is fully
# configured and has nothing to check against. Run in that moment, Vale stops
# with:
#
#   E100 [loadStyles] Runtime error
#   style 'Microsoft' does not exist on StylesPath
#
# That reads like a broken manual rather than a missing download, and it is the
# first thing a new writer would see. So every entry point that runs Vale --
# container setup, `make lint`, and the "Check writing style" task -- calls this
# first, rather than each of them assuming some earlier step did.
#
# Guarded rather than an unconditional `vale sync`: the download needs the
# network, and someone writing on a plane should not be told the style checker
# is broken when the rules are already sitting on disk.

set -euo pipefail

# styles/config is our own vocabulary and is committed; everything else in
# styles/ was downloaded. So anything beyond config means the sync has happened.
if [ -n "$(ls -A styles 2>/dev/null | grep -v '^config$' || true)" ]; then
  exit 0
fi

echo "Fetching the style rules named in .vale.ini (once)..."

if ! vale sync; then
  cat >&2 <<'HELP'

  Could not download the style rules, so the style checker is unavailable.

  This is a network problem rather than something you have done wrong. Writing
  the manual and building it still work -- only the prose check is missing, and
  it will try again next time you run it.

HELP
  exit 1
fi
