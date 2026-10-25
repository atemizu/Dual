#!/usr/bin/env python3
"""Dual's change set for Linux: the stage (the canonical source, shared with
macOS) against the prepared Helium source it was made on, as one patch to
apply to a prepared Helium Linux source of the same version.

  make_linux_patch.py <stage> <prepared Helium src> <out.patch>

Files only macOS builds (.mm, *_mac.h) are left out. A file new in the stage
becomes a file added by the patch.
"""
import difflib, sys
from pathlib import Path

stage, pristine, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
chunks = []
for path in sorted(p for p in stage.rglob('*') if p.is_file()):
    rel = str(path.relative_to(stage))
    if rel.endswith(('.mm', '_mac.h')) or '/.' in '/' + rel:
        continue
    new = path.read_text(errors='surrogateescape').splitlines(keepends=True)
    old_path = pristine / rel
    old = old_path.read_text(errors='surrogateescape').splitlines(keepends=True) if old_path.exists() else []
    if old == new:
        continue
    diff = list(difflib.unified_diff(old, new, fromfile='a/' + rel if old_path.exists() else '/dev/null',
                                     tofile='b/' + rel, n=3))
    # Hunks that only list macOS files (in build files) are left out: the
    # macOS parts of a build file differ between the platforms' sources.
    head, hunks = diff[:2], []
    for line in diff[2:]:
        if line.startswith('@@'):
            hunks.append([line])
        else:
            hunks[-1].append(line)
    def mac_only(hunk):
        added = [l for l in hunk[1:] if l.startswith('+')]
        return rel.endswith('.gn') and added and all('_mac.' in l for l in added)
    kept = [h for h in hunks if not mac_only(h)]
    if not kept:
        continue
    lines = head + [l for h in kept for l in h]
    text = ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n' for line in lines)
    chunks.append(text)
out.write_text(''.join(chunks), errors='surrogateescape')
print(f'{len(chunks)} files -> {out}')
