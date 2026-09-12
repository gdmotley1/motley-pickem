"""Turn Grant's badge art into the files the Season tab ships.

    python scripts/build_badges.py            # write src/assets/badges/<id>.webp
    python scripts/build_badges.py --check    # exit 1 if any shipped file is stale or missing

The source is inputs/badges/<id>.png: 17 ChatGPT renders at 1254px and about 2MB each,
matched to their prompts by eye on 2026-09-12 (inputs/badges/README.md). Each one here is
trimmed to the medallion, squared, and saved as a 320px WebP with its alpha. The biggest
badge on any screen is 104px, so 320 is three times that for a phone.

They live under src/assets rather than static because Vite then fingerprints the file
name. A badge Grant redraws gets a new URL, so neither GitHub Pages' ten-minute cache nor
the service worker can keep serving the old art under the old name.

--check compares fingerprints recorded in manifest.json rather than re-encoding. Encoding
all seventeen takes about half a minute, which is too slow for a gate that runs before
every "done"; the build itself was confirmed byte-for-byte repeatable on 2026-09-12.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "inputs", "badges")
OUT = os.path.join(ROOT, "src", "assets", "badges")
MANIFEST = os.path.join(OUT, "manifest.json")
PX = 320
QUALITY = 86

# Every badge the record book can draw. tests/test_records.py holds this list against
# src/lib/seasonRecords.js, so a record added there without art fails the gate.
IDS = [
    # everyone's numbers, chrome rims
    "best_week", "best_record", "low_week", "streak", "worst_miss", "my_upset",
    "weeks_won", "season_record",
    # Hall of fame, gold laurel
    "perfect_week", "only_one", "season_points", "big_upset", "win_by_20", "two_td_upset",
    "three_upsets", "margin",
    # Hall of shame, cracked gunmetal
    "lost_20",
]


def sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def source(bid: str) -> str:
    path = os.path.join(SRC, bid + ".png")
    if not os.path.exists(path):
        raise SystemExit("missing badge art: %s (save the PNG there and re-run)" % path)
    return path


def render(bid: str) -> bytes:
    from PIL import Image

    im = Image.open(source(bid)).convert("RGBA")
    # Trim on alpha above 16, so the near-invisible fringe a background remover leaves
    # does not count as part of the badge and shrink it inside its box.
    box = im.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    if not box:
        raise SystemExit("%s is fully transparent" % source(bid))
    im = im.crop(box)
    side = max(im.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(im, ((side - im.size[0]) // 2, (side - im.size[1]) // 2))
    square = square.resize((PX, PX), Image.LANCZOS)
    buf = io.BytesIO()
    square.save(buf, "WEBP", quality=QUALITY, method=6)
    return buf.getvalue()


def check() -> list[str]:
    """Everything wrong with what ships, without re-encoding anything."""
    problems = []
    try:
        manifest = json.load(open(MANIFEST, encoding="utf-8"))
    except (OSError, ValueError):
        return ["no readable manifest.json; run the build"]
    if manifest.get("settings") != {"px": PX, "quality": QUALITY}:
        problems.append("size or quality changed since the last build")
    for bid in IDS:
        entry = manifest.get("badges", {}).get(bid)
        out = os.path.join(OUT, bid + ".webp")
        if not entry:
            problems.append("%s was never built" % bid)
        elif entry["source"] != sha(source(bid)):
            problems.append("inputs/badges/%s.png changed since it was built" % bid)
        elif not os.path.exists(out) or entry["output"] != sha(out):
            problems.append("src/assets/badges/%s.webp is missing or was edited by hand" % bid)
    extra = sorted(set(f[:-5] for f in os.listdir(OUT) if f.endswith(".webp")) - set(IDS))
    problems += ["%s.webp is not a badge any more" % x for x in extra]
    return problems


def main() -> int:
    if "--check" in sys.argv:
        problems = check()
        for p in problems:
            print(p)
        print("badges %s" % ("STALE" if problems else "ok"))
        return 1 if problems else 0

    os.makedirs(OUT, exist_ok=True)
    badges = {}
    total = 0
    for bid in IDS:
        data = render(bid)
        dest = os.path.join(OUT, bid + ".webp")
        with open(dest, "wb") as fh:
            fh.write(data)
        total += len(data)
        badges[bid] = {"source": sha(source(bid)), "output": hashlib.sha256(data).hexdigest()}
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"settings": {"px": PX, "quality": QUALITY}, "badges": badges}, fh, indent=1)
        fh.write("\n")
    print("%d badges, %.0f KB" % (len(IDS), total / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
