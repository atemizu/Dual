#!/usr/bin/env python3
"""Is there a Helium release newer than the one Dual is based on?

  check_upstream.py [source-lock.json]

Prints both versions. Exit status: 0 when Dual's base is the latest release,
1 when a newer one exists, 2 when the answer could not be obtained.
Reads only the public release list of imputnet/helium-macos.
"""
import json, ssl, sys, urllib.request
from pathlib import Path

RELEASES = 'https://api.github.com/repos/imputnet/helium-macos/releases?per_page=30'


def version_key(tag):
    return tuple(int(part) for part in tag.split('.'))


def latest_release():
    """The newest full release: (tag, date)."""
    request = urllib.request.Request(RELEASES, headers={'Accept': 'application/vnd.github+json'})
    # A python.org Python on macOS has no certificate store of its own.
    system_store = '/etc/ssl/cert.pem'
    context = ssl.create_default_context(cafile=system_store if Path(system_store).exists() else None)
    with urllib.request.urlopen(request, timeout=30, context=context) as response:
        releases = json.load(response)
    full = [r for r in releases if not r['prerelease'] and not r['draft']
            and all(part.isdigit() for part in r['tag_name'].split('.'))]
    newest = max(full, key=lambda r: version_key(r['tag_name']))
    return newest['tag_name'], newest['published_at'][:10]


def base_version(lock_path):
    return json.loads(Path(lock_path).read_text())['helium_macos']['tag']


def main():
    lock = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / 'source-lock.json'
    base = base_version(lock)
    try:
        latest, date = latest_release()
    except Exception as error:  # noqa: BLE001
        print(f'Dual is based on Helium {base}. The release list could not be read: {error}')
        return 2
    if version_key(latest) > version_key(base):
        print(f'Dual is based on Helium {base}. Helium {latest} was released on {date}.')
        return 1
    print(f'Dual is based on Helium {base}, the latest release ({date}).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
