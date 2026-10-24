#!/bin/bash
# Builds dual-translate-host for Linux with Chromium's clang and Debian
# bullseye sysroot, so that it runs wherever Dual for Linux does.
#   build_linux.sh <llama.cpp checkout at b11846> <out dir> <arm64|x64> <Chromium src>
# Leaves <out>/dual-translate-host and <out>/dual-translate-host-licenses.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
llama=$1
out=$2
arch=$3
chromium=$4
clang="$chromium/third_party/llvm-build/Release+Asserts/bin"
case "$arch" in
  arm64) target=aarch64-linux-gnu; processor=aarch64; sysroot="$chromium/build/linux/debian_bullseye_arm64-sysroot" ;;
  x64) target=x86_64-linux-gnu; processor=x86_64; sysroot="$chromium/build/linux/debian_bullseye_amd64-sysroot" ;;
  *) echo "arch is arm64 or x64" >&2; exit 1 ;;
esac
cmake -S "$here" -B "$out/build" -DLLAMA_SOURCE="$llama" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR="$processor" \
  -DCMAKE_C_COMPILER="$clang/clang" -DCMAKE_CXX_COMPILER="$clang/clang++" \
  -DCMAKE_C_COMPILER_TARGET="$target" -DCMAKE_CXX_COMPILER_TARGET="$target" \
  -DCMAKE_SYSROOT="$sysroot" -DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=lld" \
  -DGGML_OPENMP=OFF
cmake --build "$out/build" --target dual-translate-host -j "$(nproc)"
cp "$out/build/dual-translate-host" "$out/dual-translate-host"
"$clang/llvm-strip" "$out/dual-translate-host" 2>/dev/null || true
rm -rf "$out/dual-translate-host-licenses"
cp -R "$here/licenses" "$out/dual-translate-host-licenses"
