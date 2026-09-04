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
        out.append({
            "id": str(t["id"]),
            "abbr": t.get("abbr", ""),
            "school": t.get("short") or t.get("school", ""),
            "mascot": t.get("mascot", ""),
            "conf": t.get("conference", "Other"),
            "bg": bg,
            "bg_from": why,
            "cut": cut,
        })
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
