#!/usr/bin/env python3
# Dual: unofficial modifications of Helium, 2026-09-08 to 2026-10-04 (Dual 6.2.3).
# Modifications Copyright 2026 Dual contributors; GPL-3.0-only.
"""Package a built Dual app as the public release DMG.

  python3 packaging/package_release.py \
      --built "/path/to/src/out/Default/Helium Dual.app" \
      --icon Dual-6.icns --version 6.2.3 --out /path/to/release

Copies the built app, sets the public name and bundle identifier (kept equal to
Dual 5 so an existing profile carries over), applies the icon, ad-hoc signs it
and writes Dual-<version>-macOS-arm64.dmg with a SHA-256 file. The input build
is not modified.
"""

import argparse
import hashlib
import plistlib
import shutil
import subprocess
from pathlib import Path

BUNDLE_ID = 'local.heliumdual.browser'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--built', required=True, type=Path)
    parser.add_argument('--icon', required=True, type=Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()

    name = f'Dual {args.version}'
    root = args.out / 'dmg-root'
    if root.exists():
        raise SystemExit(f'refusing to overwrite {root}')
    root.mkdir(parents=True)
    app = root / f'{name}.app'
    subprocess.run(['/bin/cp', '-Rp', str(args.built), str(app)], check=True)

    info_path = app / 'Contents/Info.plist'
    info = plistlib.loads(info_path.read_bytes())
    info.update(CFBundleIdentifier=BUNDLE_ID, CFBundleName=name,
                CFBundleDisplayName=name, CFBundleIconFile='app.icns')
    info.pop('CFBundleIconName', None)  # use app.icns, not the asset catalog
    info.pop('CrProductDirName', None)
    info_path.write_bytes(plistlib.dumps(info))
    shutil.copyfile(args.icon, app / 'Contents/Resources/app.icns')

    subprocess.run(['/usr/bin/codesign', '--force', '--deep', '--sign', '-',
                    '--timestamp=none', '--identifier', BUNDLE_ID, str(app)],
                   check=True)
    subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict',
                    str(app)], check=True)

    (root / 'Applications').symlink_to('/Applications')
    dmg = args.out / f'Dual-{args.version}-macOS-arm64.dmg'
    subprocess.run(['/usr/bin/hdiutil', 'create', '-volname', name,
                    '-srcfolder', str(root), '-format', 'ULFO', str(dmg)],
                   check=True)
    digest = hashlib.sha256(dmg.read_bytes()).hexdigest()
    (dmg.parent / (dmg.name + '.sha256')).write_text(f'{digest}  {dmg.name}\n')
    print(digest, dmg)


if __name__ == '__main__':
    main()
