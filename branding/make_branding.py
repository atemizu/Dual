#!/usr/bin/env python3
# Copyright 2026 Dual contributors. Dual is an unofficial derivative of Helium.
# You can use, redistribute, and/or modify this source code under
# the terms of the GPL-3.0 license that can be found in the LICENSE file.
"""Generate Dual's in-app branding in the same set and formats as Helium's
resources/branding (consumed by helium_resources / replace_resources.py).

The mark is the Dual icon's three blocks: a 3x3 staircase whose rows are,
bottom to top, navy, blue and light blue, on the icon's light gray tile.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
SOURCE_ICON = OUT / 'icon-source.png'
NAVY, BLUE, SKY, TILE = '#362979', '#227AF4', '#84D6FE', '#DDDDDD'
MONO = (60, 64, 67, 255)          # Helium's mono logo color
FONT = ('/System/Library/Fonts/HelveticaNeue.ttc', 10)  # Medium
HEADER = ('// Copyright 2026 Dual contributors. Dual is an unofficial derivative of Helium.\n'
          '// You can use, redistribute, and/or modify this source code under\n'
          '// the terms of the GPL-3.0 license that can be found in the LICENSE file.\n\n')


def blocks(x0, y0, size):
    """The three rows (rect, color) of the mark in a size x size box, y down."""
    c = size / 3
    return [((x0, y0 + 2 * c, x0 + size, y0 + size), NAVY),
            ((x0 + c, y0 + c, x0 + size, y0 + 2 * c), BLUE),
            ((x0 + 2 * c, y0, x0 + size, y0 + c), SKY)]


def staircase(x0, y0, size):
    """Outline of the mark as one polygon, y down."""
    c = size / 3
    return [(x0, y0 + size), (x0, y0 + 2 * c), (x0 + c, y0 + 2 * c), (x0 + c, y0 + c),
            (x0 + 2 * c, y0 + c), (x0 + 2 * c, y0), (x0 + size, y0), (x0 + size, y0 + size)]


def num(v):
    return f'{v:g}' if float(v).is_integer() else f'{v:.2f}f'.rstrip('0').replace('.f', 'f')


def icon_rect(x0, y0, x1, y1):
    return [f'MOVE_TO, {num(x0)}, {num(y0)},', f'LINE_TO, {num(x1)}, {num(y0)},',
            f'LINE_TO, {num(x1)}, {num(y1)},', f'LINE_TO, {num(x0)}, {num(y1)},', 'CLOSE,']


def argb(hex_color):
    h = hex_color.lstrip('#')
    return 'PATH_COLOR_ARGB, 0xFF, ' + ', '.join(f'0x{h[i:i + 2].upper()}' for i in (0, 2, 4)) + ','


def write_icons():
    # Monochrome (tinted by Chromium), 56 canvas like Helium's.
    pts = staircase(4, 4, 48)
    lines = ['CANVAS_DIMENSIONS, 56,', 'FILL_RULE_NONZERO,', f'MOVE_TO, {num(pts[0][0])}, {num(pts[0][1])},']
    lines += [f'LINE_TO, {num(x)}, {num(y)},' for x, y in pts[1:]] + ['CLOSE']
    (OUT / 'product_logo.icon').write_text(HEADER + '\n'.join(lines) + '\n')
    # Color: the gray tile with the three blocks, 256 canvas.
    lines = ['CANVAS_DIMENSIONS, 256,', 'NEW_PATH,', argb(TILE), 'ROUND_RECT, 0, 0, 256, 256, 58,']
    for (x0, y0, x1, y1), color in blocks(36, 36, 184):
        lines += ['NEW_PATH,', argb(color)] + icon_rect(x0, y0, x1, y1)
    lines[-1] = 'CLOSE'
    (OUT / 'product_logo_color.icon').write_text(HEADER + '\n'.join(lines) + '\n')


def write_svg():
    rects = ''.join(f'<rect x="{x0:g}" y="{y0:g}" width="{x1 - x0:g}" height="{y1 - y0:g}" fill="{c}"/>'
                    for (x0, y0, x1, y1), c in blocks(36, 36, 184))
    (OUT / 'product_logo.svg').write_text(
        '<svg width="256" height="256" viewBox="0 0 256 256" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="256" height="256" rx="58" fill="{TILE}"/>{rects}</svg>')


def draw_mark(size, mono=None, scale=4):
    big = Image.new('RGBA', (size * scale, size * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    if mono:
        d.polygon(staircase(0, 0, size * scale), fill=mono)
    else:
        for rect, color in blocks(0, 0, size * scale):
            d.rectangle(rect, fill=color)
    return big.resize((size, size), Image.LANCZOS)


def write_wordmarks():
    # Same layout as Helium's 280x64 wordmark: mark, then the name.
    for suffix, color in (('', (0, 0, 0, 255)), ('_white', (255, 255, 255, 255))):
        big = Image.new('RGBA', (280 * 4, 64 * 4), (0, 0, 0, 0))
        big.alpha_composite(draw_mark(54 * 4, mono=color, scale=1), (10 * 4, 5 * 4))
        font = ImageFont.truetype(FONT[0], 64 * 4, index=FONT[1])
        d = ImageDraw.Draw(big)
        # Cap height of the name matches Helium's (rows 9..54 of 64).
        top = font.getbbox('D')[1]
        cap = font.getbbox('D')[3] - top
        font = ImageFont.truetype(FONT[0], round(64 * 4 * 46 * 4 / cap), index=FONT[1])
        top = font.getbbox('D')[1]
        d.text((85 * 4, 9 * 4 - top), 'Dual', font=font, fill=color)
        img200 = big.resize((280, 64), Image.LANCZOS)
        img200.save(OUT / f'product_logo{suffix}_200.png', optimize=True)
        img200.resize((140, 32), Image.LANCZOS).save(OUT / f'product_logo{suffix}.png', optimize=True)


def write_mono_22():
    img = Image.new('RGBA', (22, 22), (0, 0, 0, 0))
    img.alpha_composite(draw_mark(18, mono=MONO), (2, 2))
    img.save(OUT / 'product_logo_22_mono.png', optimize=True)


def write_onboarding_favicon():
    # The tiled app icon: the bare mark's navy row is lost on dark tab strips.
    tile = Image.open(OUT / 'app_icon' / 'raw.png').convert('RGBA')
    tile.resize((128, 128), Image.LANCZOS).save(OUT / 'onboarding_favicon.png', optimize=True)


def write_app_icon():
    # The app icon's own artwork, with rounded corners like a macOS icon.
    src = Image.open(SOURCE_ICON).convert('RGBA').resize((1024, 1024), Image.LANCZOS)
    mask = Image.new('L', (4096, 4096), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 4095, 4095), radius=round(4096 * 0.225), fill=255)
    src.putalpha(mask.resize((1024, 1024), Image.LANCZOS))
    (OUT / 'app_icon').mkdir(exist_ok=True)
    src.save(OUT / 'app_icon' / 'raw.png', optimize=True)
    src.resize((512, 512), Image.LANCZOS).save(OUT / 'app_icon' / 'file.png', optimize=True)
    # Pre-rendered like Helium's generated/product_icon, so applying the
    # branding needs no image library.
    (OUT / 'product_icon').mkdir(exist_ok=True)
    for size in (16, 24, 32, 48, 64, 128, 256):
        src.resize((size, size), Image.LANCZOS).save(OUT / 'product_icon' / f'{size}x{size}.png', optimize=True)


def main():
    OUT.mkdir(exist_ok=True)
    write_icons()
    write_svg()
    write_wordmarks()
    write_mono_22()
    write_app_icon()
    write_onboarding_favicon()
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.suffix != '.py' and p.name != 'icon-source.png':
            print(p.relative_to(OUT), p.stat().st_size)


if __name__ == '__main__':
    main()
