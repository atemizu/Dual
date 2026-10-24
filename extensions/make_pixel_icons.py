#!/usr/bin/env python3
"""Make an extension's icons from a pixel drawing.

The drawing is made of equal squares on a white (or clear) ground. The icons
keep only the drawing, on a clear ground, and draw every square as a whole
number of pixels so the edges stay sharp. Each square keeps its own colour.

  make_pixel_icons.py <drawing.png> <icons directory> [size=pixels-per-square ...]

Without the last arguments, every icon uses the most pixels per square that
fit: 16, 32, 48 and 128 pixel icons. A drawing with more squares than an icon
has pixels is shrunk to fit that icon instead, which softens its edges.
"""
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

SIZES = (16, 32, 48, 128)


def is_ink(pixel):
    red, green, blue, alpha = pixel
    return alpha > 127 and red + green + blue < 720


def read_squares(drawing):
    """The drawing as rows of squares: a colour, or None where nothing is drawn."""
    pixels = drawing.load()
    ink = [(x, y) for y in range(drawing.height) for x in range(drawing.width) if is_ink(pixels[x, y])]
    left, top = min(x for x, _ in ink), min(y for _, y in ink)
    right, bottom = max(x for x, _ in ink), max(y for _, y in ink)

    def runs(lines):
        return [len(run) for line in lines for run in ''.join('#' if on else ' ' for on in line).split()]

    rows = [[is_ink(pixels[x, y]) for x in range(left, right + 1)] for y in range(top, bottom + 1)]
    columns = [[is_ink(pixels[x, y]) for y in range(top, bottom + 1)] for x in range(left, right + 1)]
    # The shortest run of drawn pixels, across or down, is one square.
    side = min(runs(rows) + runs(columns))
    assert (right - left + 1) % side == 0 and (bottom - top + 1) % side == 0, 'the drawing is not on a grid'
    squares = []
    for row in range((bottom - top + 1) // side):
        line = []
        for column in range((right - left + 1) // side):
            inside = [pixels[left + column * side + dx, top + row * side + dy]
                      for dx in range(side) for dy in range(side)]
            drawn = [pixel[:3] for pixel in inside if is_ink(pixel)]
            # Slight noise in the source is not a colour of its own.
            line.append(Counter(drawn).most_common(1)[0][0] if len(drawn) * 2 > len(inside) else None)
        squares.append(line)
    return squares


def merge_near_colours(squares):
    """Squares whose colours differ only by noise get one colour."""
    counts = Counter(colour for line in squares for colour in line if colour)
    palette = []
    for colour, _ in counts.most_common():
        if not any(sum(abs(a - b) for a, b in zip(colour, known)) < 24 for known in palette):
            palette.append(colour)

    def nearest(colour):
        return min(palette, key=lambda known: sum(abs(a - b) for a, b in zip(colour, known)))

    return [[nearest(colour) if colour else None for colour in line] for line in squares], palette


def icon(squares, size, pixels_per_square):
    rows, columns = len(squares), len(squares[0])
    assert columns * pixels_per_square <= size and rows * pixels_per_square <= size, 'does not fit'
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    left = (size - columns * pixels_per_square) // 2
    top = (size - rows * pixels_per_square) // 2
    for row in range(rows):
        for column in range(columns):
            colour = squares[row][column]
            if colour:
                x, y = left + column * pixels_per_square, top + row * pixels_per_square
                image.paste(colour + (255,), (x, y, x + pixels_per_square, y + pixels_per_square))
    return image


def shrunk_icon(squares, size):
    """The whole drawing in fewer pixels than it has squares."""
    across = max(len(squares), len(squares[0]))
    # Colour is weighted by coverage, so the clear ground does not darken the edges.
    large = icon(squares, across * 8, 8).convert('RGBa')
    return large.resize((size, size), Image.BOX).convert('RGBA')


def main():
    drawing, out = Path(sys.argv[1]), Path(sys.argv[2])
    chosen = dict((int(size), int(pixels)) for size, pixels in (arg.split('=') for arg in sys.argv[3:]))
    squares, palette = merge_near_colours(read_squares(Image.open(drawing).convert('RGBA')))
    rows, columns = len(squares), len(squares[0])
    print(f'{drawing.name}: {columns} x {rows} squares, colours {palette}')
    marks = {colour: mark for colour, mark in zip(palette, ('██', '▒▒', '░░', '::'))}
    for line in squares:
        print('  ' + ''.join(marks.get(colour, '??') if colour else '  ' for colour in line))
    out.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        pixels_per_square = chosen.get(size, size // max(rows, columns))
        if pixels_per_square < 1:
            shrunk_icon(squares, size).save(out / f'{size}.png')
            print(f'  {size}.png: shrunk to fit ({size / max(rows, columns):.2f} px per square)')
            continue
        icon(squares, size, pixels_per_square).save(out / f'{size}.png')
        print(f'  {size}.png: {pixels_per_square} px per square, '
              f'drawing {columns * pixels_per_square} x {rows * pixels_per_square}')


if __name__ == '__main__':
    main()
