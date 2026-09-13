"""Grant's 13px floor for text, held where it has been fixed and ratcheted everywhere else.

He called the old record book "tiny text" on 2026-09-12 and then asked for the tab bar
and the header's week line to come up too. Those sit on every screen, so they are pinned by
name. The rest of the stylesheet still has text under 13px on other screens, and that is
held as a ceiling that only moves down: fix one, lower CEILING; add one, and this fails.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLOOR = 13.0

# Text on every screen, or on the tab where it was fixed. Each must be at least FLOOR.
PINNED = ("eyebrow", "apphdr__title", "apphdr__week", "apphdr__me", "tabbar__btn",
          "srow__ptslabel")

# Declarations under FLOOR left in src/app.css. 65 after 2026-09-12; 55 once the Week tab
# recap was rebuilt that night and its 9.5px labels went. Lower it as they get fixed.
CEILING = 55


def css():
    with open(os.path.join(ROOT, "src", "app.css"), encoding="utf-8") as f:
        return f.read()


def base_rule_size(sheet, klass):
    """The font-size in the class's own top-level rule, not a descendant or a variant."""
    rule = re.search(r"\n\.%s\s*\{(.*?)\n\}" % re.escape(klass), sheet, re.S)
    assert rule, ".%s has no rule of its own in app.css" % klass
    sizes = re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", rule.group(1))
    assert sizes, ".%s sets no px font-size" % klass
    return float(sizes[-1])


def test_the_text_on_every_screen_is_at_least_13px():
    sheet = css()
    small = {k: base_rule_size(sheet, k) for k in PINNED}
    small = {k: v for k, v in small.items() if v < FLOOR}
    assert not small, "under the %dpx floor: %s" % (FLOOR, small)


def test_no_rule_shrinks_a_pinned_label_again():
    """A later, more specific rule could quietly take a label back under the floor, the
    way book mode re-skins the header and tab bar. Walks every rule naming a pinned class."""
    sheet = css()
    for klass in PINNED:
        for selector, body in re.findall(r"([^{}]*\.%s\b[^{}]*)\{([^{}]*)\}" % re.escape(klass), sheet):
            for size in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", body):
                assert float(size) >= FLOOR, (
                    "%s sets %spx on .%s, under the floor" % (selector.strip(), size, klass)
                )


def test_tiny_text_only_ever_goes_down():
    sizes = [float(s) for s in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", css())]
    tiny = sum(1 for s in sizes if s < FLOOR)
    assert tiny <= CEILING, (
        "%d font sizes under %dpx in app.css, the ceiling is %d. Grant's floor is 13px: size "
        "new text at 13 or more." % (tiny, FLOOR, CEILING)
    )
    assert tiny >= CEILING - 5 or tiny == 0, (
        "only %d left under %dpx; lower CEILING in this file to %d so the gain is kept"
        % (tiny, FLOOR, tiny)
    )
