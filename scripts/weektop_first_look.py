"""Week tab, the top: four rough directions for the part above the final table.

Grant, 2026-09-13: "i like the week tab except for the top portion. come up with new designs
for the top while keeping the rest below it". Each phone is a new top drawn on Week 1's
real result (Grant 186, 16-4, by 7 over James), stacked on the REAL rest of the tab, cropped
from the harness screenshot of the live screen (outputs/harness/build_week/scn-now.png).

    python scripts/weektop_first_look.py
"""
from __future__ import annotations

import base64
import io
import json
import os
import subprocess

from html import escape as e

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "weektop-first-look")
TEAMS = {t["id"]: t for t in json.load(open(os.path.join(ROOT, "static", "data", "teams.json"), encoding="utf-8"))}
MODEL = json.load(open(os.path.join(ROOT, "outputs", "weektab_model.json"), encoding="utf-8"))
P = {p["name"]: p for p in MODEL["players"]}
WIN, RUN = P["Grant"], P["James"]
MARGIN = WIN["points"] - RUN["points"]


def png(tid, px=160, dark=False):
    from PIL import Image

    path = os.path.join(ROOT, "static", "logos", "%s%s.png" % (tid, "-dark" if dark else ""))
    if not os.path.exists(path):
        path = os.path.join(ROOT, "static", "logos", "%s.png" % tid)
    im = Image.open(path).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def sat(h):
    r, g, b = (int(h[k:k + 2], 16) / 255 for k in (1, 3, 5))
    mx, mn = max(r, g, b), min(r, g, b)
    light = (mx + mn) / 2
    return 0 if mx == mn else (mx - mn) / (1 - abs(2 * light - 1))


def loud(tid):
    t = TEAMS[tid]
    return max((t["bg"], t["alt"]), key=sat)


def logo(tid, size, dark=True, cls="wt-logo"):
    return '<img class="%s" src="%s" width="%d" height="%d" alt="">' % (cls, png(tid, 200, dark), size, size)


def disc(tid, size):
    t = TEAMS[tid]
    return ('<span class="wt-disc" style="width:%dpx;height:%dpx;background:%s"><img src="%s" width="%d" height="%d" alt=""></span>'
            % (size, size, t["bg"], png(tid, 96, t.get("cut") == "dark"), round(size * .72), round(size * .72)))


def header(cls):
    return ('<header class="wt-hdr %s"><div><b>Motley Pick&rsquo;em</b><span>Week 2 &middot; 20 games</span></div>'
            '<span class="wt-me">%s Grant</span></header>' % (cls, disc(WIN["team_id"], 24)))


CHEV_L = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
CHEV_R = CHEV_L.replace('M15 5l-7 7 7 7', 'M9 5l7 7-7 7')
CARET = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M6 9l6 6 6-6" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>'


# ------------------------------------------------------------------ 1: jumbotron final

def opt_jumbo():
    red = loud(WIN["team_id"])
    return (
        '<div class="o1">%s'
        '<div class="o1-nav"><span class="o1-arrow">%s</span><span class="o1-week">Week 1 %s</span><span class="o1-arrow">%s</span></div>'
        '<div class="o1-wall"><div class="o1-strip"><span>Week 1</span><span class="o1-final">Final</span><span>20/20</span></div>'
        '<div class="o1-panel" style="--t:%s">%s<span class="o1-lamp">Winner</span>'
        '<span class="o1-led o1-name"><span>%s</span></span>'
        '<div class="o1-line"><span class="o1-led o1-pts"><span>%d</span></span><span class="o1-by">by %d over %s</span></div></div></div></div>'
        % (header("o1-hdr"), CHEV_L, CARET, CHEV_R, red, logo(WIN["team_id"], 130, cls="o1-mark"), e(WIN["name"]), WIN["points"], MARGIN, e(RUN["name"])))


# ------------------------------------------------------------------ 2: final score

