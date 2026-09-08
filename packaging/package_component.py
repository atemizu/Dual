#!/usr/bin/env python3
# Copyright 2026 Helium Dual contributors.
# You can use, redistribute, and/or modify this source code under
# the terms of the GPL-3.0 license that can be found in the LICENSE file.
# Modified: 2026-09-09 (source-publication preparation).
"""Privately package a completed Chromium/Helium macOS component build.

Does not build, launch, install, modify the source, or replace an existing app.
Only the app and its recursively discovered non-system Mach-O dependencies are
copied. A successful report proves dependency closure and signatures, not UX.
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import time
from typing import Any

BASE = Path(__file__).resolve().parents[2]
MAGICS = {bytes.fromhex(x) for x in (
    'feedface', 'cefaedfe', 'feedfacf', 'cffaedfe',
    'cafebabe', 'bebafeca', 'cafebabf', 'bfbafeca')}
SYSTEM_PREFIXES = ('/usr/lib/', '/System/Library/', '/System/iOSSupport/',
                   '/Library/Apple/System/Library/')
LOAD_COMMANDS = {'LC_LOAD_DYLIB', 'LC_LOAD_WEAK_DYLIB', 'LC_REEXPORT_DYLIB',
                 'LC_LOAD_UPWARD_DYLIB', 'LC_LAZY_LOAD_DYLIB'}
BUNDLE_SUFFIXES = {'.app', '.framework', '.xpc', '.appex', '.bundle'}


class PackageError(RuntimeError):
    pass


def run(args: list[str | Path], *, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run([str(x) for x in args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    if check and result.returncode:
        raise PackageError(f"Command failed ({result.returncode}): {args!r}\n"
                           + result.stdout.decode(errors='replace')
                           + result.stderr.decode(errors='replace'))
    return result


def within(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def macho(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open('rb') as stream:
        return stream.read(4) in MAGICS


def files(root: Path):
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs.sort()
        for name in sorted(names):
            path = Path(directory) / name
            if not path.is_symlink():
                yield path


def machos(root: Path) -> list[Path]:
    return [p.resolve() for p in files(root) if macho(p)]


def bundle_plist(bundle: Path) -> tuple[dict, Path] | None:
    candidates = [bundle / 'Contents/Info.plist', bundle / 'Resources/Info.plist',
                  bundle / 'Info.plist']
    for plist in candidates:
        if not plist.is_file():
            continue
        with plist.open('rb') as stream:
            info = plistlib.load(stream)
        name = info.get('CFBundleExecutable')
        if not name:
            continue
        executable_candidates = [bundle / 'Contents/MacOS' / name, bundle / name]
        executable_candidates += list(bundle.glob(f'Versions/*/{name}'))
        for executable in executable_candidates:
            if executable.is_file() and macho(executable):
                return info, executable.resolve()
    return None


def executable_context(image: Path, app: Path, info: 'Image') -> Path:
    if info.executable:
        return image
    for parent in image.parents:
        if parent.suffix in {'.app', '.xpc', '.appex'}:
            details = bundle_plist(parent)
            if details:
                return details[1]
        if parent == app:
            break
    details = bundle_plist(app)
    if not details:
        raise PackageError(f'No main executable in {app}')
    return details[1]


@dataclasses.dataclass(frozen=True)
class Dependency:
    name: str
    weak: bool = False


@dataclasses.dataclass
class Image:
    dependencies: list[Dependency]
    rpaths: list[str]
    install_id: str | None
    executable: bool


class Inspector:
    def __init__(self):
        self.cache: dict[Path, Image] = {}

    def read(self, path: Path) -> Image:
        path = path.resolve()
        if path in self.cache:
            return self.cache[path]
        output = run(['/usr/bin/otool', '-m', '-l', path]).stdout.decode(errors='strict')
        deps: list[Dependency] = []
        rpaths: list[str] = []
        install_id = None
        executable = False
        command = ''
        for line in output.splitlines():
            value = line.strip()
            if value.startswith('cmd '):
                command = value[4:]
                executable |= command in {'LC_MAIN', 'LC_UNIXTHREAD'}
            elif command in LOAD_COMMANDS and value.startswith('name '):
                dep = Dependency(value[5:].rsplit(' (offset ', 1)[0],
                                 command == 'LC_LOAD_WEAK_DYLIB')
                if dep not in deps:
                    deps.append(dep)
            elif command == 'LC_ID_DYLIB' and value.startswith('name '):
                new_id = value[5:].rsplit(' (offset ', 1)[0]
                if install_id and install_id != new_id:
                    raise PackageError(f'Different install IDs across architectures: {path}')
                install_id = new_id
            elif command == 'LC_RPATH' and value.startswith('path '):
                rpath = value[5:].rsplit(' (offset ', 1)[0]
                if rpath not in rpaths:
                    rpaths.append(rpath)
        result = Image(deps, rpaths, install_id, executable)
        self.cache[path] = result
        return result


def system(name: str) -> bool:
    return any(name == prefix.rstrip('/') or name.startswith(prefix)
               for prefix in SYSTEM_PREFIXES)


def expand(value: str, image: Path, executable: Path) -> Path | None:
    for token, parent in (('@loader_path', image.parent),
                          ('@executable_path', executable.parent)):
        if value == token or value.startswith(token + '/'):
            return (parent / value[len(token):].lstrip('/')).resolve()
    if value.startswith('/'):
        return Path(value).resolve()
    return None


def resolve(dep: str, image: Path, executable: Path,
            search: tuple[Path, ...], fallback: Path | None = None) -> Path:
    candidates: list[Path] = []
    direct = expand(dep, image, executable)
    if direct:
        candidates.append(direct)
    elif dep.startswith('@rpath/'):
        tail = dep.removeprefix('@rpath/')
        candidates.extend(p / tail for p in search)
        if fallback:
            candidates.append(fallback / tail)
    elif not dep.startswith('@'):
        # Legacy install names such as libfoo.dylib are relative at runtime;
        # resolve them in the build directory, then replace with loader paths.
        if fallback:
            candidates.extend([image.parent / dep, fallback / dep])
    for candidate in candidates:
        # macOS may keep system dylibs only in the dyld shared cache.
        if system(str(candidate)):
            return candidate
        if candidate.is_file() and macho(candidate):
            return candidate.resolve()
    raise PackageError(f'Unresolved dependency {dep!r} in {image}\n'
                       f'Executable context: {executable}\n'
                       f'Candidates: {[str(p) for p in candidates]}')


def framework_root(path: Path, stop: Path) -> Path | None:
    for parent in path.parents:
        if parent.suffix == '.framework':
            return parent
        if parent == stop:
            break
    return None


def audit_symlinks(root: Path) -> list[dict]:
    result = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in dirs + names:
            path = Path(directory) / name
            if not path.is_symlink():
                continue
            if not path.exists() or not within(path, root):
                raise PackageError(f'Broken or external bundle symlink: {path} -> {os.readlink(path)}')
            result.append({'path': str(path.relative_to(root)),
                           'target': os.readlink(path)})
    return result


def identical_bundle(source: Path, existing: Path) -> dict:
    """Require matching trees, symlink targets, modes, and every file byte."""
    def entries(root: Path) -> dict:
        result = {}
        for parent, directories, names in os.walk(root, followlinks=False):
            for name in directories + names:
                path = Path(parent) / name
                relative = str(path.relative_to(root))
                if path.is_symlink():
                    value = ('symlink', os.readlink(path))
                elif path.is_dir():
                    value = ('directory',)
                else:
                    value = ('file', path.stat().st_size,
                             stat.S_IMODE(path.stat().st_mode))
                result[relative] = value
        return result

    left, right = entries(source), entries(existing)
    if left != right:
        differences = [name for name in sorted(left.keys() | right.keys())
                       if left.get(name) != right.get(name)]
        raise PackageError(f'Framework destination collision with different trees: '
                           f'{source} and {existing}: {differences[:10]}')
    manifest = hashlib.sha256()
    size = count = 0
    for name, details in sorted(left.items()):
        if details[0] != 'file':
            manifest.update(json.dumps([name, details]).encode())
            continue
        def digest(path: Path) -> str:
            result = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    result.update(chunk)
            return result.hexdigest()
        source_hash, existing_hash = digest(source / name), digest(existing / name)
        if source_hash != existing_hash:
            raise PackageError(f'Framework destination collision with different bytes: '
                               f'{source / name} and {existing / name}')
        manifest.update(json.dumps([name, details, source_hash]).encode())
        size += details[1]
        count += 1
    return {'source': str(source), 'existing_app_copy': str(existing),
            'tree_entries': len(left), 'files_hashed': count,
            'file_bytes_in_each_copy': size,
            'identity_manifest_sha256': manifest.hexdigest(),
            'byte_identical': True}


class Plan:
    def __init__(self, source_app: Path):
        self.app = source_app.resolve()
        self.out = self.app.parent
        self.inspector = Inspector()
        self.mapping: dict[Path, Path] = {}
        self.copies: dict[Path, Path] = {}
        self.edges: dict[tuple[Path, str], Path] = {}
        self.contexts: dict[Path, set[Path]] = collections.defaultdict(set)
        self.system_deps: set[str] = set()
        self._queue = collections.deque()
        self._seen: set[tuple[Path, Path, tuple[Path, ...]]] = set()
        self._dest_owners: dict[Path, Path] = {}
        self.aliases: dict[Path, Path] = {}
        self.reused_frameworks: list[dict] = []

    def add_mapping(self, source: Path, relative: Path):
        source = source.resolve()
        previous = self.mapping.get(source)
        if previous and previous != relative:
            return
        owner = self._dest_owners.get(relative)
        if owner and owner != source:
            raise PackageError(f'Destination collision: {relative}: {owner} and {source}')
        self.mapping[source] = relative
        self._dest_owners[relative] = source

    def seed(self, root: Path, destination: Path):
        audit_symlinks(root)
        for image in machos(root):
            self.add_mapping(image, destination / image.relative_to(root.resolve()))
            context = executable_context(image, self.app, self.inspector.read(image))
            self._queue.append((image, context, ()))

    def ensure_target(self, source: Path) -> Path:
        source = self.aliases.get(source, source)
        if source in self.mapping:
            return source
        if not within(source, self.out):
            raise PackageError(f'Non-system runtime dependency outside build output: {source}')
        if within(source, self.app):
            self.add_mapping(source, source.relative_to(self.app))
            return source
        framework = framework_root(source, self.out)
        if framework:
            relative = Path('Contents/Frameworks') / framework.name
            existing = self.app / relative
            if existing.is_dir():
                # Chromium also keeps the original framework beside the app.
                # Canonicalize its identical copy before adding graph edges, so
                # one destination is never relocated twice from stale commands.
                evidence = identical_bundle(framework, existing)
                aliases = {}
                for image in machos(framework):
                    canonical = (existing / image.relative_to(framework)).resolve()
                    if canonical not in self.mapping:
                        raise PackageError(f'Existing framework image was not seeded: {canonical}')
                    self.aliases[image] = canonical
                    aliases[str(image)] = str(canonical)
                evidence['macho_aliases'] = aliases
                self.reused_frameworks.append(evidence)
                return self.aliases[source]
            self.copies[framework] = relative
            self.seed(framework, relative)
            return source
        if source.suffix != '.dylib':
            raise PackageError(f'External dependency is not a dylib/framework: {source}')
        relative = Path('Contents/Frameworks') / source.name
        self.copies[source] = relative
        self.add_mapping(source, relative)
        return source

    def collect(self):
        self.seed(self.app, Path())
        while self._queue:
            image, executable, inherited = self._queue.popleft()
            data = self.inspector.read(image)
            current = tuple(p for r in data.rpaths
                            if (p := expand(r, image, executable)) is not None)
            # A loader's paths precede the inherited dependency-chain paths.
            search = tuple(dict.fromkeys(current + inherited))
            key = (image, executable, search)
            if key in self._seen:
                continue
            self._seen.add(key)
            if len(self._seen) > 100000:
                raise PackageError('Unexpectedly large/cyclic dynamic-loader graph')
            self.contexts[image].add(executable)
            for dep in data.dependencies:
                if system(dep.name):
                    self.system_deps.add(dep.name)
                    continue
                target = resolve(dep.name, image, executable, search, self.out)
                if not system(str(target)):
                    target = self.ensure_target(target)
                else:
                    self.system_deps.add(str(target))
                edge = (image, dep.name)
                previous = self.edges.get(edge)
                if previous and previous != target:
                    raise PackageError(f'Context-dependent resolution for {dep.name} in {image}')
                self.edges[edge] = target
                if not system(str(target)):
                    self._queue.append((target, executable, search))
        return self

    def report(self) -> dict:
        return {
            'source_app': str(self.app),
            'macho_count': len(self.mapping),
            'additional_copies': [{'source': str(s), 'destination': str(d)}
                                  for s, d in sorted(self.copies.items())],
            'non_system_edges': len(self.edges),
            'reused_identical_frameworks': self.reused_frameworks,
            'canonical_alias_count': len(self.aliases),
            'system_dependencies': sorted(self.system_deps),
        }


def signature_metadata(path: Path) -> tuple[bool, dict]:
    shown = run(['/usr/bin/codesign', '--display', '--entitlements', ':-', path], check=False)
    if shown.returncode:
        return False, {}
    data = shown.stdout
    if b'<?xml' in data:
        data = data[data.index(b'<?xml'):]
        data = data[:data.index(b'</plist>') + len(b'</plist>')]
        return True, plistlib.loads(data)
    if data.startswith(b'bplist00'):
        return True, plistlib.loads(data)
    return True, {}


def entitlement_profile(bundle: Path, app: Path, official: Path) -> Path | None:
    if bundle == app:
        return official / 'app-entitlements.plist'
    name = bundle.name
    if bundle.suffix == '.app':
        if 'Helper (Renderer)' in name:
            return official / 'helper-renderer-entitlements.plist'
        if 'Helper (GPU)' in name:
            return official / 'helper-gpu-entitlements.plist'
        if name.endswith(' Helper.app'):
            return official / 'helper-entitlements.plist'
    # Chromium signing/parts.py assigns no process entitlements to frameworks.
    # They are dylibs; capabilities belong to the main/helper executables.
    return None


def safe_binary(path: Path, app: Path):
    if not within(path, app) or path.is_symlink():
        raise PackageError(f'Refusing to modify non-local/symlink binary: {path}')
    path.chmod(path.stat().st_mode | stat.S_IWUSR)


def remove_sectionless_rpaths(path: Path, names: list[str]) -> dict:
    """Shrink only LC_RPATH records in a small, sectionless arm64 dylib.

    Apple's install_name_tool rejects even deletions in Chromium's sectionless
    reexport framework. Keep the file layout and every other load command byte
    unchanged; only remove requested rpath records and zero their freed space.
    The normal signing stage subsequently replaces the invalidated signature.
    """
    if path.stat().st_size > 1024 * 1024:
        raise PackageError(f'Sectionless fallback refuses large image: {path}')
    original = path.read_bytes()
    if len(original) < 32:
        raise PackageError(f'Sectionless fallback refuses short image: {path}')
    header = struct.unpack_from('<8I', original)
    magic, cpu, subtype, filetype, count, size, flags, reserved = header
    if magic != 0xFEEDFACF or cpu != 0x0100000C or filetype != 6:
        raise PackageError(f'Sectionless fallback requires thin arm64 dylib: {path}')
    if 32 + size > len(original) or count > 1024:
        raise PackageError(f'Sectionless fallback found invalid header: {path}')
    offset = 32
    kept = []
    removed = []
    segments = []
    for _ in range(count):
        command, length = struct.unpack_from('<II', original, offset)
        if length < 8 or length % 8 or offset + length > 32 + size:
            raise PackageError(f'Sectionless fallback found invalid command: {path}')
        record = original[offset:offset + length]
        if command == 0x19:  # LC_SEGMENT_64
            if length < 72:
                raise PackageError(f'Sectionless fallback found short segment: {path}')
            segment = struct.unpack_from('<II16sQQQQiiII', record)
            if segment[9] != 0:  # nsects
                raise PackageError(f'Sectionless fallback refuses sectioned dylib: {path}')
            segments.append(segment)
        remove = False
        if command == 0x8000001C:  # LC_RPATH
            start = struct.unpack_from('<I', record, 8)[0]
            if not 12 <= start < length or b'\0' not in record[start:]:
                raise PackageError(f'Sectionless fallback found malformed rpath: {path}')
            name = record[start:].split(b'\0', 1)[0].decode('utf-8')
            if name in names:
                removed.append(name)
                remove = True
        if not remove:
            kept.append(record)
        offset += length
    if offset != 32 + size or sorted(removed) != sorted(names):
        raise PackageError(f'Sectionless fallback rpaths/header differ: {path}')
    # The precise Chromium wrapper has a header-only TEXT segment followed by
    # LINKEDIT. Refuse every other layout rather than generalizing binary edits.
    if ([seg[2].rstrip(b'\0') for seg in segments] != [b'__TEXT', b'__LINKEDIT'] or
            segments[0][5] != 0 or segments[0][6] < 32 + size or
            segments[1][5] < 32 + size):
        raise PackageError(f'Sectionless fallback refuses unfamiliar layout: {path}')
    records = b''.join(kept)
    updated = bytearray(original)
    struct.pack_into('<II', updated, 16, count - len(removed), len(records))
    updated[32:32 + size] = records + bytes(size - len(records))
    if (len(updated) != len(original) or updated[:16] != original[:16] or
            updated[24:32] != original[24:32] or
            updated[32 + size:] != original[32 + size:]):
        raise PackageError(f'Sectionless fallback changed bytes outside load header: {path}')
    path.write_bytes(updated)
    return {'method': 'sectionless_arm64_rpath_removal',
            'removed_rpaths': removed, 'old_load_commands': count,
            'new_load_commands': count - len(removed),
            'old_load_command_bytes': size, 'new_load_command_bytes': len(records),
            'file_offsets_and_non_header_bytes_unchanged': True,
            'non_header_sha256_before_signing': hashlib.sha256(
                original[32 + size:]).hexdigest()}


def loader_path(image: Path, directory: Path) -> str:
    relative = os.path.relpath(directory, image.parent)
    return '@loader_path' if relative == '.' else '@loader_path/' + relative


def relocate(plan: Plan, app: Path) -> list[dict]:
    changes_report = []
    frameworks = app / 'Contents/Frameworks'
    root_cache: dict[tuple[Path, str], Path | None] = {}
    relocated_inspector = Inspector()

    def rpath_root(target: Path, name: str) -> Path | None:
        key = (target, name)
        if key not in root_cache:
            tail = name.removeprefix('@rpath/')
            candidates = dict.fromkeys([frameworks, target.parent, *target.parents])
            root_cache[key] = next((root for root in candidates
                                    if within(root, app) and
                                    (root / tail).resolve() == target.resolve()), None)
        return root_cache[key]

    for source, relative in sorted(plan.mapping.items()):
        image = app / relative
        safe_binary(image, app)
        data = plan.inspector.read(source)
        contexts = []
        source_contexts = sorted(plan.contexts[source])
        for source_exe in source_contexts:
            exe_relative = plan.mapping.get(source_exe)
            if exe_relative is None:
                raise PackageError(f'Executable context was not mapped: {source_exe}')
            contexts.append(app / exe_relative)
        if not contexts:
            raise PackageError(f'No executable context: {source}')
        changes: list[str | Path] = []
        renamed = {}
        # Keep Chromium's @rpath load names: changing hundreds of names to
        # @loader_path can exceed lld's small Mach-O header padding. Package
        # their destinations under matching roots, and relocate only rpaths.
        # Existing safe Chromium dlopen search paths are retained below.
        # System-only images need no additional component search paths.
        required_roots: set[Path] = set()
        for dep in data.dependencies:
            if system(dep.name):
                continue
            source_target = plan.edges[(source, dep.name)]
            if system(str(source_target)):
                new = str(source_target)
            else:
                target = app / plan.mapping[source_target]
                root = (rpath_root(target, dep.name)
                        if dep.name.startswith('@rpath/') else None)
                if root is not None:
                    required_roots.add(root.resolve())
                    new = dep.name
                elif all(expand(dep.name, image, exe) == target.resolve()
                         for exe in contexts):
                    new = dep.name
                else:
                    new = '@loader_path/' + os.path.relpath(target, image.parent)
            if dep.name != new:
                changes.extend(['-change', dep.name, new])
                renamed[dep.name] = new
        new_id = data.install_id
        if data.install_id:
            if (data.install_id.startswith('@rpath/') and
                    rpath_root(image, data.install_id) is not None):
                pass
            elif all(expand(data.install_id, image, exe) == image.resolve()
                     for exe in contexts):
                pass
            else:
                new_id = '@rpath/' + os.path.relpath(image, frameworks)
            if new_id != data.install_id:
                changes.extend(['-id', new_id])
        kept = []
        removed = []
        for rpath in data.rpaths:
            expanded = [expand(rpath, image, exe) for exe in contexts]
            if all(p is not None and (within(p, app) or system(str(p)))
                   for p in expanded):
                kept.append(rpath)
            else:
                removed.append(rpath)
        missing = []
        inherited_roots = []
        for root in sorted(required_roots):
            covered_locally = any(all(expand(rpath, image, exe) == root for exe in contexts)
                                  for rpath in kept)
            # dyld inherits the executable's rpaths down its loading chain.
            # Chromium's bundled SwiftShader/ANGLE libraries already use that
            # root; adding a redundant long LC_RPATH can exhaust their padding.
            covered_by_executables = all(
                any(expand(rpath, executable, executable) == root
                    for rpath in plan.inspector.read(original_exe).rpaths)
                for original_exe, executable in zip(source_contexts, contexts))
            if not covered_locally and covered_by_executables:
                inherited_roots.append(str(root.relative_to(app)))
            if not covered_locally and not covered_by_executables:
                rpath = loader_path(image, root)
                if rpath not in missing:
                    missing.append(rpath)
        replaced = {}
        # Reuse an escaping command's space where possible. No redundant
        # loader-path additions when an existing safe rpath covers the root.
        for new in missing:
            fitting = [old for old in removed if len(old.encode()) >= len(new.encode())]
            if fitting:
                old = min(fitting, key=lambda value: len(value.encode()))
                changes.extend(['-rpath', old, new])
                removed.remove(old)
                replaced[old] = new
            else:
                changes.extend(['-add_rpath', new])
            kept.append(new)
        for old in removed:
            changes.extend(['-delete_rpath', old])
        fallback = None
        if changes:
            try:
                run(['/usr/bin/install_name_tool', *changes, image])
            except PackageError as exc:
                only_deletions = (len(changes) % 2 == 0 and
                                  all(value == '-delete_rpath' for value in changes[::2]))
                if 'larger updated load commands do not fit' not in str(exc) or not only_deletions:
                    raise
                fallback = remove_sectionless_rpaths(image, changes[1::2])
        actual = relocated_inspector.read(image)
        expected_names = [renamed.get(d.name, d.name) for d in data.dependencies]
        if ([d.name for d in actual.dependencies] != expected_names or
                actual.install_id != new_id or set(actual.rpaths) != set(kept)):
            raise PackageError(f'Relocation load commands differ from plan: {image}')
        changes_report.append({'image': str(relative), 'dependencies': renamed,
                               'install_id': new_id,
                               'preserved_rpath_dependencies': sum(
                                   d.name.startswith('@rpath/') and d.name not in renamed
                                   for d in data.dependencies),
                               'removed_rpaths': removed,
                               'replaced_rpaths': replaced, 'rpaths': actual.rpaths,
                               'header_tool_fallback': fallback,
                               'roots_inherited_from_executables': inherited_roots})
    return changes_report


def signing_units(app: Path) -> tuple[list[Path], list[Path]]:
    bundles = [app]
    for directory, dirs, _ in os.walk(app, followlinks=False):
        for name in dirs:
            path = Path(directory) / name
            if not path.is_symlink() and path.suffix in BUNDLE_SUFFIXES and bundle_plist(path):
                bundles.append(path)
    owned = {details[1] for b in bundles if (details := bundle_plist(b))}
    raw = [p for p in machos(app) if p not in owned]
    # Nested code is signed first; the enclosing app is always last.
    bundles.sort(key=lambda p: len(p.parts), reverse=True)
    return raw, bundles


def remove_signing_xattrs(target: Path, app: Path) -> list[dict]:
    """Remove only Apple's two signing-blocking metadata attributes in our copy."""
    if not within(target, app):
        raise PackageError(f'Refusing xattr cleanup outside staged app: {target}')
    output = run(['/usr/bin/xattr', '-lr', target]).stdout.decode(errors='replace')
    found = re.findall(r'^(.*): (com\.apple\.(?:FinderInfo|ResourceFork)):',
                       output, flags=re.MULTILINE)
    removed = []
    for path_text, attribute in dict.fromkeys(found):
        path = Path(path_text)
        if not within(path, app) or path.is_symlink():
            raise PackageError(f'Refusing xattr cleanup outside staged regular path: {path}')
        previous = run(['/usr/bin/xattr', '-px', attribute, path]).stdout.decode().strip()
        run(['/usr/bin/xattr', '-d', attribute, path])
        removed.append({'path': str(path.relative_to(app)), 'attribute': attribute,
                        'previous_value_hex': ''.join(previous.split())})
    return removed


