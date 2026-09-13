"""Incandescent bulb lettering for option 1 of the Week tab board, the stadium scoreboard.

Every character is a module of 5 by 7 bulbs (the period is 2 by 7), drawn as inline SVG
that points at symbols defined once per page: `#wb-off5` / `#wb-off2` are the dim unlit
bulbs of a whole module, `#wb-<code>` the lit ones. So a number costs a few <use>
elements however many times it appears, and the glow sits on the lit layer only.

Glyphs follow the classic 5x7 character ROM, with a plain zero: on a scoreboard a zero is
never mistaken for an O.
"""
from __future__ import annotations

GLYPHS = {
    "0": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
    "A": [".###.", "#...#", "#...#", "#...#", "#####", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
    "Y": ["#...#", "#...#", "#...#", ".#.#.", "..#..", "..#..", "..#.."],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    ".": ["..", "..", "..", "..", "..", "##", "##"],
}

PITCH = 10      # user units between bulb centres
R_ON = 3.9
R_OFF = 3.0
GAP = 1         # blank columns between modules
SPACE = 3       # columns for a space: no module, no bulbs


def code(ch):
    return {"+": "plus", "-": "dash", ".": "dot"}.get(ch, ch)


def defs():
    """The hidden <svg> every bulb string on the page points at. Emit once."""
    def dots(rows, r, only_lit):
        out = []
        for y, row in enumerate(rows):
            for x, cell in enumerate(row):
                if only_lit and cell != "#":
                    continue
                out.append('<circle cx="%g" cy="%g" r="%g"/>' % (x * PITCH + PITCH / 2, y * PITCH + PITCH / 2, r))
        return "".join(out)

    parts = [
        '<symbol id="wb-off5" overflow="visible">%s</symbol>' % dots(["#####"] * 7, R_OFF, False),
        '<symbol id="wb-off2" overflow="visible">%s</symbol>' % dots(["##"] * 7, R_OFF, False),
    ]
    for ch, rows in GLYPHS.items():
        parts.append('<symbol id="wb-%s" overflow="visible">%s</symbol>' % (code(ch), dots(rows, R_ON, True)))
    glow = ('<filter id="wb-glow" x="-20%" y="-20%" width="140%" height="140%">'
            '<feGaussianBlur stdDeviation="2.4" result="b"/>'
            '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    return ('<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>%s%s</defs></svg>'
            % (glow, "".join(parts)))


def width_cols(text):
    cols = 0
    for i, ch in enumerate(text):
        if ch == " ":
            cols += SPACE
            continue
        cols += len(GLYPHS[ch][0])
        if i < len(text) - 1 and text[i + 1] != " ":
            cols += GAP
    return cols


def bulbs(text, height, cls="", label=None, align="left", cols=None):
    """Inline SVG for `text` in bulbs, `height` CSS px tall (7 bulbs). `cols` pads the
    string to a fixed module count, right-aligned, so a column of numbers lines up the way
    a scoreboard's digit modules do: unused modules stay dark rather than disappearing."""
    text = str(text).upper()
    pad = 0
    if cols is not None:
        pad = max(0, cols - len(text))
    off, on, x = [], [], 0
    for _ in range(pad):
        off.append('<use href="#wb-off5" x="%d"/>' % x)
        x += (5 + GAP) * PITCH
    for i, ch in enumerate(text):
        if ch == " ":
            x += SPACE * PITCH
            continue
        w = len(GLYPHS[ch][0])
        off.append('<use href="#wb-off%d" x="%d"/>' % (w, x))
        on.append('<use href="#wb-%s" x="%d"/>' % (code(ch), x))
        x += w * PITCH
        if i < len(text) - 1 and text[i + 1] != " ":
            x += GAP * PITCH
    vw, vh = x, 7 * PITCH
    return ('<svg class="wb %s" viewBox="-2 -2 %d %d" width="%.1f" height="%d" role="img" aria-label="%s">'
            '<g class="wb-off">%s</g><g class="wb-on" filter="url(#wb-glow)">%s</g></svg>'
            % (cls, vw + 4, vh + 4, height * (vw + 4) / (vh + 4), height, label or text,
               "".join(off), "".join(on)))
