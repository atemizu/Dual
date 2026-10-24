#!/usr/bin/env python3
"""Make a stage from the published patch: Dual's version of every file the
patch adds or changes, laid out like the Helium source tree.

  stage_from_patch.py <prepared Helium src> <helium-dual-window.patch> <stage>

The source tree is only read. It must be the Helium the patch was made for,
prepared but without the patch applied.
"""
import re, shutil, subprocess, sys
from pathlib import Path


def main():
    src, patch, stage = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    if stage.exists():
        raise SystemExit(f'{stage} exists already')
    names = re.findall(r'(?m)^\+\+\+ b/(.+)$', patch.read_text(encoding='utf-8'))
    for name in names:
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if (src / name).exists():
            shutil.copyfile(src / name, target)
    result = subprocess.run(['patch', '-p1', '--forward', '--silent', '-d', str(stage), '-i', str(patch.resolve())],
                            capture_output=True, text=True)
    if result.returncode:
        raise SystemExit('the patch does not apply to this source:\n' + result.stdout + result.stderr)
    leftovers = [p for p in stage.rglob('*') if p.suffix in ('.orig', '.rej')]
    if leftovers:
        raise SystemExit(f'patch left {leftovers}')
    print(f'{len(names)} files in {stage}')


if __name__ == '__main__':
    main()
