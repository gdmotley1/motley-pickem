"""Everything but Season's record book on the jumbotron, as Grant asked on 2026-09-13.

"It shows a white banner at the top that keeps the score going, but it doesn't fit the theme
at all. And so I need you to fix the setup tab, that little white piece, and anywhere else
that still shows, like, the old theme and design ... Same goes for the standings on the
season tab above the hall of fame. They don't fit the theme anymore. It looks dinky."

A sweep of the whole app in demo mode found the old look in the Board's pinned score strip,
Setup, sign-in and its PIN keypad, and every sheet: the account menu, Pick your team,
Reminders and the Week tab's week list. Season's header was the last old-look title. The
standings became trading cards ("ship the trading card one from before i liked that
better"), over an LED leaderboard, a podium and brass plaques and four variants of the podium.

What is guarded: one header on every tab; the strip names its own colors, because it is
portalled out of reach of the skin; the stadium's tokens reach every sheet, sign-in, the
toast and the splash, covering every color token Slate defines; the LED button lights outside
the wall; gold always carries dark lettering; the headings on the wall name their face; the
standings are one template of cards; nothing restyled here is under 13px.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def strip_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def rules(sheet):
    """(selectors, body) for every rule, comments stripped. Selectors split on commas."""
    out = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", strip_comments(sheet)):
        out.append(([s.strip() for s in sel.split(",")], body))
    return out


def rule(sheet, selector):
    for sels, body in rules(sheet):
        if selector in sels:
            return body
    raise AssertionError(f"{selector} has no rule")


def app_css():
    return read("src", "app.css")


def theme_css():
    return read("src", "theme.css")


def winning(body, prop):
    """The declaration of `prop` that applies: an !important one if any, else the last."""
    decls = re.findall(r"(?:^|[;\s])%s:\s*([^;]+);" % re.escape(prop), body)
    if not decls:
        return None
    return next((d for d in decls if "!important" in d), decls[-1]).strip()


# ------------------------------------------------------------------ one header


def test_every_tab_wears_the_same_header():
    """Season kept the book's wool header and an Archivo title until 2026-09-13. The header
    and tab bar rules are now written for every .app, and nothing re-skins them per tab."""
    css = app_css()
    hdr = rule(css, ".app .apphdr")
    assert "#07080b" in hdr, "the header is no longer the jumbotron's black"
    assert "'Big Shoulders Display'" in winning(rule(css, ".app .apphdr__title"), "font-family")
    assert "#ffb020" in rule(css, ".app .tabbar__btn.is-on"), "the on tab is no longer amber"
    for sels, _ in rules(css):
        for s in sels:
            if re.search(r"\.(apphdr|tabbar)\b", s) and re.search(r"\[data-(mode|skin)=", s):
                raise AssertionError(f"{s} re-skins the header or tab bar for one tab again")


# ------------------------------------------------------------------ the score strip


def test_the_score_strip_names_its_own_colors():
    """ScoreBug portals into document.body so it can stay fixed. A rule written against
    .app[data-skin='jumbo'] can never reach it, which is exactly how it stayed white."""
    css = app_css()
    assert "rgba(3, 4, 6" in rule(css, ".wkbug__bar"), "the strip is not the jumbotron's black"
    for sels, _ in rules(css):
        for s in sels:
            if "wkbug" in s and ("[data-skin" in s or ".app" in s):
                raise AssertionError(f"{s} targets the strip through .app, which it is portalled out of")
    names = float(re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", rule(css, ".wkbug__p"))[-1])
    points = float(re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", rule(css, ".wkbug__p b"))[-1])
    assert names >= 13 and points >= 13, (names, points)
    assert "grid-template-areas" in rule(css, ".wkbug__p"), (
        "names back on one line with the score: four of them cut to GRA... at a phone's width"
    )


# ------------------------------------------------------------------ the tokens


def test_the_stadium_tokens_reach_what_lives_outside_the_app():
    """Sheets, the toast and the splash portal or render outside .app, and sign-in renders
    before it exists, so each has to be named in the token block itself."""
    blocks = [sels for sels, _ in rules(theme_css()) if "[data-skin='jumbo']" in sels]
    assert len(blocks) == 1, "expected exactly one jumbotron token block in theme.css"
    for needed in ("[data-skin='jumbo']", ".sheet", ".signin", ".toast", ".splash"):
        assert needed in blocks[0], f"{needed} no longer gets the jumbotron's tokens"


def test_the_stadium_tokens_cover_every_color_slate_defines():
    """Walks :root rather than listing names: any color token Slate defines and the block
    forgets would render Slate's light value on the jumbotron."""
    theme = strip_comments(theme_css())
    root = re.search(r":root\s*\{([^{}]*)\}", theme).group(1)
    color_tokens = {
        name for name, value in re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", root)
        if re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|var\(--(s|c|b|gr|rd)-", value)
        and not re.match(r"--(s|c|b|gr|rd)-\d", name)  # the palette ramps themselves
    }
    block = next(body for sels, body in rules(theme_css()) if "[data-skin='jumbo']" in sels)
    defined = set(re.findall(r"(--[a-z0-9-]+):", block))
    missing = sorted(color_tokens - defined)
    assert len(color_tokens) >= 25, "found almost no color tokens; the walk is reading the wrong block"
    assert not missing, f"the jumbotron token block leaves these at Slate's value: {missing}"


# ------------------------------------------------------------------ buttons and gold


def test_the_led_button_lights_outside_the_wall():
    """.btn--led first read its amber from .jb's variables, which a sheet, sign-in and
    Setup do not have: the button would have painted nothing."""
    css = app_css()
    for sel in (".btn.btn--led", ".btn.btn--led:disabled", ".btn.btn--led-ghost"):
        assert "var(--jb-" not in rule(css, sel), f"{sel} depends on .jb's variables again"


def test_no_primary_button_is_left_in_the_old_look():
    """Walks every component: a bare className="btn" is Slate's dark-blue button."""
    bare = []
    for dirpath, _, files in os.walk(SRC):
        for name in files:
            if name.endswith(".jsx"):
                body = read(os.path.relpath(os.path.join(dirpath, name), ROOT))
                if re.search(r'className="btn"', body):
                    bare.append(name)
    assert not bare, f"a plain .btn is still drawn in: {bare}"


def test_gold_always_carries_dark_lettering():
    """The selection is gold on the jumbotron; white on it is unreadable. Walks every rule
    that paints --pick behind itself."""
    for sels, body in rules(app_css()):
        bg = winning(body, "background")
        color = winning(body, "color")
        if bg and "var(--pick)" in bg and color:
            assert color.lower() not in ("#fff", "#ffffff", "white"), f"{sels}: white on gold"


def test_setup_rows_name_their_text_color():
    """The rows are buttons, which do not inherit color: the games went dark on the wall."""
    assert winning(rule(app_css(), ".arow"), "color") == "var(--ink)"


# ------------------------------------------------------------------ lettering


def test_the_headings_on_the_wall_name_their_face():
    """theme.css hands every h1, h2 and h3 Archivo, and a rule on the element beats the face
    inherited from the wall (memory/traps.md)."""
    css = app_css()
    for sel in (".sheet__title", ".signin__title", ".sheet .h2", ".adm__dayhead",
                "[data-skin='jumbo'] .h1", ".scard__name"):
        face = winning(rule(css, sel), "font-family")
        assert face and "'Big Shoulders Display'" in face, f"{sel} is not in the LED lettering"


def test_nothing_restyled_here_is_under_13px():
    """Walks every rule for the pieces this change restyled, wherever they sit in app.css."""
    families = r"\.(sheet|signin|seat|key|pin|label|field|adm__|fchip|arow|chip|tpick__|wkrow|notif|switch|wkbug|scard|standings|update|toast|btn)"
    small = []
    for sels, body in rules(app_css()):
        if any(re.search(families, s) for s in sels):
            for size in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", body):
                if float(size) < 13:
                    small.append(f"{', '.join(sels)} {size}px")
    assert not small, f"under 13px: {small}"


# ------------------------------------------------------------------ the standings


def test_the_standings_are_one_template_of_trading_cards():
    season = read("src", "screens", "Season.jsx")
    start = season.index("function Standings(")
    body = season[start: season.index("\nfunction ", start + 1)]
    assert body.count('className="scard__name"') == 1, "the cards are no longer one template"
    assert "players.map((p) =>" in body
    assert "p.points === lead ? ' is-lead'" in body, "a tie for first no longer makes two gold cards"
    assert "__standings" not in season, "the options board's switch shipped"
    css = app_css()
    for gone in (".srow", ".stand {", ".pod", ".plaque", ".st1", ".st2", ".st3"):
        assert gone not in css, f"a replaced or rejected standings rule is still in app.css: {gone}"
    name = rule(css, ".scard__name")
    assert "text-overflow: ellipsis" in name and "white-space: nowrap" in name, (
        "a long claimed name would push its card wider than the column"
    )