def sign(app: Path, official: Path, temporary: Path) -> list[dict]:
    raw, bundles = signing_units(app)
    results = []
    for index, target in enumerate(raw + bundles):
        signed, existing = signature_metadata(target)
        entitlements = dict(existing)
        profile = entitlement_profile(target, app, official)
        if profile:
            with profile.open('rb') as stream:
                defaults = plistlib.load(stream)
            # Preserve every original entitlement, and enforce official required
            # capabilities such as allow-jit and disable-library-validation.
            for name, value in defaults.items():
                if name in entitlements and entitlements[name] != value:
                    raise PackageError(f'Conflicting required entitlement {name} on {target}')
                entitlements[name] = value
        args: list[str | Path] = ['/usr/bin/codesign', '--force', '--sign', '-',
                                 '--timestamp=none']
        if signed:
            args += ['--preserve-metadata=identifier,flags,runtime']
        if entitlements:
            plist = temporary / f'entitlements-{index}.plist'
            plist.write_bytes(plistlib.dumps(entitlements))
            args += ['--entitlements', plist]
        args.append(target)
        removed_xattrs = []
        detail = run(['/usr/bin/codesign', '--display', '--verbose=2', target], check=False)
        reusable = (signed and existing == entitlements and
                    b'Signature=adhoc' in detail.stderr and
                    run(['/usr/bin/codesign', '--verify', '--strict', target], check=False).returncode == 0)
        if not reusable:
            try:
                run(args)
            except PackageError as exc:
                if 'resource fork, Finder information, or similar detritus not allowed' not in str(exc):
                    raise
                removed_xattrs = remove_signing_xattrs(target, app)
                if not removed_xattrs:
                    raise
                run(args)
            run(['/usr/bin/codesign', '--verify', '--strict', '--verbose=2', target])
        _, actual = signature_metadata(target)
        if actual != entitlements:
            raise PackageError(f'Signed entitlements differ for {target}: {actual!r}')
        results.append({'path': str(target.relative_to(app)),
                        'entitlements': actual, 'signature_verified': True,
                        'profile': profile.name if profile else None,
                        'removed_signing_xattrs': removed_xattrs,
                        'existing_adhoc_signature_reused': reusable})
    run(['/usr/bin/codesign', '--verify', '--deep', '--strict', '--verbose=2', app])
    return results


