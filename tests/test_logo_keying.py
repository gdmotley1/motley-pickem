"""Turning a mark handed over on a solid background into a transparent one.

`fetch_extra_teams.key_background` exists because a school's own artwork does not arrive
the way ESPN's does. Grant supplied the Georgia College bobcat on 2026-09-10 as a flat
royal-blue image, and the mark's navy is close enough to that blue that deleting every
matching pixel eats the outline. Flooding in from the corners instead only clears
background that touches an edge, so navy enclosed by the white keyline survives.

The fixture is DRAWN here rather than taken from `static/logos/gcsu.png`. The first cut
of this file did use the shipped mark, and every assertion in it broke the moment that
mark was replaced with the artwork these tests exist to support: the new file carries a
keyline of its own, so the keyline-less case it was asserting no longer existed. A test
whose fixture is the asset under change proves nothing about the code. Drawing a mark
with the two properties that matter, navy enclosed by white and navy exposed to the
field, pins the behaviour instead.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from fetch_extra_teams import PACK_FILL, ink_box, key_background, shape  # noqa: E402

FIELD = (23, 56, 125)     # the royal blue Grant's file sits on
NAVY = (18, 49, 132)      # the real mark's navy: 10.7 RGB units from the field
GREEN = (24, 100, 70)
WHITE = (254, 254, 254)
N, SS = 400, 4            # frame, and the supersample that gives real anti-aliasing


def draw_mark(keyline: bool):
    """A stand-in bobcat: green body, navy detail, optionally a white keyline.

    With the keyline the outermost colour is white, which is what stops a flood. Without
    it the body is ringed in navy, which is within tolerance of the field it sits on, and
    that is the case the input requirement exists for.
    """
    n = N * SS
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body = [70 * SS, 110 * SS, 330 * SS, 320 * SS]
    ears = [(90 * SS, 130 * SS), (140 * SS, 30 * SS), (190 * SS, 140 * SS)]
    ears2 = [(210 * SS, 140 * SS), (260 * SS, 30 * SS), (310 * SS, 130 * SS)]

    if keyline:
        pad = 11 * SS
        d.ellipse([body[0] - pad, body[1] - pad, body[2] + pad, body[3] + pad],
                  fill=WHITE + (255,))
        for e in (ears, ears2):
            d.polygon([(x + (pad if x > 200 * SS else -pad), y - pad) for x, y in e],
                      fill=WHITE + (255,))

    outline = NAVY if not keyline else GREEN
    d.ellipse(body, fill=outline + (255,))
    for e in (ears, ears2):
        d.polygon(e, fill=outline + (255,))
    d.ellipse([body[0] + 6 * SS, body[1] + 6 * SS, body[2] - 6 * SS, body[3] - 6 * SS],
              fill=GREEN + (255,))

    # interior navy, fully enclosed by green: the thing a colour match would delete
    d.ellipse([150 * SS, 180 * SS, 190 * SS, 215 * SS], fill=NAVY + (255,))
    d.ellipse([215 * SS, 180 * SS, 255 * SS, 215 * SS], fill=NAVY + (255,))
    d.ellipse([160 * SS, 240 * SS, 245 * SS, 300 * SS], fill=WHITE + (255,))
    return im.resize((N, N), Image.LANCZOS)


def on_field(mark, field=FIELD):
    """Composite onto a flat opaque colour, the way a handed-over file arrives."""
    a = np.asarray(mark).astype(float)
    al = a[:, :, 3:4] / 255.0
    rgb = a[:, :, :3] * al + np.array(field, float) * (1 - al)
    return Image.fromarray(
        np.dstack([rgb.astype("uint8"), np.full(rgb.shape[:2], 255, "uint8")]), "RGBA")


@pytest.fixture(scope="module")
def keyed():
    """Keyed output, plus the drawn mark's own alpha to judge it against.

    Two thresholds, not one, and the difference is not pedantry. Compositing onto an
    opaque field turns every half-transparent edge pixel into a fully opaque blend, so
    "alpha > 200 in the original" understates the mark by the width of its own
    anti-aliasing: judged that way, keying looked like it left 763px of field behind when
    every one of them was the tip of a drawn ear. Solid mark is alpha > 200; definite
    background is alpha == 0; the ramp in between belongs to neither."""
    mark = draw_mark(keyline=True)
    return key_background(on_field(mark)), np.asarray(mark)[:, :, 3]


def test_keying_recovers_the_mark(keyed):
    out, alpha = keyed
    kept = np.asarray(out)[:, :, 3] > 200
    lost = int(((alpha > 200) & ~kept).sum())
    assert lost <= 2, "keying removed %d px of the mark" % lost


def test_keying_leaves_no_background_behind(keyed):
    out, alpha = keyed
    kept = np.asarray(out)[:, :, 3] > 200
    left = int(((alpha == 0) & kept).sum())
    assert left == 0, "%d px of the flat field survived keying" % left


def test_navy_enclosed_by_the_keyline_survives(keyed):
    """The point of flooding rather than colour-matching. The interior navy is 10.7 units
    from the field it sits on and is a quarter of the artwork, so there is no tolerance
    that keeps it and drops the field. Connectivity is the only thing separating them."""
    out, _ = keyed
    src = np.asarray(draw_mark(keyline=True))
    navy = (np.abs(src[:, :, :3].astype(int) - np.array(NAVY)).sum(axis=2) < 30)
    navy &= src[:, :, 3] > 200
    assert navy.sum() > 500, "fixture has no interior navy to check"
    kept = np.asarray(out)[:, :, 3] > 200
    assert int((navy & ~kept).sum()) == 0, "interior navy was keyed away"


def test_the_field_is_cleared_flat_not_faded():
    """A field that looks flat is not flat in the file, and fading background by its
    distance from the median hands the open field alpha 16-32. Invisible on white, a grey
    wash on anything darker, and enough to push the bounding box out to the whole frame.
    Anything the flood reaches away from the mark must be a hard zero."""
    noisy = np.asarray(on_field(draw_mark(keyline=True))).astype(int)
    rng = np.random.default_rng(4)
    noisy[:, :, :3] += rng.integers(-6, 7, size=noisy[:, :, :3].shape)
    vign = np.linspace(0, 12, N)[None, :, None]          # a gentle gradient across it
    noisy[:, :, :3] = np.clip(noisy[:, :, :3] + vign, 0, 255)
    out = key_background(Image.fromarray(noisy.astype("uint8"), "RGBA"))
    al = np.asarray(out)[:, :, 3]
    assert al[:40, :40].max() == 0, "corner still carries alpha %d" % al[:40, :40].max()
    assert al[:, :20].max() == 0 and al[-20:, :].max() == 0, "frame edge still carries alpha"


def test_the_keyline_and_not_the_tolerance_is_what_saves_the_mark():
    """The requirement on the input, measured.

    The first version of this test claimed a tight tolerance protected an exposed navy
    outline. It does not, and the arithmetic says so: the mark's navy is 10.7 units from
    the field, so it is inside any tolerance loose enough to clear the field at all.
    Lowering `tol` buys nothing here. What saves the mark is the white keyline sealing
    the navy off from the frame, which is why inputs/logos/README.md asks for one."""
    bare, keyed_art = draw_mark(keyline=False), draw_mark(keyline=True)

    def lost(mark, tol):
        before = np.asarray(mark)[:, :, 3] > 200
        after = np.asarray(key_background(on_field(mark), tol=tol))[:, :, 3] > 200
        return float((before & ~after).sum()) / before.sum()

    for tol in (20, 30, 45):
        assert lost(keyed_art, tol) < 0.01, (
            "keyline artwork eroded %.1f%% at tol=%d" % (lost(keyed_art, tol) * 100, tol))
        assert lost(bare, tol) > 0.10, (
            "exposed navy survived at tol=%d; if the two colours moved apart the "
            "keyline requirement can be relaxed" % tol)


def espn_fill(sample=40):
    """How much of its frame a vendored ESPN mark spans, over a stable sample."""
    import random

    d = os.path.join(ROOT, "static", "logos")
    fs = sorted(f for f in os.listdir(d)
                if f.endswith(".png") and not f.endswith("-dark.png"))
    spans = []
    for f in random.Random(7).sample(fs, min(sample, len(fs))):
        im = Image.open(os.path.join(d, f)).convert("RGBA")
        b = im.getbbox()
        if b:
            spans.append(max(b[2] - b[0], b[3] - b[1]) / max(im.size))
    return sorted(spans)


def test_shaping_lands_on_the_pack_size_and_centre():
    """Grant asked for GCSU to sit at the same size as every other mark, so this measures
    against the pack rather than a padding constant. Shaping to 6% padding gave 0.893 and
    the pack sits at 0.920: a 3% difference that reads as a slightly small logo."""
    import io

    buf = io.BytesIO()
    on_field(draw_mark(keyline=True)).save(buf, "PNG")
    out = shape(buf.getvalue(), 0.0, key=True)
    assert out.size == (500, 500), "the pack is 500px square"

    box = ink_box(out)
    assert box is not None, "shaping produced an empty frame"
    span = max(box[2] - box[0], box[3] - box[1]) / 500.0
    spans = espn_fill()
    lo, hi = spans[len(spans) // 10], spans[9 * len(spans) // 10]
    assert lo - 0.015 <= span <= hi + 0.015, (
        "shaped mark spans %.3f; the ESPN pack sits between %.3f and %.3f"
        % (span, lo, hi))
    assert abs(span - PACK_FILL) < 0.02, "span %.3f is not the target %.3f" % (
        span, PACK_FILL)
    assert abs((box[0] + box[2]) / 2 - 250) <= 3, "off centre horizontally"
    assert abs((box[1] + box[3]) / 2 - 250) <= 3, "off centre vertically"


def test_the_shipped_gcsu_mark_is_shaped_and_clean():
    """The asset itself, as it will render. Separate from the logic tests above on
    purpose: this is the one that fails if fetch_extra_teams is re-run badly."""
    p = os.path.join(ROOT, "static", "logos", "gcsu.png")
    im = Image.open(p).convert("RGBA")
    assert im.size == (500, 500)

    box = ink_box(im)
    span = max(box[2] - box[0], box[3] - box[1]) / 500.0
    assert abs(span - PACK_FILL) < 0.02, "gcsu spans %.3f, pack is %.3f" % (span, PACK_FILL)
    assert abs((box[0] + box[2]) / 2 - 250) <= 3, "gcsu is off centre"

    al = np.asarray(im)[:, :, 3]
    margin = max(al[:, :18].max(), al[:18, :].max(), al[:, -18:].max(), al[-18:, :].max())
    assert margin == 0, "residual background in the margin, alpha %d" % margin

    # No colour assertion here on purpose. A quarter of this mark is a navy 10.7 units
    # from the field it was lifted off, so "does any pixel look like the field" cannot
    # distinguish leftover background from the bobcat's own outline. The margin check
    # above is the real one: surviving field would be connected to the frame edge.
