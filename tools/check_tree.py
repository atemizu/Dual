#!/usr/bin/env python3
"""Does a build tree hold exactly Helium plus the stage plus the rebrand?

  check_tree.py <prepared Helium src (untouched)> <stage> <build tree src> [--fix-stage]

Every file of the build tree is compared with the untouched source. A file
that differs must be in the stage and equal to it, or be something
dual_rebrand.py writes (message files, translations, logos). Anything else is
reported: a change made in the tree but missing from the stage, or the other
way round. Build output (out/), caches and the tools that Helium's configure
step downloads into the tree are skipped.
With --fix-stage, files of the stage that differ in the tree are copied from
the tree, and changed files unknown to the stage are listed for adding.
Exit status 0 when tree and stage agree.
"""
import filecmp, os, shutil, sys
from pathlib import Path

SKIP_DIRS = {'out', '.git', '__pycache__', '.pc'}
# Downloaded into the tree by Helium's configure step (cipd packages).
TOOLS = ('third_party/dawn/tools/', 'third_party/typescript/mac-arm64/', 'third_party/siso/cipd/', 'buildtools/mac/',
         'third_party/depot_tools/.', 'third_party/devtools-frontend/src/third_party/esbuild/',
         'third_party/llvm-build/')
# Written into the source tree by the build, from the (rebranded) messages.
GENERATED = ('components/helium_onboarding/src/lib/strings.ts',)
# What dual_rebrand.py rewrites: messages, translations and Helium's logo files.
REBRAND_SUFFIXES = ('.grd', '.grdp', '.xtb')
REBRAND_NAMES = ('product_logo', 'browser_logo', 'chrome_product', 'product_chrome_refresh', 'product_old',
                 'product.icon', 'product_refresh.icon', 'favicon.png')


def main():
    pristine, stage, tree = (Path(a) for a in sys.argv[1:4])
    fix = '--fix-stage' in sys.argv
    staged = {str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file() and p.name != '.DS_Store'}
    changed, new = set(), set()
    for root, dirs, files in os.walk(tree):
        rel_root = Path(root).relative_to(tree)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            rel = str(rel_root / name)
            if name.endswith(('.pyc', '.DS_Store', '.orig', '.rej')) or rel.startswith(TOOLS) or rel in GENERATED:
                continue
            mine, theirs = tree / rel, pristine / rel
            if not theirs.exists():
                new.add(rel)
            elif mine.stat().st_size != theirs.stat().st_size or not filecmp.cmp(mine, theirs, shallow=False):
                changed.add(rel)
    rebrand = {f for f in changed | new if f.endswith(REBRAND_SUFFIXES) or any(n in Path(f).name for n in REBRAND_NAMES)}
    problems = []
    for rel in sorted((changed | new) - rebrand):
        if rel not in staged:
            problems.append(('in the tree, not in the stage', rel))
        elif not filecmp.cmp(tree / rel, stage / rel, shallow=False):
            if fix:
                shutil.copyfile(tree / rel, stage / rel)
                print('stage updated from the tree:', rel)
            else:
                problems.append(('differs between tree and stage', rel))
    for rel in sorted(staged - changed - new):
        problems.append(('in the stage, but the tree has Helium\'s file', rel))
    print(f'{len(changed)} files changed and {len(new)} added in the tree; {len(rebrand)} of them by the rebrand; '
          f'{len(staged)} in the stage')
    for kind, rel in problems:
        print(f'  {kind}: {rel}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