def opt_final():
    rows = []
    for p, won in ((WIN, True), (RUN, False)):
        c = loud(p["team_id"])
        rows.append('<div class="o2-row%s" style="--t:%s"><span class="o2-block">%s</span><span class="o2-name">%s<small>%d-%d</small></span>'
                    '<span class="o2-pts">%d</span>%s</div>'
                    % (" is-win" if won else "", c, logo(p["team_id"], 44), e(p["name"]), p["correct"], p["wrong"], p["points"],
                       '<span class="o2-w">W</span>' if won else '<span class="o2-w is-blank"></span>'))
    return (
        '<div class="o2">%s<div class="o2-stage">'
        '<div class="o2-nav"><span class="o2-arrow">%s</span><span class="o2-week">Week 1 %s</span><span class="o2-arrow">%s</span></div>'
        '<div class="o2-bug"><div class="o2-tab"><span class="o2-final">Final</span><span>Week 1</span><span class="o2-margin">by %d</span></div>%s</div>'
        '<p class="o2-caption"><b>%s wins the week.</b> Same record as %s, 7 more points where it counted.</p>'
        '</div></div>'
        % (header("o2-hdr"), CHEV_L, CARET, CHEV_R, MARGIN, "".join(rows), e(WIN["name"]), e(RUN["name"])))


# ------------------------------------------------------------------ 3: trophy

TROPHY = ('<svg class="o3-cup" viewBox="0 0 160 170" aria-hidden="true"><defs><linearGradient id="gold" x1="0" x2="1">'
          '<stop offset="0" stop-color="#9b6a12"/><stop offset=".35" stop-color="#ffe7a0"/><stop offset=".55" stop-color="#f3c343"/>'
          '<stop offset="1" stop-color="#8a5b0c"/></linearGradient></defs>'
          '<path d="M34 14h92v34c0 34-20 58-46 62-26-4-46-28-46-62Z" fill="url(#gold)"/>'
          '<path d="M34 24H12c0 26 12 40 30 44M126 24h22c0 26-12 40-30 44" fill="none" stroke="url(#gold)" stroke-width="9" stroke-linecap="round"/>'
          '<path d="M70 110h20v22H70Z" fill="url(#gold)"/><path d="M46 132h68l8 20H38Z" fill="url(#gold)"/>'
          '<rect x="30" y="152" width="100" height="16" rx="3" fill="#3b2a12"/></svg>')


def opt_trophy():
    return (
        '<div class="o3">%s<div class="o3-stage">'
        '<div class="o3-nav"><span class="o3-arrow">%s</span><span class="o3-week">Week 1 %s</span><span class="o3-arrow">%s</span></div>'
        '<div class="o3-beam"></div><div class="o3-trophy">%s<span class="o3-badge">%s</span></div>'
        '<p class="o3-kick">Week 1 champion</p><h2 class="o3-name">%s</h2>'
        '<div class="o3-plaque"><b>%d</b><span>points &middot; %d-%d &middot; by %d over %s</span></div>'
        '</div></div>'
        % (header("o3-hdr"), CHEV_L, CARET, CHEV_R, TROPHY, disc(WIN["team_id"], 42), e(WIN["name"]), WIN["points"],
           WIN["correct"], WIN["wrong"], MARGIN, e(RUN["name"])))


# ------------------------------------------------------------------ 4: the banner

def opt_banner():
    red = loud(WIN["team_id"])
    return (
        '<div class="o4" style="--t:%s">%s<div class="o4-rafters">'
        '<div class="o4-nav"><span class="o4-arrow">%s</span><span class="o4-week">Week 1 %s</span><span class="o4-arrow">%s</span></div>'
        '<div class="o4-hang"><div class="o4-banner"><span class="o4-small">Week 1</span><span class="o4-champ">Champion</span>'
        '%s<b class="o4-name">%s</b><span class="o4-pts">%d</span></div>'
        '<div class="o4-side"><p class="o4-by">By <b>%d</b><br>over %s</p><p class="o4-rec">%d-%d</p>'
        '<p class="o4-note">Hangs here until the next week is final.</p></div></div>'
        '</div></div>'
        % (red, header("o4-hdr"), CHEV_L, CARET, CHEV_R, logo(WIN["team_id"], 74, cls="o4-mark"), e(WIN["name"]), WIN["points"],
           MARGIN, e(RUN["name"]), WIN["correct"], WIN["wrong"]))


