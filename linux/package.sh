#!/usr/bin/env bash
# Packs a built Dual for Linux into dual-browser-<version>-<arch>.tar.xz.
#   linux/package.sh <helium-linux checkout> <out dir, e.g. Default> <version> <built hosts dir> <destination>
# <built hosts dir> holds dual-translate-host for the same architecture
# (translate-host/build_linux.sh).
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(dirname "$here")
helium=$1; out=$2; version=$3; hosts=$4; rel=$5
src="$helium/build/src/out/$out"
arch=$(grep ^target_cpu "$src/args.gn" | tail -1 | cut -d\" -f2); [ "$arch" = x64 ] && arch=x86_64
name=dual-browser-$version-$arch
dir=$rel/$name
rm -rf "$dir"; mkdir -p "$dir/locales"
for f in helium chrome_100_percent.pak chrome_200_percent.pak helium_crashpad_handler icudtl.dat libEGL.so libGLESv2.so \
         libqt5_shim.so libqt6_shim.so libvk_swiftshader.so libvulkan.so.1 product_logo_256.png resources.pak \
         v8_context_snapshot.bin vk_swiftshader_icd.json xdg-mime xdg-settings; do
  [ -e "$src/$f" ] && cp -r "$src/$f" "$dir/"
done
cp "$src"/locales/*.pak "$dir/locales/"
# The launcher: the browser with its libraries beside it.
cat > "$dir/dual-browser" <<"WRAP"
#!/bin/sh
# Dual: an unofficial derivative of Helium (GPL-3.0). Starts the browser in this folder.
export CHROME_VERSION_EXTRA="dual"
CHROME_WRAPPER="$(readlink -f "$0")"
HERE="$(dirname "$CHROME_WRAPPER")"
export CHROME_WRAPPER
export LD_LIBRARY_PATH="$HERE:$HERE/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
exec "$HERE/helium" "$@"
WRAP
chmod +x "$dir/dual-browser"
# The desktop entry: Helium's, with Dual's name, launcher and icon.
sed -e "s/^Name=Helium$/Name=Dual/" -e "s|^Exec=helium|Exec=dual-browser|" -e "s/^Icon=helium$/Icon=dual-browser/" \
    -e "/^\[Desktop Entry\]$/a StartupWMClass=dual-browser" \
    "$helium/package/helium.desktop" > "$dir/dual-browser.desktop"
# For the person installing it: puts the menu entry and icon in place for this user.
cat > "$dir/install-for-me.sh" <<"INST"
#!/bin/sh
# Adds Dual to this user's application menu (no administrator rights needed).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/256x256/apps"
sed "s|^Exec=dual-browser|Exec=\"$HERE/dual-browser\"|" "$HERE/dual-browser.desktop" > "$HOME/.local/share/applications/dual-browser.desktop"
cp "$HERE/product_logo_256.png" "$HOME/.local/share/icons/hicolor/256x256/apps/dual-browser.png"
echo "Dual was added to the application menu."
INST
chmod +x "$dir/install-for-me.sh"
# Where AppArmor restricts the sandbox (Ubuntu 23.10 and later): a profile like
# Helium's, for the folder Dual is unpacked in (README.txt says how).
cat > "$dir/apparmor.cfg" <<"ARMOR"
abi <abi/4.0>,
include <tunables/global>

profile dual-browser "/path/to/dual-browser-folder/helium" flags=(default_allow) {
  userns,
  include if exists <local/dual-browser>
}
ARMOR
cat > "$dir/README.txt" <<READ
Dual for Linux $version ($arch), a preview
An unofficial derivative of the Helium browser: two independent browsers, each
with its own tab bar, side by side in one window.

Start:              ./dual-browser
Add to the menu:    ./install-for-me.sh
Profile:            ~/.config/dual-browser
Translation model:  ~/.local/share/dual-translation (only if you download it)

If Dual does not start and says the sandbox could not be set up (Ubuntu 23.10
and later restrict it with AppArmor): put the full path of the "helium" file
in this folder into apparmor.cfg, then
  sudo cp apparmor.cfg /etc/apparmor.d/dual-browser
  sudo apparmor_parser -r /etc/apparmor.d/dual-browser

Source and license (GPL-3.0-only): https://github.com/atemizu/Dual/tree/v$version
(BUILDING-linux.md). Dual is not affiliated with imput LLC or the Helium project.
READ
# The extensions Dual ships with, and the translation program, next to the program.
python3 "$here/bundle_extensions_linux.py" "$repo/extensions" "$dir" "$version" --hosts "$hosts"
cp "$repo/LICENSE" "$dir/LICENSE"
find "$dir" -type f -exec file {} + | awk -F: '/ELF/ {print $1}' | \
  xargs "$helium/build/src/third_party/llvm-build/Release+Asserts/bin/llvm-strip" --strip-unneeded 2>/dev/null || true
(cd "$rel" && tar cf - "$name" | xz -T0 -6 > "$name.tar.xz")
ls -la "$rel/$name.tar.xz"
