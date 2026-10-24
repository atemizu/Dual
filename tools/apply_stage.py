#!/usr/bin/env python3
"""Put a stage's files into a prepared Helium source tree (the same result as
applying helium-dual-window.patch made from that stage).

  apply_stage.py <stage> <prepared Helium src>
"""
import shutil, sys
from pathlib import Path

stage, src = Path(sys.argv[1]), Path(sys.argv[2])
count = 0
for path in sorted(p for p in stage.rglob('*') if p.is_file() and p.name != '.DS_Store'):
    target = src / path.relative_to(stage)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.read_bytes() != path.read_bytes():
        shutil.copyfile(path, target)
        count += 1
print(f'{count} files written')
