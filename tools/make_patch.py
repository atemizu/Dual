#!/usr/bin/env python3
"""Write helium-dual-window.patch from a stage: every staged file diffed
against the prepared Helium tree it was made for. Changed files first, then
Dual's own new files, each group in path order.

  make_patch.py <prepared Helium src> <stage> <patch to write>
"""
import subprocess, sys
from pathlib import Path


def main():
    pristine, stage, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    files = sorted(str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file() and p.name != '.DS_Store')
    changed = [f for f in files if (pristine / f).exists()]
    new = [f for f in files if not (pristine / f).exists()]
    chunks = []
    for name in changed + new:
        old = pristine / name if name in changed else Path('/dev/null')
        label = f'a/{name}' if name in changed else '/dev/null'
        result = subprocess.run(['diff', '-u', '--label', label, '--label', f'b/{name}', str(old), str(stage / name)],
                                capture_output=True, text=True)
        if result.returncode == 0:
            print('unchanged, skipped:', name, file=sys.stderr)
            continue
        if result.returncode != 1:
            raise SystemExit(result.stderr)
        chunks.append(result.stdout)
    out.write_text(''.join(chunks))
    print(f'{len(chunks)} files ({len(changed)} changed, {len(new)} new) -> {out}')


if __name__ == '__main__':
    main()
