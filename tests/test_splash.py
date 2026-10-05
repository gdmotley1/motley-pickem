"""The splash is a real football thrown in a spiral, static in index.html.

Grant, 2026-10-05: "instead of the yellow football oval thing upon loading the webpage fresh
can we do something better or cooler". Off a board of six he took the spiral, then "the
football doesnt look real since the laces are going wrong way and always showing. make it
look like a real ball". So: a leather ball with four panel seams along its length, spinning
on that length, the laces riding one seam across the face and going behind once a turn.

It is static markup outside #root so it paints before the bundle runs, and App removes it
once the session check has answered. These pin all three pieces so none can drift alone.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def splash_markup():
    html = read("index.html")
    m = re.search(r'<div id="splash" class="splash"[^>]*>(.*?)</div>\s*<div id="root">', html, re.S)
    assert m, "index.html has no static #splash ahead of #root"
    return m.group(1)


def test_the_splash_is_static_markup_ahead_of_the_app_root():
    html = read("index.html")
    assert html.index('id="splash"') < html.index('id="root"'), "the splash must come before #root"
    assert 'aria-hidden="true"' in html[html.index('id="splash"') - 60: html.index('id="splash"') + 60]


def test_the_ball_is_a_real_one():
    """Four seams along the length, laces on the first with loops across it, the two bands
    of a college ball, leather, grain and shading. No oval."""
    body = splash_markup()
    assert len(re.findall(r'class="fb__seam fb__seam--\d"', body)) == 4, "the ball needs four panel seams"
    assert 'class="fb__lace"' in body and 'class="fb__loops"' in body, "laces ride a seam, loops across it"
    assert len(re.findall(r"<line ", body)) == 8, "eight lace loops"
    assert body.count('fill="#f4f0e6"') == 2, "two white bands near the tips"
    for ident in ("fb-leather", "fb-pebble", "fb-sheen", "fb-vignette", "fb-clip"):
        assert 'id="%s"' % ident in body, "the ball lost its %s" % ident
    assert "Motley<br />Pick'em" in body, "the wordmark under the ball"


def test_app_draws_nothing_while_checking_and_takes_the_splash_down_after():
    app = read("src", "App.jsx")
    assert "if (me === undefined) return null" in app, "App is drawing its own loading state again"
    assert "function Splash" not in app, "a React Splash is back; the splash is index.html's"
    assert "document.getElementById('splash')?.remove()" in app
    assert re.search(r"useEffect\(\(\) => \{\s*if \(me !== undefined\) document\.getElementById\('splash'\)\?\.remove\(\)\s*\}, \[me\]\)", app), (
        "the splash must come down in an effect keyed on `me`, after the first screen has painted"
    )


def test_the_styles_ship_and_the_oval_is_gone():
    css = read("src", "app.css")
    assert ".splash__ball" not in css or "border-radius: 50% / 58%" not in css, "the gold oval is back"
    assert "@keyframes bob" not in css
    splash = css[css.index(".splash {"): css.index(".toast {")]
    assert "position: fixed" in splash and "inset: 0" in splash, "the splash must cover the page's own background"
    for kf in ("fb-seam", "fb-lace", "fb-loops", "splash-streak"):
        assert "@keyframes %s" % kf in splash, "missing animation %s" % kf
    assert "prefers-reduced-motion" in splash
    # nothing under 13px on screen, the house rule
    sizes = [float(v) for v in re.findall(r"font-size:\s*([\d.]+)px", splash)]
    assert sizes and min(sizes) >= 13, sizes


def test_the_splash_keeps_the_jumbotron_tokens():
    """theme.css hands .splash the stadium's tokens; the wall colour comes from there."""
    theme = read("src", "theme.css")
    block = re.search(r"\[data-skin='jumbo'\],[^{]*\{", theme).group(0)
    assert ".splash" in block
    css = read("src", "app.css")
    assert "background: var(--page, #07080b)" in css[css.index(".splash {"): css.index(".splash__stage")]
