"""Week tab options, rendered side by side on the real Week 1.

    node scripts/weektab_model.mjs && python scripts/build_weektab_board.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weektab_bulbs  # noqa: E402
from weektab_common import ROOT, logo_css  # noqa: E402

import weektab_opt1, weektab_opt2, weektab_opt3, weektab_opt4, weektab_opt5  # noqa: E402,E401

OPTIONS = [
    (1, "Scoreboard", weektab_opt1, "weektab_opt1.css"),
    (2, "Winner's colors", weektab_opt2, "weektab_opt2.css"),
    (3, "Banner night", weektab_opt3, "weektab_opt3.css"),
    (4, "Trading cards", weektab_opt4, "weektab_opt4.css"),
    (5, "Stat sheet", weektab_opt5, "weektab_opt5.css"),
]
OUT = os.path.join(ROOT, "outputs", "weektab-board.html")


def read(name):
    path = os.path.join(ROOT, "scripts", name)
    return open(path, encoding="utf-8").read() if os.path.exists(path) else None


def build(only=None):
    css, phones = [read("weektab_base.css")], []
    for n, name, mod, sheet in OPTIONS:
        if only and n not in only:
            continue
        style = read(sheet)
        if style is None:
            continue
        css.append(style)
        phones.append('<figure class="bd-opt" id="opt-%d"><figcaption><b>%d</b> %s</figcaption>%s</figure>'
                      % (n, n, name, mod.build()))
    fonts = ("https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,400..900;1,62..125,400..900"
             "&family=Inter:wght@400;500;600;700;800&family=Graduate&family=Courier+Prime:wght@400;700&display=swap")
    return ('<!doctype html>\n<html lang="en"><meta charset="utf-8"><title>Week Tab Picks</title>'
            '<link href="%s" rel="stylesheet"><style>%s\n%s\n'
            'body{margin:0;background:#dfe3e8;font-family:var(--ui)}'
            '.bd-row{display:flex;gap:32px;align-items:flex-start;padding:24px}'
            '.bd-opt{margin:0}.bd-opt figcaption{margin:0 0 10px 6px;font:800 22px var(--display);color:#111}'
            '.bd-opt figcaption b{display:inline-grid;place-items:center;width:34px;height:34px;margin-right:6px;border-radius:50%%;background:#111;color:#fff}'
            '</style>%s<div class="bd-row">%s</div><pre id="measure"></pre>'
            '<script>setTimeout(function(){document.getElementById("measure").textContent=JSON.stringify('
            '[].map.call(document.querySelectorAll(".wt-phone"),function(p){var r=p.getBoundingClientRect();'
            'return [Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]}))},2500)</script>'
            % (fonts, logo_css(), "\n".join(css), weektab_bulbs.defs(), "".join(phones)))


if __name__ == "__main__":
    page = build()
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        fh.write(page)
    print("wrote %s (%.0f KB)" % (OUT, len(page.encode()) / 1024))
