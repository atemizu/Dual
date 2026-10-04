#!/usr/bin/env python3
# Copyright 2026 Dual contributors. Dual is an unofficial derivative of Helium.
# You can use, redistribute, and/or modify this source code under
# the terms of the GPL-3.0 license that can be found in the LICENSE file.
"""Show Dual's name and logo instead of Helium's inside the app.

Run on a Helium source tree after Helium's own preparation (which puts
Helium's name and logo in place of Chromium's) and after applying
helium-dual-window.patch:

    python3 dual_rebrand.py <src> [--branding DIR] [--dry-run]

1. UI strings. "Helium" naming the browser becomes "Dual" in .grd/.grdp
   messages and in their .xtb translations. Helium itself keeps its name:
   Helium services and servers (Dual still uses them), "The Helium Authors",
   "The Helium Projects", the Helium Partner program and "verified by Helium".
2. The About page says Dual is an unofficial build based on Helium.
3. Product logos: Dual's mark replaces Helium's at the paths Helium's own
   branding step (helium_resources.txt) writes.

It reuses Helium's name substitution helpers for message fingerprints, so
translations stay attached to their rewritten English messages.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as xml

HERE = Path(__file__).resolve().parent

# Platforms and channels a macOS Chromium-branded build does not compile.
SKIP_PARTS = {'out', '.pc', 'ios', 'android', 'chromeos', 'ash', 'remoting',
              'testdata', 'node_modules', 'devtools-frontend'}
SKIP_NAME = re.compile(r'google_chrome|chromeos|os_settings_strings|android')

WORD = re.compile(r'\bHelium\b')
# English: Helium's own services, authors and projects keep the name.
KEEP_AFTER_EN = re.compile(
    r' (?:services?|Services|servers?|Authors|Projects?|open source project|Partners?)\b')
# Helium's partner program supports Helium's development; its vetting is Helium's.
KEEP_BEFORE_EN = re.compile(r'(?:verified by|development of) $')
# Japanese renders "Helium services" as "Helium サービス".
KEEP_AFTER_JA = re.compile(r' ?(?:の)?(?:サービス|サーバー|サーバ|Authors|プロジェクト|パートナー|開発)')

# Messages rewritten outright. English replaces the leading text of the
# message; Japanese is the full .xtb translation body.
REWRITES = {
    'IDS_VERSION_UI_OFFICIAL': {
        'en': 'Unofficial Build',
        'ja': '非公式ビルド',
    },
    'IDS_SETTINGS_ABOUT_PAGE_BROWSER_VERSION': {
        'en': 'Based on Helium ',
        'ja': ('Helium <ph name="HELIUM_PRODUCT_VERSION" /> ベース (<ph name="PRODUCT_CHANNEL" />、'
               '<ph name="CHROMIUM_NAME" /> <ph name="PRODUCT_VERSION" /><ph name="PRODUCT_VERSION_SUFFIX" />) '
               '<ph name="PRODUCT_MODIFIER" /> <ph name="PRODUCT_VERSION_BITS" />'),
    },
    'IDS_VERSION_UI_LICENSE': {
        'en': 'Dual, an unofficial derivative of Helium, is made possible by the ',
        'ja': ('Dual は Helium の非公式な派生版で、<ph name="BEGIN_LINK_CHROMIUM" />Chromium'
               '<ph name="END_LINK_CHROMIUM" /> オープンソース プロジェクトやその他の'
               '<ph name="BEGIN_LINK_OSS" />オープンソース ソフトウェア<ph name="END_LINK_OSS" />'
               'によって実現しました。'),
    },
}

# Helium's branding destinations (helium-chromium resources/helium_resources.txt).
BRANDING_FILES = {
    'product_logo.png': ['components/resources/default_100_percent/chromium/product_logo.png'],
    'product_logo_white.png': ['components/resources/default_100_percent/chromium/product_logo_white.png'],
    'product_logo_200.png': ['components/resources/default_200_percent/chromium/product_logo.png'],
    'product_logo_white_200.png': ['components/resources/default_200_percent/chromium/product_logo_white.png'],
    'product_logo_22_mono.png': ['chrome/app/theme/chromium/product_logo_22_mono.png'],
    'product_logo.svg': ['chrome/app/theme/chromium/product_logo.svg'],
    'product_logo.icon': [
        'chrome/app/vector_icons/browser_logo.icon',
        'chrome/app/vector_icons/browser_logo_old.icon',
        'chrome/app/vector_icons/chrome_product.icon',
        'components/omnibox/browser/vector_icons/chrome_product.icon',
        'components/omnibox/browser/vector_icons/product_chrome_refresh.icon',
        'components/omnibox/browser/vector_icons/product_chrome_refresh_old.icon',
        'components/omnibox/browser/vector_icons/product_old.icon',
        'components/vector_icons/chromium/product.icon',
        'ui/message_center/vector_icons/chrome_product.icon',
        'ui/message_center/vector_icons/product_old.icon',
    ],
    'product_logo_color.icon': ['components/vector_icons/chromium/product_refresh.icon'],
    'onboarding_favicon.png': ['components/helium_onboarding/public/favicon.png'],
}
# Product icon sizes, pre-rendered in branding/product_icon from app_icon/raw.png
# (helium-chromium resources/generate_resources.txt + helium_resources.txt).
PRODUCT_ICONS = [
    (16, 'chrome/app/theme/chromium/product_logo_16.png'),
    (24, 'chrome/app/theme/chromium/product_logo_24.png'),
    (48, 'chrome/app/theme/chromium/product_logo_48.png'),
    (64, 'chrome/app/theme/chromium/product_logo_64.png'),
    (128, 'chrome/app/theme/chromium/product_logo_128.png'),
    (256, 'chrome/app/theme/chromium/product_logo_256.png'),
    (16, 'chrome/app/theme/default_100_percent/chromium/product_logo_16.png'),
    (32, 'chrome/app/theme/default_100_percent/chromium/product_logo_32.png'),
    (32, 'chrome/app/theme/default_200_percent/chromium/product_logo_16.png'),
    (64, 'chrome/app/theme/default_200_percent/chromium/product_logo_32.png'),
]


def message_files(src, exts):
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        dirs[:] = [d for d in dirs if d not in SKIP_PARTS and not d.startswith('.')]
        if SKIP_PARTS.intersection(rel.parts):
            continue
        for name in files:
            if name.rsplit('.', 1)[-1] in exts and not SKIP_NAME.search(name):
                yield Path(root) / name


def rename(text, keep_after, keep_before=None):
    def sub(match):
        if keep_after.match(text, match.end()):
            return match.group(0)
        if keep_before and keep_before.search(text[max(0, match.start() - 20):match.start()]):
            return match.group(0)
        return 'Dual'
    return WORD.sub(sub, text)


def rename_element(elem, keep_after, keep_before=None):
    """Renames in an element's text, its children and their tails."""
    changed = False
    if elem.text:
        new = rename(elem.text, keep_after, keep_before)
        changed |= new != elem.text
        elem.text = new
    for child in elem:
        changed |= rename_element(child, keep_after, keep_before)
        if child.tail:
            new = rename(child.tail, keep_after, keep_before)
            changed |= new != child.tail
            child.tail = new
    return changed


