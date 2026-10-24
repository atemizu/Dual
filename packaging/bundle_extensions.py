#!/usr/bin/env python3
"""Copy Dual's bundled extensions into an app bundle.

  bundle_extensions.py <extensions dir> <Dual app> <Dual version>
                       [--hosts <dir>] [name ...]

Each extension goes to Contents/Resources/Dual Extensions/<extension id>/,
where Dual looks for it at launch. The id comes from the "key" in the
extension's manifest. An extension with a build.json is told which Dual
release it ships in. With names given, only those extensions are bundled.

An extension with a native_host.json comes with a program of its own (a
native messaging host). The program, built beforehand, is taken from the
--hosts directory, with its licenses (the directory <program>-licenses next
to it), and goes to Contents/Resources/Dual Native Hosts/ with a manifest
that lets only that extension start it. Dual looks for its hosts there first.

Run before the app is signed.
"""
import argparse, base64, hashlib, json, shutil
from pathlib import Path


def extension_id(manifest):
    digest = hashlib.sha256(base64.b64decode(manifest['key'])).hexdigest()[:32]
    return ''.join(chr(ord('a') + int(c, 16)) for c in digest)


def add_host(directory, ident, hosts_source, hosts_target):
    """Puts the program an extension needs next to its manifest."""
    host = json.loads((directory / 'native_host.json').read_text(encoding='utf-8'))
    program = Path(hosts_source or '') / host['program']
    if not hosts_source or not program.is_file():
        raise SystemExit(f'{directory.name} needs {host["program"]}: build it and pass --hosts')
    hosts_target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(program, hosts_target / program.name)
    licenses = program.with_name(program.name + '-licenses')
    if licenses.is_dir():
        shutil.copytree(licenses, hosts_target / licenses.name)
    manifest = {
        'name': host['name'],
        'description': host['description'],
        # By file name: Dual finds it next to this manifest.
        'path': program.name,
        'type': 'stdio',
        'allowed_origins': [f'chrome-extension://{ident}/'],
    }
    (hosts_target / f'{host["name"]}.json').write_text(json.dumps(manifest, indent=2) + '\n')


def bundle(source, app, version, only=None, hosts=None):
    target = Path(app) / 'Contents/Resources/Dual Extensions'
    hosts_target = Path(app) / 'Contents/Resources/Dual Native Hosts'
    for old in (target, hosts_target):
        if old.exists():
            shutil.rmtree(old)
    bundled = {}
    for directory in sorted(p for p in Path(source).iterdir() if (p / 'manifest.json').is_file()):
        if only and directory.name not in only:
            continue
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        ident = extension_id(manifest)
        shutil.copytree(directory, target / ident,
                        ignore=shutil.ignore_patterns('.*', 'native_host.json'))
        if (target / ident / 'build.json').exists():
            (target / ident / 'build.json').write_text(json.dumps({'dual': version}) + '\n')
        if (directory / 'native_host.json').is_file():
            add_host(directory, ident, hosts, hosts_target)
        bundled[directory.name] = ident
    return bundled


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('extensions')
    parser.add_argument('app')
    parser.add_argument('version')
    parser.add_argument('--hosts')
    parser.add_argument('only', nargs='*')
    args = parser.parse_args()
    print(json.dumps(bundle(args.extensions, args.app, args.version, args.only, args.hosts)))
