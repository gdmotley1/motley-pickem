"""Build the team list the phone uses to pick a profile picture.

    python scripts/build_team_library.py        # -> static/data/teams.json
    python scripts/build_team_library.py --check

Grant chose "team mark on that school's own colour" from outputs/avatar-board.html on
2026-09-04. The board flagged the one weakness of that choice in its own caption: the
contrast is out of your hands, because it is whatever the school's brand happens to be.

That is not hypothetical. A school whose mark is drawn in its own primary colour, on a
disc of that same primary colour, is a solid blob. So rather than ship the flaw, every
logo is measured here against its school's colours and the background is chosen to be the
one the mark actually shows up on:

  1. the school's primary, if enough of the mark stands clear of it
  2. otherwise the school's alternate
  3. otherwise a neutral, dark or light, whichever the mark stands clear of

`bg` in the output is the answer, and `bg_from` records which rule produced it so a
surprising avatar can be explained without rerunning anything.

The mark is judged on the pixels that are actually drawn: fully transparent pixels are
ignored, since a logo is mostly empty space.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FBS = os.path.join(ROOT, "inputs", "fbs_teams.json")
EXTRA = os.path.join(ROOT, "inputs", "extra_teams.json")
LOGO_DIR = os.path.join(ROOT, "static", "logos")
OUT = os.path.join(ROOT, "static", "data", "teams.json")

# Anything closer than this in RGB space reads as the same colour at 22px.
TOO_CLOSE = 70
# The bar for `alt`, which is a solid block butted against the solid disc rather than a
# mark drawn on top of one. Two flat areas separate at a far smaller difference than a
# logo does, so reusing TOO_CLOSE here rejected Georgia College's own green at a
# distance of 68 and left Grant's alma mater with no block colour at all.
ALT_TOO_CLOSE = 40
# The scorebug's chrome, and the contrast a colour block has to reach against it to read
# as a block at all. Two of the four schools on the current roster carry black as their
# second colour: Kennesaw's #0b1315 scored 1.02 against this and Georgia's #2c2a29 scored
# 1.28, measured in the harness on 2026-09-10, which is to say they were not there. A
# school's black is still its black; it just has to be lifted far enough off the chrome to
# be seen, the way a broadcast graphic never puts true black on a black bug.
BUG_CHROME = (16, 21, 28)
MIN_BLOCK_CONTRAST = 1.7
# If more than this share of the drawn mark blends into the background, reject it.
MAX_BLEND = 0.34
# The last resort, when neither school colour can host the mark. Two polarities, not
# one: the first cut of this used only the dark slate, and a mark that is itself dark
# (Army, Colorado's buffalo, Texas State) came out as a near-invisible smudge. Whichever
# of the two the mark stands clear of wins.
NEUTRALS = [("#28313d", "neutral"), ("#eef1f5", "neutral light")]


def hex_rgb(value: str):
    v = (value or "").lstrip("#")
    if len(v) != 6:
        return None
    try:
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def blend_share(pixels, bg) -> float:
    """Share of the drawn mark that would disappear against this background."""
    if not pixels:
        return 1.0
    br, bg_, bb = bg
    close = sum(1 for (r, g, b, n) in pixels
                if ((r - br) ** 2 + (g - bg_) ** 2 + (b - bb) ** 2) ** 0.5 < TOO_CLOSE
                for _ in range(n))
    total = sum(n for *_, n in pixels)
    return close / total


def mark_pixels(team_id, dark=False):
    """Coarse colour histogram of the opaque pixels, as [(r, g, b, count)].

    ESPN ships two cuts of every mark: the default, drawn for light backgrounds, and a
    `-dark` variant drawn for dark ones, usually by knocking the mark out in white. Both
    are already on disk, so the background and the variant are chosen together. Picking a
    background without picking the cut to sit on it is what made the first version of
    this script reject 104 of 139 primaries.
    """
    from PIL import Image

    name = "%s-dark.png" % team_id if dark else "%s.png" % team_id
    path = os.path.join(LOGO_DIR, name)
    if not os.path.exists(path):
        return None
    im = Image.open(path).convert("RGBA")
    im.thumbnail((96, 96))
    hist = {}
    for r, g, b, a in im.get_flattened_data() if hasattr(im, "get_flattened_data") \
            else im.getdata():
        if a < 40:
            continue
        key = (r // 16 * 16, g // 16 * 16, b // 16 * 16)
        hist[key] = hist.get(key, 0) + 1
    return [(r, g, b, n) for (r, g, b), n in hist.items()]


def choose_bg(team, cuts):
    """Best (background, logo cut) pair, preferring the school's own primary colour.

    `cuts` is {"light": pixels, "dark": pixels or None}. Within one background the
    better-contrasting cut wins; across backgrounds the school's primary wins as long as
    some cut stands clear of it, because that is the look Grant chose.
    """
    for field, label in (("color", "primary"), ("alt_color", "alternate")):
        rgb = hex_rgb(team.get(field))
        if not rgb:
            continue
        scored = sorted(((blend_share(px, rgb), cut) for cut, px in cuts.items() if px),
                        key=lambda s: s[0])
        if scored and scored[0][0] <= MAX_BLEND:
            return "#" + "".join("%02x" % c for c in rgb), label, scored[0][1]
    best = None
    for value, label in NEUTRALS:
        rgb = hex_rgb(value)
        for cut, px in cuts.items():
            if not px:
                continue
            share = blend_share(px, rgb)
            if best is None or share < best[0]:
                best = (share, value, label, cut)
    return (best[1], best[2], best[3]) if best else (NEUTRALS[0][0], "neutral", "light")


def _lum(rgb):
    f = []
    for v in rgb:
        v /= 255.0
        f.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def contrast(a, b):
    x, y = _lum(a) + 0.05, _lum(b) + 0.05
    return max(x, y) / min(x, y)


def lift(rgb, against=BUG_CHROME, target=MIN_BLOCK_CONTRAST):
    """Raise a colour toward white just far enough to read against the bug's chrome.

    Mixes toward white rather than brightening each channel, so the hue survives: a navy
    lifts to a lighter navy, and a true black lifts to a neutral charcoal because that is
    what a true black actually is. Returns the colour unchanged when it already clears.
    """
    if contrast(rgb, against) >= target:
        return rgb, False
    for step in range(1, 21):
        t = step / 20.0
        mixed = tuple(round(c + (255 - c) * t) for c in rgb)
        if contrast(mixed, against) >= target:
            return mixed, True
    return (255, 255, 255), True


def choose_alt(team, bg_hex, bg_from):
    """The school's OTHER colour, for anything drawn beside the avatar rather than under it.

    Grant asked on 2026-09-10 for the scorebug's colour block to be "the secondary colour
    of each school". Read literally as `alt_color` that fails immediately on this roster:
    Wyoming's alternate is #ffc425, which is already the disc, so the disc would vanish
    into the block.

    So secondary is defined here as the school colour the disc is NOT using. Wyoming's
    disc took the alternate, so its block gets the primary brown; Georgia's disc took the
    primary red, so its block gets the near-black alternate. That is the same idea and it
    can never collide by construction.

    Returns None when the school has only one usable colour, or when both are so close
    that a block would read as the same swatch. The caller falls back to the player's own
    colour, which is what an unclaimed seat uses anyway.
    """
    used = hex_rgb(bg_hex)
    order = ("color", "alt_color") if bg_from == "alternate" else ("alt_color", "color")
    for field in order:
        rgb = hex_rgb(team.get(field))
        if not rgb or used is None:
            continue
        if sum((a - b) ** 2 for a, b in zip(rgb, used)) ** 0.5 < ALT_TOO_CLOSE:
            continue
        rgb, lifted = lift(rgb)
        return "#" + "".join("%02x" % c for c in rgb), ("lifted" if lifted else field)
    return None, None


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("teams", [])


def build():
    teams = load(FBS) + load(EXTRA)
    out, stats, missing = [], {}, []
    for t in sorted(teams, key=lambda t: t["school"]):
        cuts = {"light": mark_pixels(t["id"]), "dark": mark_pixels(t["id"], dark=True)}
        if cuts["light"] is None and cuts["dark"] is None:
            missing.append(t["id"])
            continue
        bg, why, cut = choose_bg(t, cuts)
        stats[why] = stats.get(why, 0) + 1
        row = {
            "id": str(t["id"]),
            "abbr": t.get("abbr", ""),
            "school": t.get("short") or t.get("school", ""),
            "mascot": t.get("mascot", ""),
            "conf": t.get("conference", "Other"),
            "bg": bg,
            "bg_from": why,
            "cut": cut,
        }
        alt, alt_from = choose_alt(t, bg, why)
        if alt:
            row["alt"] = alt
            row["alt_from"] = alt_from
        out.append(row)
    return out, stats, missing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    teams, stats, missing = build()
    if missing:
        print("FAIL: no logo on disk for %d team(s): %s"
              % (len(missing), missing[:8]), file=sys.stderr)
        return 1

    body = json.dumps(teams, separators=(",", ":"), ensure_ascii=False)
    if a.check:
        if not os.path.exists(OUT):
            print("FAIL: %s missing. Run without --check." % OUT, file=sys.stderr)
            return 1
        with open(OUT, encoding="utf-8") as f:
            if f.read() != body:
                print("FAIL: %s is stale. Rebuild it." % OUT, file=sys.stderr)
                return 1
        print("OK: teams.json matches a fresh build (%d teams)" % len(teams))
        return 0

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(body)
    print("wrote %s: %d teams, %.0f KB" % (OUT, len(teams), len(body) / 1024))
    print("background chosen from: %s"
          % ", ".join("%d %s" % (n, k) for k, n in sorted(stats.items(),
                                                          key=lambda kv: -kv[1])))
    odd = [t for t in teams if t["bg_from"] != "primary"]
    if odd:
        print("not on their primary colour:")
        for t in odd[:14]:
            print("   %-26s %-10s %s" % (t["school"], t["bg_from"], t["bg"]))
        if len(odd) > 14:
            print("   ... and %d more" % (len(odd) - 14))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
