"""The theme contract: components name jobs, never positions on a colour ramp.

src/app.css used to reach into the palette directly, 97 times, with tokens like --g-600
and --n-200. Each of those baked "the chrome is green" and "the page is warm" into the
component that used it, so a new palette could not simply be dropped in: swapping to
Slate on 2026-09-04 meant editing ninety-seven declarations before a single colour moved.

These tests keep that from growing back. A component may use only semantic tokens, every
token it uses has to exist, and the palette ramp stays private to src/theme.css.
"""
from __future__ import annotations

import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
THEME = os.path.join(SRC, "theme.css")

# The ramps, present and past: slate/cool/blue/green/red now, green/neutral/amber before.
# A component reaching for any of them is the regression.
RAMP = re.compile(r"var\(\s*(--(?:s|c|b|gr|rd|g|n|a|r)-\d+)\b")
USED = re.compile(r"var\(\s*(--[a-z0-9-]+)")
DEFINED = re.compile(r"^\s+(--[a-z0-9-]+)\s*:", re.M)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def component_files():
    """Everything that styles something, which is every source file but theme.css."""
    out = []
    for base, _dirs, files in os.walk(SRC):
        for name in files:
            if not name.endswith((".css", ".jsx", ".js")):
                continue
            path = os.path.join(base, name)
            if os.path.abspath(path) != os.path.abspath(THEME):
                out.append(path)
    return sorted(out)


@pytest.mark.parametrize("path", component_files(), ids=lambda p: os.path.relpath(p, ROOT))
def test_no_component_reaches_into_the_colour_ramp(path):
    hits = sorted(set(RAMP.findall(read(path))))
    assert not hits, (
        "%s names ramp positions instead of jobs: %s. Use a semantic token from "
        "theme.css, or add one if none fits."
        % (os.path.relpath(path, ROOT), ", ".join(hits))
    )


def test_every_token_a_component_uses_is_defined():
    defined = set(DEFINED.findall(read(THEME)))
    missing = {}
    for path in component_files():
        for token in set(USED.findall(read(path))):
            if token not in defined:
                missing.setdefault(token, []).append(os.path.relpath(path, ROOT))
    assert not missing, "undefined tokens: %s" % missing


def test_selection_and_result_are_separate_colours():
    """--pick says you chose this. --good says it was right. They must not collapse.

    They were the same green under the old palette, so nothing forced them apart until
    --pick became blue and a correct pick briefly rendered blue points on a green wash.
    """
    theme = read(THEME)
    for token in ("--pick", "--pick-edge", "--pick-wash", "--good", "--good-wash"):
        assert re.search(r"^\s+%s\s*:" % token, theme, re.M), "%s is not defined" % token

    def resolve(name):
        m = re.search(r"^\s+%s\s*:\s*([^;]+);" % name, theme, re.M)
        value = m.group(1).strip()
        ref = re.match(r"var\(\s*(--[a-z0-9-]+)\s*\)$", value)
        return resolve(ref.group(1)) if ref else value

    assert resolve("--pick") != resolve("--good"), (
        "the selection colour and the correct-answer colour resolve to the same value, "
        "so a right pick and a chosen pick are indistinguishable on the board"
    )


def test_the_pwa_chrome_matches_the_field_colour():
    """The install splash and the Android status bar are painted from these two files,
    not from CSS, so they do not move with the palette unless someone moves them."""
    field = re.search(r"^\s+--s-700\s*:\s*(#[0-9a-fA-F]{3,8});", read(THEME), re.M)
    assert field, "--s-700 backs --field and must be a literal the manifest can copy"
    colour = field.group(1).lower()

    manifest = read(os.path.join(ROOT, "static", "manifest.webmanifest"))
    for key in ("background_color", "theme_color"):
        found = re.search(r'"%s"\s*:\s*"(#[0-9a-fA-F]{3,8})"' % key, manifest)
        assert found and found.group(1).lower() == colour, (
            "manifest %s is %s, expected the field colour %s"
            % (key, found.group(1) if found else "absent", colour)
        )

    index = read(os.path.join(ROOT, "index.html"))
    meta = re.search(r'name="theme-color"\s+content="(#[0-9a-fA-F]{3,8})"', index)
    assert meta and meta.group(1).lower() == colour, (
        "index.html theme-color is %s, expected %s"
        % (meta.group(1) if meta else "absent", colour)
    )


def test_the_display_face_is_actually_loaded():
    """A --display family the font link never requests falls back silently, and the
    whole app quietly renders in the fallback serif with nobody noticing."""
    family = re.search(r"^\s+--display\s*:\s*'([^']+)'", read(THEME), re.M)
    assert family, "--display should lead with a quoted family name"
    name = family.group(1).replace(" ", "+")

    index = read(os.path.join(ROOT, "index.html"))
    link = re.search(r'href="(https://fonts\.googleapis\.com/css2[^"]+)"', index)
    assert link, "no Google Fonts link in index.html"
    assert "family=%s" % name in link.group(1), (
        "%s is the display face but index.html never loads it" % family.group(1)
    )


# ------------------------------------------------------ zoom, and the 16px input floor

