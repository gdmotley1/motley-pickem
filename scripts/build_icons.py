"""Build every app icon from one piece of source artwork.

    python scripts/build_icons.py --src inputs/app-icon.png
    python scripts/build_icons.py --src inputs/app-icon.png --check

Writes static/icons/icon-180.png, icon-192.png, icon-512.png and icon-512-maskable.png,
which are the four the manifest and index.html name. Run it again whenever the artwork
changes rather than resizing anything by hand.

Two things about app icons that are easy to get wrong and expensive to notice late:

1. THE CORNERS MUST BE OPAQUE. iOS masks a home screen icon to its own squircle, so any
   transparency the artwork leaves outside its own rounded corners is composited against
   black and the icon gets a dark halo inside Apple's curve. Source art that is already
   a rounded square, which is the usual shape a logo arrives in, is exactly the case that
   hits this. The fix here is to lay the art over a blown-up copy of itself, so the colour
   under the corners is the art's own colour rather than a flat guess that will not match
   a gradient.

2. A MASKABLE ICON IS CROPPED HARD. Android and some launchers cut it to whatever shape
   they like, guaranteeing only the middle 80%. Anything outside that is expendable, so
   the maskable variant is the art inset into a filled square rather than the same file
   under a different name.
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("needs Pillow: python -m pip install pillow", file=sys.stderr)
    raise SystemExit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "icons")

# The four the app actually references. 180 is apple-touch-icon in index.html; the other
# three are named by static/manifest.webmanifest.
SIZES = {
    "icon-180.png": (180, False),
    "icon-192.png": (192, False),
    "icon-512.png": (512, False),
    "icon-512-maskable.png": (512, True),
}

# A logo usually arrives with a soft glow or drop shadow around it. Cropping to any
# non-zero alpha would keep all of that as dead margin, so the crop is to pixels that are
# nearly solid, which finds the artwork itself.
SOLID_ALPHA = 200

# How far in the crop may go looking for solid corners before giving up and filling
# instead. A rounded square needs about radius * 0.3, which for a typical app-icon radius
# is around 6%. Well past that means the art is not a rounded square at all.
MAX_INSET = 0.15

# A maskable icon's guaranteed-visible area is the middle 80%.
SAFE = 0.80


def solid_box(im: Image.Image):
    """The bounding box of the artwork, ignoring any glow around it."""
    alpha = im.getchannel("A")
    mask = alpha.point(lambda a: 255 if a >= SOLID_ALPHA else 0)
    box = mask.getbbox()
    if not box:
        raise SystemExit("the source image is fully transparent")
    return box


def squared(im: Image.Image) -> Image.Image:
    """Centre the art on a square canvas without distorting it."""
    w, h = im.size
    if w == h:
        return im
    side = max(w, h)
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(im, ((side - w) // 2, (side - h) // 2), im)
    return out


def opaque(im: Image.Image) -> Image.Image:
    """Make the square fully opaque edge to edge.

    Preferred route is to crop INWARD until the corners are solid. Source art is nearly
    always an already-rounded square, and the region just inside its own radius is real
    artwork with the real gradient in it, so cropping there gives a true full bleed. The
    rounded look is not lost by this: iOS re-rounds the icon itself, and supplying a
    square is what it actually wants.

    Filling behind the corners instead was the first attempt and it looked wrong. The
    blown-up copy is still transparent at its own corners, so the fill fell through to
    the dominant colour, which on a gradient is the DARKEST blue, and every corner read
    as a shadow inside Apple's curve.
    """
    side = im.size[0]
    step = max(1, side // 200)
    inset = 0
    while inset < side * MAX_INSET:
        if corners_solid(im, inset):
            break
        inset += step

    if corners_solid(im, inset):
        if inset:
            print("  cropped %d px (%.1f%%) into the corner radius for a full bleed"
                  % (inset, 100.0 * inset / side))
        cut = im.crop((inset, inset, side - inset, side - inset)).convert("RGBA")
        # Flatten the last few points of alpha away. "Nearly opaque" still composites
        # against black on an iOS home screen, just faintly, and a faint dark wash over
        # the whole icon is harder to spot than a dark corner and just as wrong.
        flat = Image.new("RGBA", cut.size, dominant(cut))
        flat.alpha_composite(cut)
        return flat

    # Art that is not a rounded square at all (a circle, a wordmark on nothing). Cropping
    # would never reach solid corners, so fall back to laying it on its own colour.
    print("  corners never went solid within %.0f%%; filling instead" % (MAX_INSET * 100))
    flat = Image.new("RGBA", (side, side), dominant(im))
    flat.alpha_composite(im)
    return flat


def corners_solid(im: Image.Image, inset: int) -> bool:
    """Are all four corners of the inset square solid?

    SOLID_ALPHA, not 255. This blue logo's interior alpha is 249 to 253, never a clean
    255, presumably from whatever rendered its glow. Testing for 255 meant the crop never
    found a solid corner at any inset and every icon silently took the fill path instead,
    which is what put a dark shadow in all four corners the first time round.
    """
    side = im.size[0]
    hi = side - 1 - inset
    if hi <= inset:
        return False
    alpha = im.getchannel("A")
    return all(alpha.getpixel(p) >= SOLID_ALPHA
               for p in ((inset, inset), (hi, inset), (inset, hi), (hi, hi)))


def edge_color(im: Image.Image):
    """The average colour around the art's border.

    Used to fill behind an inset logo, where what you want is whatever the artwork's own
    edge is painting rather than whatever colour it uses most.
    """
    side = im.size[0]
    band = max(1, side // 40)
    px = im.convert("RGB")
    samples = []
    for i in range(0, side, max(1, side // 64)):
        samples.append(px.getpixel((i, band)))
        samples.append(px.getpixel((i, side - 1 - band)))
        samples.append(px.getpixel((band, i)))
        samples.append(px.getpixel((side - 1 - band, i)))
    n = len(samples)
    return (sum(s[0] for s in samples) // n,
            sum(s[1] for s in samples) // n,
            sum(s[2] for s in samples) // n, 255)


def dominant(im: Image.Image):
    """The most common nearly-solid colour, used as the last-resort fill."""
    small = im.resize((32, 32), Image.LANCZOS)
    counts = {}
    for px in small.getdata():
        if px[3] >= SOLID_ALPHA:
            counts[px[:3]] = counts.get(px[:3], 0) + 1
    if not counts:
        return (0, 0, 0, 255)
    return max(counts.items(), key=lambda kv: kv[1])[0] + (255,)


def build(src_path: str, check: bool) -> int:
    src = Image.open(src_path).convert("RGBA")
    art = opaque(squared(src.crop(solid_box(src))))
    print("source %s %s -> art %s" % (os.path.basename(src_path), src.size, art.size))

    corner = art.getpixel((0, 0))
    if corner[3] != 255:
        raise SystemExit("the corners are still transparent; iOS would halo this icon")

    os.makedirs(OUT, exist_ok=True)
    for name, (size, maskable) in SIZES.items():
        if maskable:
            inner = int(size * SAFE)
            # edge_color, not dominant. The art's most common colour is WHITE here,
            # because the M and the wordmark are white and large, so a dominant fill put
            # a white border around the icon. What belongs behind an inset logo is the
            # colour its own edge is already painting.
            out = Image.new("RGBA", (size, size), edge_color(art))
            out.alpha_composite(art.resize((inner, inner), Image.LANCZOS),
                                ((size - inner) // 2, (size - inner) // 2))
        else:
            out = art.resize((size, size), Image.LANCZOS)

        path = os.path.join(OUT, name)
        if check:
            existing = Image.open(path).convert("RGBA") if os.path.exists(path) else None
            same = existing is not None and list(existing.getdata()) == list(out.getdata())
            print("  %-22s %s" % (name, "up to date" if same else "WOULD CHANGE"))
            continue
        out.save(path, "PNG", optimize=True)
        print("  %-22s %dx%d  %s" % (name, size, size,
                                     "maskable, art inset to 80%" if maskable else "full bleed"))
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--src", default=os.path.join(ROOT, "inputs", "app-icon.png"),
                   help="the source artwork (default: inputs/app-icon.png)")
    p.add_argument("--check", action="store_true",
                   help="report what would change without writing anything")
    a = p.parse_args()
    if not os.path.exists(a.src):
        print("no such file: %s" % a.src, file=sys.stderr)
        return 2
    return build(a.src, a.check)


if __name__ == "__main__":
    sys.exit(main())
