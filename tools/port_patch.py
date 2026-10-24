#!/usr/bin/env python3
"""Carry Dual's changes over to a newer Helium.

Dual is kept as a "stage": its own version of every file it adds or changes,
laid out like the Helium source tree. To move to a newer Helium, each changed
file is merged three ways:

    base    the file in the Helium the stage was made for (the old prepared tree)
    ours    the file in the stage
    theirs  the file in the newer Helium (the new prepared tree)

  port_patch.py --old-helium <old prepared src> --new-helium <new prepared src>
                --stage <stage> --out <new stage>

Files that merge cleanly are written to the new stage as they are. Files with
conflicts are written with conflict markers and listed, to be resolved by hand.
Files that the newer Helium no longer has are listed too. Dual's own new files
are copied unless the newer Helium has gained a file of the same name.
Exit status: 0 when everything merged cleanly, 1 otherwise.
"""
import argparse, json, shutil, subprocess, sys
from pathlib import Path


def merge(ours, base, theirs):
    """(merged text as bytes, number of conflicts)."""
    result = subprocess.run(
        ['git', 'merge-file', '-p', '--diff3', '-L', 'Dual', '-L', 'old Helium', '-L', 'new Helium',
         str(ours), str(base), str(theirs)], capture_output=True)
    if result.returncode < 0 or result.returncode > 127:
        raise SystemExit(f'git merge-file failed on {ours}: {result.stderr.decode()}')
    return result.stdout, result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('old-helium', 'new-helium', 'stage', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    old, new, stage, out = args.old_helium, args.new_helium, args.stage, args.out
    if out.exists():
        shutil.rmtree(out)
    report = {'clean': [], 'unchanged_upstream': [], 'conflicts': {}, 'gone_upstream': [], 'new_files': [],
              'name_taken_upstream': []}
    for path in sorted(p for p in stage.rglob('*') if p.is_file() and p.name != '.DS_Store'):
        name = str(path.relative_to(stage))
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not (old / name).exists():
            # One of Dual's own files.
            if (new / name).exists():
                report['name_taken_upstream'].append(name)
            else:
                report['new_files'].append(name)
            shutil.copyfile(path, target)
            continue
        if not (new / name).exists():
            report['gone_upstream'].append(name)
            shutil.copyfile(path, target)
            continue
        if (old / name).read_bytes() == (new / name).read_bytes():
            report['unchanged_upstream'].append(name)
            shutil.copyfile(path, target)
            continue
        merged, conflicts = merge(path, old / name, new / name)
        target.write_bytes(merged)
        if conflicts:
            report['conflicts'][name] = conflicts
        else:
            report['clean'].append(name)
    (out.parent / (out.name + '-report.json')).write_text(json.dumps(report, indent=1) + '\n')
    print(f"Dual's own files copied:           {len(report['new_files'])}")
    print(f"changed files, upstream unchanged: {len(report['unchanged_upstream'])}")
    print(f"changed files, merged cleanly:     {len(report['clean'])}")
    print(f"changed files with conflicts:      {len(report['conflicts'])}")
    for name, count in report['conflicts'].items():
        print(f'    {count:2d}  {name}')
    for key, label in (('gone_upstream', 'no longer in the newer Helium'),
                       ('name_taken_upstream', 'the newer Helium now has a file of this name')):
        if report[key]:
            print(f'{label}:')
            for name in report[key]:
                print(f'    {name}')
    clean = not (report['conflicts'] or report['gone_upstream'] or report['name_taken_upstream'])
    return 0 if clean else 1


if __name__ == '__main__':
    sys.exit(main())
