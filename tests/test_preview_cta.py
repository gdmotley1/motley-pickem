"""The gate for the way in to the matchup sheet.

The control existed for a week as a 9.5px outlined pill reading "PREVIEW", built to be
the quietest thing on the card so it could not compete with the two team buttons. It was
quiet enough that nobody tapped it. Grant rejected a whole board of gentler options with
"none have any cta or pop" before picking this one on 2026-09-11.

So what is guarded here is the thing that went wrong: it must stay loud, it must stay
tappable, and its animation must not be able to strand itself invisible.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def rule(css, selector):
    """The declarations of one rule.

    Anchored to the start of a line and closed by a brace at the start of a line, because
    several of these rules are preceded by a comment rather than by the previous rule's
    closing brace, and matching on that brace found nothing.

    Comments are stripped, and that is not tidiness. The rule below explains itself with
    "transform, never background-position", so a guard asserting background-position is
    absent matched the sentence saying it is absent and failed. traps.md already records
    this shape: a grep can be satisfied by the comment explaining the fix.
    """
    m = re.search(r"^%s\s*\{(.*?)^\}" % re.escape(selector), css, re.S | re.M)
    assert m, "%s is gone" % selector
    return re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)


def test_the_cta_is_filled_not_outlined():
    """An outlined pill on a white card is what nobody tapped. It has to read as a solid
    control, which means a real background and light text on it."""
    body = rule(read("src", "app.css"), ".grow__preview")
    assert "background: var(--field-deep)" in body, "the CTA is no longer filled"
    assert "color: var(--on-field)" in body, "the CTA has lost its light text"
    assert "border: 0" in body, "the CTA is outlined again"


def test_the_cta_says_where_it_goes():
    """"Preview" named a mechanism and read like a video. The label is the destination."""
    picks = read("src", "screens", "Picks.jsx")
    btn = re.search(r'className="grow__preview".*?</button>', picks, re.S)
    assert btn, "the CTA button is gone from the Picks screen"
    assert "Matchup" in btn.group(0), "the CTA no longer names the matchup"
    assert "aria-label" in btn.group(0), "the CTA has no accessible name"


def test_the_thumb_target_is_still_44px():
    """The pill is 22px because the meta line demands it. What a thumb hits is 44, from a
    pseudo-element, so the hit area can never push the row's height back out.

    22 + 2 * 11 = 44. If either number moves the other has to move with it.
    """
    css = read("src", "app.css")
    height = re.search(r"height: (\d+)px", rule(css, ".grow__preview"))
    inset = re.search(r"inset: -(\d+)px", rule(css, ".grow__preview::after"))
    assert height and inset, "the pill or its hit area is not in the shape expected"
    total = int(height.group(1)) + 2 * int(inset.group(1))
    assert total >= 44, "the tap target is %dpx, under the 44px minimum" % total


def test_the_meta_line_is_tall_enough_to_hold_the_pill():
    """.grow__meta was pinned at 18px for a pill that no longer exists. A 22px pill in an
    18px line overflows it."""
    css = read("src", "app.css")
    meta = int(re.search(r"height: (\d+)px", rule(css, ".grow__meta")).group(1))
    pill = int(re.search(r"height: (\d+)px", rule(css, ".grow__preview")).group(1))
    assert meta >= pill, "the meta line is %dpx and the pill is %dpx" % (meta, pill)


def test_the_cta_never_shrinks_and_the_channel_does():
    """Of everything on that line, the channel is what nobody needs in full."""
    css = read("src", "app.css")
    assert "flex: 0 0 auto" in rule(css, ".grow__preview"), "the CTA can be squashed"
    tv = rule(css, ".grow__tv")
    assert "flex: 0 1 auto" in tv and "min-width: 0" in tv, (
        "the TV chip cannot yield, so the line would overflow instead"
    )


def test_the_shimmer_is_clipped_by_its_own_wrapper():
    """Not by `overflow` on the button, which would clip the 44px hit area down to the
    pill and silently undo the tap target."""
    css = read("src", "app.css")
    assert "overflow: hidden" in rule(css, ".grow__shine"), "the sweep is not clipped"
    assert "overflow" not in rule(css, ".grow__preview"), (
        "overflow on the button would clip ::after, which IS the tap target"
    )
    assert '<span className="grow__shine"' in read("src", "screens", "Picks.jsx"), (
        "the shimmer element is not rendered"
    )


def test_the_shimmer_animates_transform_not_a_painted_property():
    """Twenty of these run at once on a phone. transform is the only property here the
    compositor can animate without repainting every frame."""
    body = rule(read("src", "app.css"), ".grow__shine::before")
    assert "transform: translateX" in body, "the sweep no longer uses transform"
    assert "background-position" not in body, (
        "animating background-position repaints, twenty times over"
    )


def test_both_ends_of_the_animation_are_visible_states():
    """A backgrounded tab pauses CSS animations wherever they happen to be. This app has
    already shipped an overlay that froze half transparent because it animated from zero,
    which is recorded in memory/ui-patterns.md. Worst case here must be a stationary
    highlight, never a blank or missing pill."""
    css = read("src", "app.css")
    frames = re.search(r"@keyframes growshine \{(.*?)\n\}", css, re.S)
    assert frames, "the shimmer keyframes are gone"
    assert "opacity" not in frames.group(1), (
        "the sweep animates opacity; a paused frame could leave it invisible"
    )
    assert "prefers-reduced-motion" in css, "the shimmer never stops for reduced motion"