OPTIONS = [
    (1, "Jumbotron final", opt_jumbo, "The result on the same LED wall as the Board and Picks, so all three tabs are one stadium. The winner lit in their school's colors."),
    (2, "Final score", opt_final, "The week called like a game: a TV final between first and second, your points as the score, the W beside the winner."),
    (3, "Trophy", opt_trophy, "A spotlit trophy with the winner's school on it and a brass plaque underneath, the record book's trophy room in one piece."),
    (4, "The banner", opt_banner, "A championship banner hung from the rafters in the winner's colors, the way a stadium marks a title."),
]


def page():
    css = open(os.path.join(ROOT, "scripts", "weektop_first_look.css"), encoding="utf-8").read()
    fonts = ("https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,500..900;1,62..125,500..900"
             "&family=Big+Shoulders+Display:wght@700;800;900&family=Inter:wght@400;500;600;700;800&family=Alfa+Slab+One&display=swap")
    cols = "".join('<div class="col" id="c%d">%s</div>' % (n, fn()) for n, _, fn, _ in OPTIONS)
    return ('<!doctype html>\n<html lang="en"><meta charset="utf-8"><title>Week top first look</title>'
            '<link href="%s" rel="stylesheet"><style>%s</style><div class="row">%s</div>' % (fonts, css, cols))


def shoot():
    """Render the four tops at 2x, find where each one ends, and stack the real tab under it."""
    from PIL import Image, ImageDraw, ImageFont

    os.makedirs(OUT, exist_ok=True)
    html = os.path.join(OUT, "tops.html")
    open(html, "w", encoding="utf-8", newline="").write(page())
    shot = os.path.join(OUT, "tops.png")
    if os.path.exists(shot):
        os.remove(shot)
    subprocess.run(["powershell", "-NoProfile", "-File", os.path.join(ROOT, "outputs", "harness", "tools", "shot.ps1"),
                    "-In", html, "-Out", shot, "-Width", "1800", "-Height", "900", "-Scale", "2"], check=True, capture_output=True)
    tops = Image.open(shot).convert("RGB")

    live = Image.open(os.path.join(ROOT, "outputs", "harness", "build_week", "scn-now.png")).convert("RGB")
    # The final table's first row starts at y=995 in this shot, right against the hero's
    # diagonal, so the crop starts on the row and a strip of the page colour goes above it.
    start = 993
    band = Image.new("RGB", (780, 24), live.getpixel((440, 970)))
    rest = Image.new("RGB", (780, 24 + 1180))
    rest.paste(band, (0, 0))
    rest.paste(live.crop((44, start, 824, start + 1180)), (0, 24))

    labels = []
    for i, (n, name, _, what) in enumerate(OPTIONS):
        x0 = 40 + i * 860
        col = tops.crop((x0, 40, x0 + 780, tops.height))
        # each column is painted magenta below its top
        px = lambda y: col.getpixel((390, y))
        end = next(y for y in range(col.height) if px(y)[0] > 200 and px(y)[1] < 80 and px(y)[2] > 200) - 1
        labels.append((n, name, what, col.crop((0, 0, 780, end))))

    W = 4 * 780 + 5 * 60
    H = 150 + max(t.height for *_, t in labels) + rest.height + 40
    out = Image.new("RGB", (W, H), (223, 227, 232))
    d = ImageDraw.Draw(out)
    try:
        big = ImageFont.truetype("arialbd.ttf", 44)
        small = ImageFont.truetype("arial.ttf", 26)
    except OSError:
        big = small = ImageFont.load_default()
    for i, (n, name, what, top) in enumerate(labels):
        x = 60 + i * 840
        d.text((x, 30), "%d  %s" % (n, name), font=big, fill=(17, 17, 17))
        d.text((x, 88), "top is %d px tall on the phone (today %d)" % (round(top.height / 2), round((995 - 44) / 2)), font=small, fill=(70, 70, 70))
        out.paste(top, (x, 150))
        out.paste(rest, (x, 150 + top.height))
    final = os.path.join(OUT, "weektop-first-look.png")
    out = out.resize((W // 2, H // 2), Image.LANCZOS)
    out.save(final)
    print("wrote", final, out.size, "live crop starts at", start)


if __name__ == "__main__":
    shoot()
