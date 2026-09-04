"""Add schools ESPN does not carry to the avatar pack.

    python scripts/fetch_extra_teams.py                  # -> static/logos/<id>.png
    python scripts/fetch_extra_teams.py --check          # verify, download nothing

fetch_teams.py covers the 138 FBS schools, which is everyone the pool ever plays. But a
profile picture is not about who plays: Grant asked for Georgia College & State on
2026-09-04 because it is his alma mater. GCSU is Division II Peach Belt and fields no
football team at all, so it appears in none of ESPN's lists. Verified: 760 football teams
and 362 in each basketball league, zero matches.

So non-ESPN schools need their own small pipeline, and they need two things ESPN's marks
give away for free:

  CROP. ESPN marks are head-only and drawn to survive a favicon. A school's own athletics
  logo usually carries a wordmark, and GCSU's is a third "GCSU" lettering that turns into
  a smear at the 22px the Board renders. `crop_bottom` drops it.

  A BACKGROUND THAT IS NOT THE MARK'S OWN COLOUR. The chosen avatar treatment puts the
  mark on the school's colour, so the two must not be the same. GCSU's bobcat is outlined
  in the school green, and on green it loses its edges entirely. On the school navy the
  green and white pop. Both were rendered at 22/36/56 before choosing.

Sources are recorded per school. These are copyrighted school marks used to identify the
school, in a private four-person family app.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRA = os.path.join(ROOT, "inputs", "extra_teams.json")
LOGO_DIR = os.path.join(ROOT, "static", "logos")

# Wikimedia refuses the default urllib agent with a 403 and asks for a descriptive one.
# This is NOT the browser-like UA that CLAUDE.md warns about: that rule is about the
# egress proxy in front of ESPN, and this never touches ESPN.
UA = "MotleyPickem/1.0 (private family pick'em; contact gdmotley1@gmail.com)"


def load():
    with open(EXTRA, encoding="utf-8") as f:
        return json.load(f)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def shape(blob: bytes, crop_bottom: float, pad: float = 0.06):
    """Drop the wordmark, trim the transparent margin, and square it up.

    Squaring matters because <Avatar> is a circle: an un-squared mark is scaled by its
    long edge and ends up floating small inside the disc.
    """
    from PIL import Image

    im = Image.open(io.BytesIO(blob)).convert("RGBA")
    if crop_bottom:
        im = im.crop((0, 0, im.width, int(im.height * (1 - crop_bottom))))
    box = im.getbbox()
    if box:
        im = im.crop(box)
    side = int(max(im.size) * (1 + pad * 2))
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
    return out.resize((500, 500), Image.LANCZOS)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the logos are on disk; download nothing")
    a = ap.parse_args()

    teams = load()
    missing = []
    for t in teams:
        dest = os.path.join(LOGO_DIR, "%s.png" % t["id"])
        if a.check:
            (missing.append(t["id"]) if not os.path.exists(dest)
             else print("  ok  %-6s %s" % (t["id"], t["school"])))
            continue
        blob = fetch(t["source"])
        art = shape(blob, t.get("crop_bottom", 0.0))
        os.makedirs(LOGO_DIR, exist_ok=True)
        art.save(dest, "PNG", optimize=True)
        print("  %-6s %-34s %s (%.0f KB from %s)"
              % (t["id"], t["school"], t["color"], os.path.getsize(dest) / 1024,
                 t["source"].split("/")[2]))

    if missing:
        print("\nFAIL: no logo on disk for %s. Run without --check."
              % ", ".join(missing), file=sys.stderr)
        return 1
    print("\nOK: %d extra team(s)" % len(teams))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