def full_text(elem):
    return ''.join(elem.itertext())


def visible_text(elem):
    """Message text without placeholder contents such as <ex> samples."""
    parts = [elem.text or '']
    for child in elem:
        if child.tag != 'ph':
            parts.append(visible_text(child))
        parts.append(child.tail or '')
    return ''.join(parts)


def substitute_grd(path, util, dry_run):
    """Returns {old_fp: (new_fp, kind)} for messages whose text changed.
    kind is 'all' when every Helium became Dual, 'some' otherwise, or a
    REWRITES key."""
    original = path.read_text(encoding='utf-8')
    text = original.replace('&#36;', '!!dollar-sign-literal!!')
    if 'Helium' not in text and not any(f'"{n}"' in text for n in REWRITES):
        return {}
    tree = xml.fromstring(text, util.get_parser())
    fp_map = {}
    for message in tree.iter('message'):
        name = message.get('name')
        if name in REWRITES:
            old_fp = util.compute_fp(message)
            prefix = REWRITES[name]['en']
            if name == 'IDS_VERSION_UI_OFFICIAL':
                message.text = message.text.replace('Official Build', prefix)
            elif name == 'IDS_SETTINGS_ABOUT_PAGE_BROWSER_VERSION':
                message.text = message.text.replace('Version ', prefix, 1)
            elif name == 'IDS_VERSION_UI_LICENSE':
                message.text = message.text.replace('Helium is made possible by the ', prefix, 1)
            new_fp = util.compute_fp(message)
            if new_fp != old_fp:
                fp_map[old_fp] = (new_fp, name)
            continue
        if 'Helium' not in full_text(message):
            continue
        old_fp = util.compute_fp(message)
        if not rename_element(message, KEEP_AFTER_EN, KEEP_BEFORE_EN):
            continue
        new_fp = util.compute_fp(message)
        kind = 'some' if 'Helium' in visible_text(message) else 'all'
        if new_fp != old_fp:
            fp_map[old_fp] = (new_fp, kind)
    if fp_map and not dry_run:
        # Keep the file's own form: some parsers take the first node as root.
        out = xml.tostring(tree, encoding='unicode',
                           xml_declaration=original.lstrip().startswith('<?xml'))
        path.write_text(out.replace('!!dollar-sign-literal!!', '&#36;'), encoding='utf-8')
    return fp_map


