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


def _eroded(mask, px: int):
    """Shrink a boolean mask by `px`, so mask & ~_eroded(mask, px) is its inner rim."""
    import numpy as np

    out = mask.copy()
    for _ in range(px):
        shrunk = out.copy()
        shrunk[1:, :] &= out[:-1, :]
        shrunk[:-1, :] &= out[1:, :]
        shrunk[:, 1:] &= out[:, :-1]
        shrunk[:, :-1] &= out[:, 1:]
        out = shrunk
    return np.asarray(out)


def key_background(im, tol: int = 30):
    """Make a solid background transparent, from the corners inward.

    A school mark handed over as a flat JPEG or a screenshot arrives on a solid colour
    rather than on transparency. Deleting every pixel that matches that colour is the
    obvious approach, and on Georgia College's bobcat it is not merely risky, it is
    hopeless: the field measures (23,55,125) and the mark's own navy is #123184, which is
    **10.7 units of RGB away** and makes up a quarter of the artwork. No tolerance
    separates them. Any colour match tight enough to keep the navy keeps the field too.

    Connectivity is what does the work, not colour. This floods in from the four corners
    and clears only background that can be reached from an edge, so the navy sealed
    inside the mark's white keyline is unreachable whatever the tolerance. That makes the
    keyline a requirement on the input rather than a nicety: see inputs/logos/README.md.
    `tol` is then only asking "is this pixel still the field", for which a loose value is
    fine, and the guard at the end catches artwork with no barrier at all.
    """
    import numpy as np

    a = np.asarray(im, dtype=np.int16)
    h, w = a.shape[:2]
    rgb = a[:, :, :3]

    corners = [rgb[0, 0], rgb[0, w - 1], rgb[h - 1, 0], rgb[h - 1, w - 1]]
    bg = np.median(np.stack(corners), axis=0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))

    # Flood from the border across everything within tolerance. Done as a repeated
    # dilation over the candidate mask, which needs no recursion and no scipy.
    near = dist <= tol
    reach = np.zeros((h, w), dtype=bool)
    reach[0, :] |= near[0, :]
    reach[-1, :] |= near[-1, :]
    reach[:, 0] |= near[:, 0]
    reach[:, -1] |= near[:, -1]
    while True:
        grown = reach.copy()
        grown[1:, :] |= reach[:-1, :]
        grown[:-1, :] |= reach[1:, :]
        grown[:, 1:] |= reach[:, :-1]
        grown[:, :-1] |= reach[:, 1:]
        grown &= near
        if grown.sum() == reach.sum():
            break
        reach = grown

    # Flooded background goes fully transparent, EXCEPT in the thin band where the flood
    # actually met the mark, which is where the anti-aliasing lives.
    #
    # Fading everything by its distance from the background colour was the obvious way to
    # keep that anti-aliasing and it does not survive real artwork. A field that looks
    # flat is not flat in the file: Grant's corners measure (22,55,125) through
    # (25,58,127) and there is a slight vignette on top, so background out in the open
    # sits ~15 units off the median and a distance ramp hands it alpha 16-32. Invisible
    # on white, a grey wash on anything darker, and enough to push the mark's bounding
    # box out to the full frame, which then shaped it 5% small.
    #
    # Distance is the wrong signal for "is this background"; connectivity already
    # answered that. Distance is only the right signal for "how far through the blend is
    # this edge pixel", so it is used only within `band` of the boundary.
    alpha = a[:, :, 3].astype(np.float32)
    edge = reach.copy()
    for _ in range(2):                       # 2px either side covers the blend
        grown = edge.copy()
        grown[1:, :] |= edge[:-1, :]
        grown[:-1, :] |= edge[1:, :]
        grown[:, 1:] |= edge[:, :-1]
        grown[:, :-1] |= edge[:, 1:]
        edge = grown
    band = reach & edge & ~_eroded(reach, 2)

    ramp = np.clip(dist / max(tol, 1), 0, 1) * 255.0
    alpha[reach] = 0.0
    alpha[band] = np.minimum(a[:, :, 3].astype(np.float32)[band], ramp[band])
    a[:, :, 3] = alpha.astype(np.int16)

    # A mark whose own outline is the background colour and touches the frame has no
    # barrier to stop the flood, and the whole thing drains away. That is a bad input
    # rather than a bug here, but it must not be saved silently: the artwork wants a
    # keyline, or a background that is not one of its own colours.
    kept = float((alpha > 200).sum()) / (h * w)
    if kept < 0.05:
        raise SystemExit(
            "keying left only %.1f%% of the frame. The mark's own colour probably runs "
            "to the edge with nothing to stop the flood; supply artwork with a keyline "
            "or on a contrasting background." % (kept * 100))

    from PIL import Image

    return Image.fromarray(a.astype("uint8"), "RGBA")


