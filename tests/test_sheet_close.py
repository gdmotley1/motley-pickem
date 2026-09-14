"""Every sheet has a close button that no scroll can take away. Added 2026-09-14.

Grant: "i cant click out of the matchup preview. no back button nothing. bad ux." The matchup
sheet runs to 92% of the screen, which leaves 67px of scrim on an 844px iPhone, most of it
under the status bar; the grab bar was never a handle, and he had to close the app to get back
to his picks.
The team picker had the same trap: no button out, only a pick or that sliver of scrim.

What is guarded: the close is rendered by Sheet itself, in a top bar outside the part that
scrolls; every sheet passes the onClose it calls; no overlay is built by hand where the close
would be missing; the sheet is a column and only its body scrolls; the target is thumb-sized
and sits inside its bar; tapping outside and Escape still close.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def rules():
    """(selectors, body) for every rule in app.css, comments stripped."""
    sheet = re.sub(r"/\*.*?\*/", "", read("src", "app.css"), flags=re.S)
    return [([s.strip() for s in sel.split(",")], body)
            for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", sheet)]


def rule(selector):
    for sels, body in rules():
        if selector in sels:
            return body
    raise AssertionError(f"{selector} has no rule in app.css")


def px(body, prop):
    m = re.search(r"(?:^|;|\s)%s:\s*(-?\d+(?:\.\d+)?)px" % re.escape(prop), body)
    return float(m.group(1)) if m else None


def sheet_component():
    ui = read("src", "components", "ui.jsx")
    start = ui.index("export function Sheet(")
    return ui[start: ui.index("\nexport function ", start + 1)]


def jsx_files():
    for dirpath, _, files in os.walk(SRC):
        for name in files:
            if name.endswith(".jsx"):
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as f:
                    yield os.path.relpath(path, SRC), f.read()


# ------------------------------------------------------------------ the component


def test_sheet_renders_the_close_above_the_part_that_scrolls():
    body = sheet_component()
    top = body.index('className="sheet__top"')
    close = body.index('className="sheet__close"')
    scroller = body.index('className="sheet__body"')
    assert top < close < scroller, "the close must sit in the top bar, before the scrolling body"
    assert re.search(r'className="sheet__close" onClick=\{onClose\} aria-label="Close"', body)
    assert re.search(r'<div className="sheet__body">\{children\}</div>', body), (
        "a sheet's content must go inside the body, or it scrolls the bar away with it"
    )
    assert body.count("{children}") == 1


def test_tapping_outside_and_escape_still_close():
    body = sheet_component()
    assert re.search(r"className=\{`sheet__scrim[^`]*`\}\s*onClick=\{onClose\}", body)
    assert "e.key === 'Escape' && onClose?.()" in body


def test_every_sheet_passes_the_onclose_its_button_calls():
    """A <Sheet> without onClose would draw a close button that does nothing. Walks src."""
    tags = []
    for path, text in jsx_files():
        # Braced attributes whole: onClose={() => ...} has a > of its own.
        tags += [(path, t) for t in re.findall(r"<Sheet\b(?:[^>{}]|\{[^{}]*\})*>", text)]
    assert len(tags) >= 6, "found almost no sheets; the walk is looking in the wrong place"
    missing = [p for p, t in tags if not re.search(r"\sonClose=\{", t)]
    assert not missing, f"sheets with no onClose: {missing}"


def test_no_overlay_is_built_by_hand():
    """A dialog assembled outside Sheet would skip the close. Only Sheet may be one."""
    found = [p for p, text in jsx_files() if re.search(r'role="dialog"|aria-modal', text)]
    assert found == [os.path.join("components", "ui.jsx")], found


# ------------------------------------------------------------------ the layout


def test_only_the_body_scrolls():
    sheet = rule(".sheet")
    assert re.search(r"display:\s*flex", sheet) and re.search(r"flex-direction:\s*column", sheet)
    assert re.search(r"(?:^|\s)flex:\s*none", rule(".sheet__top"))
    body = rule(".sheet__body")
    assert re.search(r"overflow-y:\s*auto", body)
    assert re.search(r"min-height:\s*0", body), "without min-height: 0 the body will not shrink to scroll"
    # Walk every rule that styles the sheet box itself, variants included: none may scroll it
    # or pad it again, which would put the bar back inside the scroll.
    for sels, decls in rules():
        for s in sels:
            last = s.split()[-1]
            if re.fullmatch(r"\.sheet(\.[\w-]+)*", last):
                assert not re.search(r"(?:^|\s)overflow(-y)?:\s*(auto|scroll)", decls), f"{s} scrolls the sheet"
                assert not re.search(r"(?:^|\s)padding(-top)?:", decls), f"{s} pads the sheet box"


def test_the_close_is_thumb_sized_and_inside_its_bar():
    close = rule(".sheet__close")
    size = px(close, "width")
    assert size == px(close, "height") and size >= 36, "the button itself shrank"
    assert re.search(r"min-height:\s*0", close), (
        "the global button min-height of 44px would stretch it into an oval"
    )
    grow = -px(rule(".sheet__close::after"), "inset")
    assert size + 2 * grow >= 44, "the hit area is under 44px"
    reach = px(close, "top") + size + grow
    assert reach <= px(rule(".sheet__top"), "height"), (
        "the hit area hangs out of the bar over the sheet's first line of content"
    )