def verify_closure(app: Path, expected_targets: dict | None = None) -> dict:
    inspector = Inspector()
    image_files = machos(app)
    queue = collections.deque()
    for image in image_files:
        executable = executable_context(image, app, inspector.read(image))
        inherited = tuple(path for rpath in inspector.read(executable).rpaths
                          if (path := expand(rpath, executable, executable)) is not None)
        queue.append((image, executable, inherited if image != executable else ()))
    seen = set()
    resolved_edges = set()
    while queue:
        image, executable, inherited = queue.popleft()
        data = inspector.read(image)
        current = []
        for rpath in data.rpaths:
            path = expand(rpath, image, executable)
            if path is None or not (within(path, app) or system(str(path))):
                raise PackageError(f'External/nonrelocatable LC_RPATH: {image}: {rpath}')
            current.append(path)
        search = tuple(dict.fromkeys(tuple(current) + inherited))
        key = (image, executable, search)
        if key in seen:
            continue
        seen.add(key)
        for dep in data.dependencies:
            if system(dep.name):
                continue
            if dep.name.startswith('/'):
                raise PackageError(f'Absolute non-system load command remains: {image}: {dep.name}')
            target = resolve(dep.name, image, executable, search)
            if system(str(target)):
                continue
            if not within(target, app):
                raise PackageError(f'Dependency escapes packaged app: {image}: {dep.name}')
            if expected_targets is not None:
                edge_key = (image.relative_to(app), dep.name)
                expected = expected_targets.get(edge_key)
                if expected is None or target != (app / expected).resolve():
                    raise PackageError(f'Packaged dependency resolves differently from plan: '
                                       f'{image}: {dep.name}: {target}; expected {expected}')
            resolved_edges.add((str(image.relative_to(app)), dep.name,
                                str(target.relative_to(app))))
            queue.append((target, executable, search))
    return {'macho_count': len(image_files), 'non_system_edges': len(resolved_edges),
            'edges': [list(edge) for edge in sorted(resolved_edges)],
            'symlinks': audit_symlinks(app), 'verified': True}


