#!/usr/bin/env bash
# Puts Dual into a Helium Linux 0.20.1.1 source prepared by helium-linux's own
# steps (BUILDING-linux.md, step 1), then gives the app Dual's name and logo.
#   linux/apply.sh <helium-linux checkout>
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(dirname "$here")
src="$1/build/src"
# Dual's changes: helium-dual-window.patch without the parts only macOS builds
# (make_linux_patch.py makes one from the other).
patch -p1 --forward -d "$src" < "$here/dual-0.20.1.1-linux.patch"
# Dual for Linux's own profile folder, desktop entry and icon name.
patch -p1 --forward -d "$src" < "$here/linux-identity.patch"
python3 "$repo/dual_rebrand.py" "$src" --branding "$repo/branding"