# The viewport meta used to carry maximum-scale=1. That did suppress the double-tap zoom
# delay, but it also blocked pinch zoom outright, in an app memory/traps.md describes as
# "read by every age in the family" and which already had one contrast bug for the same
# reason. touch-action: manipulation does the double-tap job properly, so the scale cap
# came off on 2026-09-04.
#
# The cap was load-bearing in one place. iOS zooms the page when a focused input renders
# text under 16px, and .adm__input sat at 14px with a comment saying that was safe
# because of the cap. With the cap gone, tapping the Setup search box would have zoomed
# the page. These two tests hold both halves together: they fail if the cap comes back,
# and they fail if any input drops below the floor that replaced it.

INPUT_FLOOR_PX = 16
HTML = os.path.join(ROOT, "index.html")
APP_CSS = os.path.join(SRC, "app.css")


def input_classes():
    """Every className actually used on an <input> in the app."""
    found = set()
    for name in os.listdir(os.path.join(SRC, "screens")):
        if not name.endswith(".jsx"):
            continue
        text = read(os.path.join(SRC, "screens", name))
        for tag in re.findall(r"<input\b[^>]*?/?>", text, re.S):
            for cls in re.findall(r'className="([^"]+)"', tag):
                found.update(cls.split())
    return found


def font_size_of(css, klass):
    rule = re.search(r"\.%s\s*\{(.*?)\}" % re.escape(klass), css, re.S)
    if not rule:
        return None
    sizes = re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", rule.group(1))
    return float(sizes[-1]) if sizes else None


def test_the_viewport_does_not_block_pinch_zoom():
    """Taking zoom away from a family app is an accessibility regression."""
    meta = re.search(r'<meta name="viewport"[^>]*>', read(HTML)).group(0)
    for banned in ("maximum-scale", "user-scalable=no", "user-scalable=0"):
        assert banned not in meta, "the viewport meta blocks zoom again: %r" % banned


def test_tappable_controls_opt_out_of_the_double_tap_delay():
    """What replaced maximum-scale=1. Without it the cap's removal costs responsiveness."""
    theme = read(THEME)
    rule = re.search(r"([^}]*?)\{[^}]*touch-action:\s*manipulation", theme, re.S)
    assert rule, "no touch-action: manipulation anywhere in theme.css"
    assert "button" in rule.group(1), "the rule does not reach <button>, and every "\
                                     "tappable thing in this app is a button"


def test_no_input_renders_below_the_size_that_makes_ios_zoom():
    """An input under 16px zooms the page on focus now that the scale cap is gone."""
    css = read(APP_CSS) + read(THEME)
    classes = input_classes()
    assert classes, "found no <input> classNames to check; did the parser break?"
    for klass in sorted(classes):
        size = font_size_of(css, klass)
        # No rule, or no font-size in it, means it inherits body's 16px. That is fine.
        if size is None:
            continue
        assert size >= INPUT_FLOOR_PX, (
            ".%s renders at %gpx; iOS will zoom the page when it takes focus"
            % (klass, size))


# ------------------------------------------------------- the tab bar may not composite

# Grant opened the app from his home screen on 2026-09-10 and the tab bar was painted
# about 50px off, with a band of page colour under it, snapping back the moment he
# scrolled. The header and the page content were in the right place in both states, which
# is what ruled out every layout explanation: nothing about the shell's height or the
# scroll container can move one fixed child and leave its siblings alone.
#
# It was a compositing bug. `backdrop-filter` on a fixed element makes Safari composite
# against a snapshot of the page taken before layout settles, and a `transform` on a
# fixed element is the same class of trigger. A cold launch from a home screen icon lands
# first paint and layout close enough together to hit it; a browser reload usually does
# not, which is why it never showed up here.
#
# Two earlier attempts rewrote the shell instead, on the theory that the document
# scrolling rather than .app__body was to blame. That was a real finding and the wrong
# one: it did not fix the gap, and it cost scrolling on the phone. Both were reverted.

def test_the_tab_bar_never_composites():
    css = read(APP_CSS)
    rule = re.search(r"\.tabbar\s*\{([^}]*)\}", re.sub(r"/\*.*?\*/", "", css, flags=re.S))
    assert rule, ".tabbar rule not found"
    body = rule.group(1)

    assert "backdrop-filter" not in body, (
        "backdrop-filter is back on .tabbar. On iOS this paints the fixed bar against a "
        "stale snapshot on cold launch and leaves a gap under it until the first scroll."
    )
    assert "transform" not in body, (
        "a transform is back on .tabbar. Same class of iOS bug as backdrop-filter, and "
        "it can hold the gap open on its own. Centre with left/right: 0 and "
        "margin-inline: auto instead."
    )
    assert re.search(r"margin-inline:\s*auto", body) and re.search(r"left:\s*0", body), (
        "the bar still has to be centred, just without a transform"
    )
    # An opaque background, because the blur is gone and content must not show through.
    assert re.search(r"background:\s*var\(--card\)", body), (
        "with no blur the bar needs the opaque --card, not the translucent --card-a"
    )


def test_the_sticky_bars_keep_their_blur():
    """Sticky is not fixed. Those bars paint with the scroll and were never affected."""
    css = re.sub(r"/\*.*?\*/", "", read(APP_CSS), flags=re.S)
    for selector in (".topbar", ".choose__top", ".rank__head"):
        rule = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
        assert rule, f"{selector} not found"
        assert "backdrop-filter" in rule.group(1), (
            f"{selector} lost its blur. Only the FIXED tab bar needed that removing; "
            f"stripping the sticky bars too is a visual regression for no reason."
        )
