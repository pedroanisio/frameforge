#!/usr/bin/env bash
# collect-google-fonts.sh — assemble the full google/fonts corpus into one dir.
#
# The whole google/fonts repo is the single biggest lever for "as many fonts as
# we can build": ~1500+ families / thousands of TTF+OTF faces under the ofl/,
# apache/ and ufl/ license trees. We shallow-clone it, then copy every face into
# $DEST (flat), leaving the git working tree (and its ~1GB history-free checkout)
# behind in the builder stage so it never reaches the final image.
#
# Env:
#   DEST               destination font dir (default: /usr/share/fonts/truetype/google-fonts)
#   GOOGLE_FONTS_REF   branch/tag/commit to check out (default: main; depth-1 clone)
#   GOOGLE_FONTS_REPO  clone URL (default: https://github.com/google/fonts.git)
set -euo pipefail

DEST="${DEST:-/usr/share/fonts/truetype/google-fonts}"
REF="${GOOGLE_FONTS_REF:-main}"
REPO="${GOOGLE_FONTS_REPO:-https://github.com/google/fonts.git}"
WORK="$(mktemp -d)"

echo ">> cloning ${REPO} (ref=${REF}, shallow) ..."
if [ "${REF}" = "main" ] || [ "${REF}" = "master" ]; then
  git clone --depth 1 --branch "${REF}" "${REPO}" "${WORK}/fonts"
else
  # A specific commit/tag: clone shallow at main, then fetch+checkout the ref.
  git clone --depth 1 "${REPO}" "${WORK}/fonts"
  git -C "${WORK}/fonts" fetch --depth 1 origin "${REF}"
  git -C "${WORK}/fonts" checkout --detach FETCH_HEAD
fi

mkdir -p "${DEST}"
echo ">> collecting .ttf/.otf faces into ${DEST} ..."
count=0
# Only the license trees hold shippable faces; skip axisregistry/lang/tools/etc.
for tree in ofl apache ufl; do
  src="${WORK}/fonts/${tree}"
  [ -d "${src}" ] || continue
  while IFS= read -r -d '' f; do
    # Flatten with a family-prefixed name so identically-named faces across
    # families (e.g. many "*-Regular.ttf") do not clobber each other.
    fam="$(basename "$(dirname "$f")")"
    cp -n "$f" "${DEST}/${fam}--$(basename "$f")"
    count=$((count + 1))
  done < <(find "${src}" -type f \( -iname '*.ttf' -o -iname '*.otf' \) -print0)
done

echo ">> collected ${count} google/fonts faces."
rm -rf "${WORK}"
