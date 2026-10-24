#!/bin/bash
# Builds dual-translate-host for macOS (arm64, Metal, macOS 13 or later).
#   build_mac.sh <llama.cpp checkout at b11846> <out dir> [cmake]
# Leaves <out>/dual-translate-host and <out>/dual-translate-host-licenses, the
# --hosts directory for bundle_extensions.py.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
llama=$1
out=$2
cmake=${3:-cmake}
"$cmake" -S "$here" -B "$out/build" -DLLAMA_SOURCE="$llama" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=13.0 -DCMAKE_OSX_ARCHITECTURES=arm64
"$cmake" --build "$out/build" --target dual-translate-host -j 8
cp "$out/build/dual-translate-host" "$out/dual-translate-host"
strip -x "$out/dual-translate-host"
rm -rf "$out/dual-translate-host-licenses"
cp -R "$here/licenses" "$out/dual-translate-host-licenses"