def xtb_lang(path):
    return path.stem.rsplit('_', 1)[-1]


def substitute_xtb(path, fp_map, util, dry_run):
    original = path.read_text(encoding='utf-8')
    text = original.replace('&#36;', '!!dollar-sign-literal!!')
    tree = xml.fromstring(text, util.get_parser())
    lang = xtb_lang(path)
    changed = False
    seen = set()
    for translation in tree.iter('translation'):
        entry = fp_map.get(translation.get('id'))
        if entry:
            new_fp, kind = entry
            if kind in REWRITES:
                if lang == 'ja':
                    body = xml.fromstring(f'<translation>{REWRITES[kind]["ja"]}</translation>')
                    translation.text = body.text
                    translation[:] = list(body)
                else:
                    # Other languages fall back to the new English text.
                    new_fp = None
            elif kind == 'all':
                rename_element(translation, re.compile(r'(?!)'))
            elif lang == 'ja':
                rename_element(translation, KEEP_AFTER_JA)
            # Mixed messages in other languages keep their wording.
            if new_fp:
                translation.set('id', new_fp)
            else:
                translation.set('id', 'dual-dropped-' + translation.get('id'))
            changed = True
        util.dedup_translations_in_place(translation, seen)
    if not changed:
        return False
    # Drop translations whose English message was rewritten (marked above).
    for parent in tree.iter():
        for child in list(parent):
            if child.tag == 'translation' and child.get('id', '').startswith('dual-dropped-'):
                parent.remove(child)
    if not dry_run:
        out = xml.tostring(tree, encoding='unicode',
                           xml_declaration=original.lstrip().startswith('<?xml'))
        path.write_text(out.replace('!!dollar-sign-literal!!', '&#36;'), encoding='utf-8')
    return True


def copy_branding(src, branding, dry_run):
    count = 0
    for name, destinations in BRANDING_FILES.items():
        data = (branding / name).read_bytes()
        for dest in destinations:
            target = src / dest
            if not target.parent.is_dir():
                raise FileNotFoundError(f'missing destination directory for {dest}')
            # Leave identical files untouched so builds see no change.
            if target.exists() and target.read_bytes() == data:
                continue
            if not dry_run:
                target.write_bytes(data)
            count += 1
    for size, dest in PRODUCT_ICONS:
        data = (branding / 'product_icon' / f'{size}x{size}.png').read_bytes()
        if (src / dest).exists() and (src / dest).read_bytes() == data:
            continue
        if not dry_run:
            (src / dest).write_bytes(data)
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('src', type=Path)
    parser.add_argument('--branding', type=Path, default=HERE / 'branding')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    src = args.src.resolve()
    if not (src / 'chrome' / 'app' / 'chromium_strings.grd').exists():
        raise SystemExit(f'{src} is not a Chromium source tree')

    sys.path.insert(0, str(src.parent.parent / 'helium-chromium' / 'utils'))
    import name_substitution_utils as util  # pylint: disable=import-error
    util.add_grit_to_path(src)

    fp_map = {}
    grd_count = 0
    for path in message_files(src, {'grd', 'grdp'}):
        changed = substitute_grd(path, util, args.dry_run)
        if changed:
            grd_count += 1
            fp_map.update(changed)
    xtb_count = sum(substitute_xtb(path, fp_map, util, args.dry_run)
                    for path in message_files(src, {'xtb'}))
    kinds = {}
    for _, kind in fp_map.values():
        kinds[kind] = kinds.get(kind, 0) + 1
    print(f'messages: {len(fp_map)} {kinds}; grd files: {grd_count}; xtb files: {xtb_count}')
    print(f'branding files written: {copy_branding(src, args.branding, args.dry_run)}')


if __name__ == '__main__':
    main()