def copy_into(source: Path, destination: Path):
    if destination.exists() or destination.is_symlink():
        raise PackageError(f'Refusing to overwrite copy target: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        run(['/usr/bin/ditto', '--noqtn', source, destination])
    else:
        shutil.copy2(source, destination)


def package(args) -> dict:
    source = args.source_app.resolve()
    destination = args.destination.absolute()
    if source == destination.resolve() or within(destination, source.parent):
        raise PackageError('Destination must be outside the source build directory')
    if not source.is_dir() or not bundle_plist(source):
        raise PackageError(f'Completed source app is not available: {source}')
    if destination.exists() or destination.is_symlink():
        raise PackageError(f'Destination already exists; preserve/move it explicitly first: {destination}')
    if not args.entitlements_dir.is_dir():
        raise PackageError(f'Official entitlements folder missing: {args.entitlements_dir}')
    plan = Plan(source).collect()
    report: dict[str, Any] = {
        'schema_version': 1, 'status': 'plan' if args.dry_run else 'preparing',
        'created_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'destination': str(destination), 'plan': plan.report(),
        'source_modified': False, 'runtime_launch_verified': False,
    }
    if args.dry_run:
        return report
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.component-package-', dir=destination.parent))
    stage = temporary / destination.name
    report['staging_directory'] = str(temporary)
    try:
        copy_into(source, stage)
        for original, relative in sorted(plan.copies.items()):
            copy_into(original, stage / relative)
        audit_symlinks(stage)
        report['relocations'] = relocate(plan, stage)
        renamed = {Path(item['image']): item['dependencies']
                   for item in report['relocations']}
        expected_targets = {
            (plan.mapping[image], renamed[plan.mapping[image]].get(name, name)):
                plan.mapping[target]
            for (image, name), target in plan.edges.items()
            if not system(str(target))
        }
        report['dependency_closure_before_signing'] = verify_closure(stage, expected_targets)
        report['signatures'] = sign(stage, args.entitlements_dir.resolve(), temporary)
        report['dependency_closure'] = verify_closure(stage, expected_targets)
        # Recheck after the final directory move: no staging-path assumptions.
        stage.rename(destination)
        report['dependency_closure'] = verify_closure(destination, expected_targets)
        run(['/usr/bin/codesign', '--verify', '--deep', '--strict', '--verbose=2', destination])
        report['status'] = 'complete'
        report['final_signature_verified'] = True
        report['application_bytes'] = sum(p.stat().st_size for p in files(destination))
        del report['staging_directory']
        shutil.rmtree(temporary)
        return report
    except Exception as exc:
        report['status'] = 'failed'
        report['error'] = str(exc)
        report['staging_preserved'] = str(temporary)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-app', type=Path,
                        required=True)
    parser.add_argument('--destination', type=Path,
                        required=True)
    parser.add_argument('--entitlements-dir', type=Path,
                        required=True)
    parser.add_argument('--report', type=Path,
                        required=True)
    parser.add_argument('--dry-run', action='store_true',
                        help='Resolve and print the source dependency plan; do not copy/sign/write')
    args = parser.parse_args()
    try:
        report = package(args)
        if not args.dry_run:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        print(json.dumps(report if args.dry_run else {
            'status': report['status'], 'application': str(args.destination),
            'report': str(args.report), 'macho_count': report['plan']['macho_count'],
            'runtime_launch_verified': False}, indent=2, ensure_ascii=False))
        return 0
    except (PackageError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'Packaging failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
