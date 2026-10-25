#!/usr/bin/env python3
"""Copy Dual's bundled extensions next to the Linux program.

  bundle_extensions_linux.py <extensions dir> <program dir> <Dual version> [--hosts <dir>]

Each extension goes to <program dir>/dual-extensions/<extension id>/, where
Dual for Linux looks for it at launch (helium_dual_bundled_extensions_linux.cc);
otherwise as packaging/bundle_extensions.py does for the macOS app. An
extension with a native_host.json gets its program (built beforehand, in
--hosts) in <program dir>/dual-native-hosts/, with a manifest that lets only
that extension start it.
"""
import argparse, base64, hashlib, json, shutil
from pathlib import Path


def extension_id(manifest):
    digest = hashlib.sha256(base64.b64decode(manifest['key'])).hexdigest()[:32]
    return ''.join(chr(ord('a') + int(c, 16)) for c in digest)


def add_host(directory, ident, hosts_source, hosts_target):
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
        'path': program.name,
        'type': 'stdio',
        'allowed_origins': [f'chrome-extension://{ident}/'],
    }
    (hosts_target / f'{host["name"]}.json').write_text(json.dumps(manifest, indent=2) + '\n')


parser = argparse.ArgumentParser()
parser.add_argument('extensions')
parser.add_argument('program')
parser.add_argument('version')
parser.add_argument('--hosts')
args = parser.parse_args()
source, program = Path(args.extensions), Path(args.program)
target, hosts_target = program / 'dual-extensions', program / 'dual-native-hosts'
for old in (target, hosts_target):
    if old.exists():
        shutil.rmtree(old)
bundled = {}
for directory in sorted(p for p in source.iterdir() if (p / 'manifest.json').is_file()):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    ident = extension_id(manifest)
    shutil.copytree(directory, target / ident, ignore=shutil.ignore_patterns('.*', 'native_host.json'))
    if (target / ident / 'build.json').exists():
        (target / ident / 'build.json').write_text(json.dumps({'dual': args.version}) + '\n')
    if (directory / 'native_host.json').is_file():
        add_host(directory, ident, args.hosts, hosts_target)
    bundled[directory.name] = ident
print(json.dumps(bundled))