# How much of its 500px frame an ESPN mark actually spans on its longest edge. Measured
# over 60 of the vendored files: median 0.920, p10 0.920, p90 0.928. Shaping to a padding
# figure instead was guesswork and came out at 0.893, which rendered GCSU about 3%
# smaller than every school beside it. Grant asked on 2026-09-10 for it to sit at the
# same size as the rest, so the constant is the measurement rather than a taste.
PACK_FILL = 0.920


def shape(blob: bytes, crop_bottom: float, fill: float = PACK_FILL, key: bool = False):
    """Drop the wordmark, trim the transparent margin, and square it up.

    Squaring matters because <Avatar> is a circle: an un-squared mark is scaled by its
    long edge and ends up floating small inside the disc. Squaring on the BOUNDING BOX
    rather than the source frame is what makes the size match: a handed-over file has
    whatever margin its author left, and trimming to the ink first means the mark is
    measured, not the whitespace around it.
    """
    from PIL import Image

    im = Image.open(io.BytesIO(blob)).convert("RGBA")
    if key:
        im = key_background(im)
    if crop_bottom:
        im = im.crop((0, 0, im.width, int(im.height * (1 - crop_bottom))))
    box = ink_box(im)
    if box:
        im = im.crop(box)
    side = int(round(max(im.size) / fill))
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
    out = out.resize((500, 500), Image.LANCZOS)
    # After the resize, not before: LANCZOS invents intermediate colours at every edge,
    # so a palette snapped first is undone by the time the file is written.
    return flatten(out) if key else out


def ink_box(im, floor: int = 16):
    """The bounding box of what is actually drawn, not of any non-zero alpha.

    `Image.getbbox()` counts a pixel at alpha 1, which is the wrong question after
    keying. A rendered background is never perfectly flat: Grant's artwork drifts across
    (22,55,125) to (25,58,127), and a handful of pixels near the frame edge land in the
    blend band and keep single-digit alpha. Those are invisible and they pushed the box
    out to 1210x1252 of a 1254px frame, which shrank the mark to 0.870 of its square
    when the whole point was to land on the pack's 0.920.
    """
    import numpy as np

    a = np.asarray(im)[:, :, 3]
    rows = np.where((a >= floor).any(axis=1))[0]
    cols = np.where((a >= floor).any(axis=0))[0]
    if not len(rows) or not len(cols):
        return None
    return (int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1)


def flatten(im, colors: int = 24):
    """Snap the palette so flat areas are actually flat.

    A school mark is four or five colours. Artwork that has been through a renderer is
    not: every "flat" area carries a little noise, PNG cannot run-length it, and GCSU
    came out at 345KB against a 45KB average for the ESPN pack. That is a tenth of the
    logo payload for one school nobody plays.

    Quantising RGB alone and re-attaching the original alpha is what keeps the edges:
    the anti-aliasing lives in the alpha channel, so snapping colour underneath it is
    invisible, whereas quantising RGBA together would band the edges.
    """
    from PIL import Image

    alpha = im.getchannel("A")
    flat = im.convert("RGB").quantize(colors=colors, method=Image.MEDIANCUT).convert("RGB")
    flat.putalpha(alpha)
    return flat


def source_bytes(t: dict) -> bytes:
    """A team's art, from a file on disk if it has one and the network otherwise.

    `source_file` wins because it is how a better cut of a mark gets in. GCSU's
    Wikipedia file carries a GCSU wordmark that overlaps the bobcat's jaw, so there is
    no crop_bottom that keeps the whole animal and drops the lettering: the one shipped
    until 2026-09-10 cut the chin off. Grant supplied the wordmark-free version, and a
    handed-over file needs a local path rather than a URL.
    """
    path = t.get("source_file")
    if path:
        full = os.path.normpath(path if os.path.isabs(path) else os.path.join(ROOT, path))
        if not os.path.exists(full):
            raise SystemExit(
                "%s wants source_file and it is not there:\n  %s\n"
                "Save the artwork to that path, then re-run." % (t["id"], full))
        with open(full, "rb") as f:
            return f.read()
    return fetch(t["source"])


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
        blob = source_bytes(t)
        art = shape(blob, t.get("crop_bottom", 0.0), key=bool(t.get("key_background")))
        os.makedirs(LOGO_DIR, exist_ok=True)
        art.save(dest, "PNG", optimize=True)
        where = t.get("source_file") or t["source"].split("/")[2]
        print("  %-6s %-34s %s (%.0f KB from %s)"
              % (t["id"], t["school"], t["color"], os.path.getsize(dest) / 1024, where))

    if missing:
        print("\nFAIL: no logo on disk for %s. Run without --check."
              % ", ".join(missing), file=sys.stderr)
        return 1
    print("\nOK: %d extra team(s)" % len(teams))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
