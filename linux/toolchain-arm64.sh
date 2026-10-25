#!/usr/bin/env bash
# For building on an arm64 Linux machine only. The prepared Helium Linux
# 0.20.1.1 source comes with x86-64 build tools; this puts arm64 ones in their
# place: clang, Rust, bindgen and crubit built from source, gn, siso and esbuild
# from CIPD at the versions DEPS names, the TypeScript 7.0.2 compiler from npm,
# Node.js 24.12.0 from nodejs.org, and the system's python3, ninja, gperf,
# clang-format and mold. Last, a shared libclang for V8's metagen.
#   linux/toolchain-arm64.sh <helium-linux checkout>
# These are the steps Dual 6.4.0 for Linux was built with, in the order they
# were run (BUILDING-linux.md); they were run one part at a time, not as this
# one script. Building clang and Rust takes a few hours.
set -euxo pipefail
here=$(cd "$(dirname "$0")" && pwd)
S="$1/build/src"
cd "$S"
tmp=$(mktemp -d)

# Domain substitution also rewrote the tool download hosts.
sed -i "s/commondatastorage.9oo91eapis.qjz9zk/commondatastorage.googleapis.com/g" \
  build/linux/sysroot_scripts/sysroots.json tools/clang/scripts/update.py tools/clang/scripts/build.py
sed -i "s/chromium.9oo91esource.qjz9zk/chromium.googlesource.com/g" \
  tools/clang/scripts/build.py tools/rust/build_rust.py tools/rust/build_bindgen.py tools/rust/build_crubit.py 2>/dev/null || true
sed -i "s/chrome-infra-packages.8pp2p8t.qjz9zk/chrome-infra-packages.appspot.com/g" tools/rust/build_rust.py
grep -rl "9oo91e\|8pp2p8t" tools/rust/*.py tools/clang/scripts/*.py || true

# gn, siso and esbuild: the linux-arm64 packages of the versions the source names.
cipd_file() {  # package version file-in-package destination
  rm -rf "$tmp/c" && mkdir "$tmp/c"
  curl -sSfL -o "$tmp/c/p.zip" "https://chrome-infra-packages.appspot.com/dl/$1/+/$2"
  (cd "$tmp/c" && unzip -q p.zip)
  cp "$tmp/c/$3" "$4"
}
cipd_file gn/gn/linux-arm64 "$(grep -oP "\x27gn_version\x27: \x27\K[^\x27]+" DEPS)" gn buildtools/linux64/gn
cipd_file build/siso/linux-arm64 "$(grep -oP "\x27siso_version\x27: \x27\K[^\x27]+" DEPS)" siso third_party/siso/cipd/siso
cipd_file infra/3pp/tools/esbuild/linux-arm64 "version:3@0.28.2.chromium.2" esbuild \
  third_party/devtools-frontend/src/third_party/esbuild/esbuild
buildtools/linux64/gn --version

# The TypeScript compiler (tsgo) DEPS names for linux-amd64, version 7.0.2, for arm64.
(cd "$tmp" && npm pack --silent @typescript/typescript-linux-arm64@7.0.2 && tar xzf typescript-typescript-linux-arm64-7.0.2.tgz)
T=third_party/typescript/linux-amd64/src/lib
chmod u+w "$T" "$T/tsc"; cp "$tmp/package/lib/tsc" "$T/tsc"; chmod 755 "$T/tsc"
"$T/tsc" --version

# Tools from the system (Debian packages python3, ninja-build, gperf, clang-format, mold).
for f in third_party/cpython3/host/bin/python3 third_party/cpython3/host/bin/python3.11; do ln -sf /usr/bin/python3 $f; done
ln -sf /usr/bin/ninja third_party/ninja/ninja
ln -sf /usr/bin/gperf third_party/gperf/cipd/bin/gperf
ln -sf /usr/bin/clang-format buildtools/linux64-format/clang-format
ln -sf /usr/bin/mold buildtools/third_party/mold/cipd/mold

# Node.js 24.12.0, the version Chromium 156 expects.
(cd "$tmp" && curl -sSfLO https://nodejs.org/dist/v24.12.0/node-v24.12.0-linux-arm64.tar.xz &&
  curl -sSfL https://nodejs.org/dist/v24.12.0/SHASUMS256.txt | grep " node-v24.12.0-linux-arm64.tar.xz$" | sha256sum -c)
sudo rm -rf /opt/node24.12 && sudo mkdir -p /opt/node24.12
sudo tar xJf "$tmp/node-v24.12.0-linux-arm64.tar.xz" -C /opt/node24.12 --strip-components=1
ln -sf /opt/node24.12/bin/node third_party/node/linux/node-linux-x64/bin/node
third_party/node/linux/node-linux-x64/bin/node --version

# clang, from the LLVM revision the source names (Debian's clang builds it).
rm -rf third_party/llvm-build/Release+Asserts third_party/rust-toolchain
tools/clang/scripts/build.py --without-fuchsia --without-android --disable-asserts \
  --host-cc=clang --host-cxx=clang++ --use-system-cmake --with-ml-inliner-model=

# helium-linux's fix for arm64 hosts (from its 0.18.3.1 release; 0.20.1.1 no
# longer carries it): a V8 toolchain for an x86-64 build made on arm64, and more.
patch -p1 --forward < "$here/fix-compiling-on-arm64.patch"

# Rust, bindgen (its own tests do not compile with this toolchain on arm64) and crubit.
export CARGO_HOME="$S/third_party/rust-src/cargo-home"
tools/rust/build_rust.py --skip-test
tools/rust/build_bindgen.py --skip-test || tools/rust/build_bindgen.py
[ -f tools/rust/build_crubit.py ] && tools/rust/build_crubit.py || true

# The Debian bullseye sysroots: arm64, and amd64 for the x86-64 build.
build/linux/sysroot_scripts/install-sysroot.py --arch=arm64
build/linux/sysroot_scripts/install-sysroot.py --arch=amd64

# A shared, arm64 libclang for v8/tools/metagen (its Python bindings), built
# with position-independent code from the same LLVM checkout.
B="$1/../libclang-build"
mkdir -p "$B" && cd "$B"
LLVM_BIN=$S/third_party/llvm-build/Release+Asserts/bin
cmake -G Ninja "$S/third_party/llvm/llvm" -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_PROJECTS=clang \
  -DLLVM_TARGETS_TO_BUILD="AArch64;X86" -DLLVM_ENABLE_PIC=ON -DLIBCLANG_BUILD_STATIC=OFF \
  -DLLVM_ENABLE_ASSERTIONS=OFF -DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF \
  -DLLVM_ENABLE_ZSTD=OFF -DLLVM_ENABLE_ZLIB=OFF -DLLVM_ENABLE_LIBXML2=OFF -DLLVM_ENABLE_TERMINFO=OFF \
  -DCMAKE_C_COMPILER="$LLVM_BIN/clang" -DCMAKE_CXX_COMPILER="$LLVM_BIN/clang++" -DLLVM_USE_LINKER=lld
ninja libclang
cp -L lib/libclang.so "$S/third_party/llvm-libclang/lib/libclang.so"
rm -rf "$tmp"
echo TOOLCHAIN-DONE
