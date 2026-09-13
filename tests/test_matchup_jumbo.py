"""The matchup preview sheet on the jumbotron, as Grant picked it on 2026-09-13.

Three rounds that day. The first put each team in a box lit in its school colors; he said
"those boxes with the color looks weird. I want the logo bigger and uniform text and ranking
under it. Make it easier to see the spread and over under and channel." The second gave
three tops; he took the logo plates as best but did not love them. From an artifact of six
he said "lets do 8": the two teams as trading cards. Below the cards he kept round one's
option 1, big LED win percentages and a column of chips per team.

What is guarded: only this sheet goes dark, the two cards are one template and stay level
whatever the names, no school color on the cards, the pick ribbon never moves a card, TV
and spread and total as three labelled tiles, one rank style, nothing under 13px, and none
of the rejected options' code left behind. tests/test_matchup.py still holds the sections
below (the clamped preview line, the heading's margin reset).
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def css():
    return re.sub(r"/\*.*?\*/", "", read("src", "app.css"), flags=re.S)


def matchup():
    return read("src", "components", "Matchup.jsx")


def rules(sheet):
    """(selector, body) for every rule in the stylesheet, comments already stripped."""
    return [(s.strip(), b) for s, b in re.findall(r"([^{}]+)\{([^{}]*)\}", sheet)]


def rule(sheet, selector):
    for s, b in rules(sheet):
        if selector in [part.strip() for part in s.split(",")]:
            return b
    raise AssertionError(f"{selector} has no rule in app.css")


def px(body, prop):
    m = re.search(r"(?:^|;|\s)%s:\s*(\d+(?:\.\d+)?)px" % re.escape(prop), body)
    return float(m.group(1)) if m else None


def cards_component():
    body = matchup()
    start = body.index("function Cards(")
    return body[start: body.index("\nfunction ", start + 1)]


# ------------------------------------------------------------------ only this sheet


def test_only_the_matchup_sheet_goes_dark():
    """Sheet is shared by the account sheet, both team pickers, Reminders, sign in and the
    Week tab's jump list. Walks every <Sheet in src rather than listing them, so a new sheet
    is covered the day it is added."""
    tones = {}
    for dirpath, _, files in os.walk(SRC):
        for name in files:
            if not name.endswith(".jsx"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as f:
                # Braced attributes whole: onClose={() => ...} has a > of its own.
                for tag in re.findall(r"<Sheet\b(?:[^>{}]|\{[^{}]*\})*>", f.read()):
                    tones.setdefault(os.path.relpath(path, SRC), []).append(tag)
    toned = {p: t for p, tags in tones.items() for t in tags if "tone=" in t}
    assert len(tones) >= 5, "found almost no sheets; the walk is looking in the wrong place"
    assert list(toned) == [os.path.join("screens", "Picks.jsx")], (
        "only the matchup preview may put a sheet on the jumbotron: %s" % toned
    )
    assert 'label="Matchup preview" tone="jumbo"' in next(iter(toned.values()))

    sheet = rule(css(), ".sheet")
    assert "background: var(--card)" in sheet, ".sheet itself was restyled; every light sheet went with it"


def test_the_sheet_is_opt_in_in_one_place():
    ui = read("src", "components", "ui.jsx")
    assert "export function Sheet({ open, onClose, label, tone, children })" in ui
    assert "sheet--${tone}" in ui


# ------------------------------------------------------------------ the cards


def test_both_cards_are_one_template():
    """Uniform was the whole ask. Two hand-built cards drift; one map cannot."""
    body = cards_component()
    assert body.count('className="mu__cardname"') == 1
    assert body.count("<Mark ") == 1, "each card must draw its logo from the same line"
    assert re.search(r"sides\.map\(\(s\) => \(\s*<div key=\{s\.side\} className=\{`mu__card", body), (
        "the cards are no longer one map over the two sides"
    )


def test_the_cards_carry_no_school_color():
    """He called the school-colored team boxes weird. Color stays on the probability bar."""
    body = cards_component()
    for tell in ("schoolPanel", "panel(", "--jb-team", "schoolField"):
        assert tell not in body, f"the cards reach for school color again ({tell})"
    sheet = css()
    for selector, rule_body in rules(sheet):
        if re.search(r"\.mu__(head|card|stage|cardname|cardstats|ribbon)\b", selector):
            assert "--jb-team" not in rule_body, f"{selector} paints a school color"


def test_the_logo_is_big_and_the_same_on_both_cards():
    body = cards_component()
    m = re.search(r"<Mark id=\{s\.id\} abbr=\{s\.abbr\} size=\{(\d+)\} />", body)
    assert m and int(m.group(1)) >= 96, "the logo shrank below the size Grant asked to be bigger"


def test_names_step_down_together_and_stats_stay_level():
    """72 of 222 real school names do not fit a card at full size (measured 2026-09-13 in the
    harness); every one of the 139 in the team library fits by the second step. Both names
    share one size, and the name bar takes the spare height so a two-line FCS name never
    pushes its card's stats out of line with the other card's."""
    body = cards_component()
    assert "querySelectorAll('.mu__cardname')" in body
    assert "setFit((f) => (f < 2 ? f + 1 : f))" in body, "the fit must step down, at most twice"
    assert "setFit(0)" not in body, (
        "a reset raced the step: React flushes passive effects before the layout effect's update"
    )
    sheet = css()
    base = px(rule(sheet, ".mu__cardname"), "font-size")
    fit1 = px(rule(sheet, ".mu__head.is-fit1 .mu__cardname"), "font-size")
    fit2 = px(rule(sheet, ".mu__head.is-fit2 .mu__cardname"), "font-size")
    assert base > fit1 > fit2 >= 13, (base, fit1, fit2)
    assert re.search(r"(?:^|\s)flex:\s*1\b", rule(sheet, ".mu__cardname")), (
        "without flex: 1 a wrapped name moves its card's stats down"
    )


def test_the_pick_ribbon_never_moves_a_card():
    sheet = css()
    assert "position: absolute" in rule(sheet, ".mu__ribbon")
    stage = rule(sheet, ".mu__stage")
    m = re.search(r"padding:\s*(\d+)px", stage)
    assert m and int(m.group(1)) >= 20, (
        "the stage must keep the ribbon's strip on both cards, or a tall logo sits under it"
    )


def test_the_at_sign_floats_outside_the_grid():
    """An absolutely placed grid item measures left and top from its own cell: with a grid
    column set, the @ landed on the home team's logo."""
    at = rule(css(), ".mu__at")
    assert "position: absolute" in at
    assert "grid-column" not in at and "grid-row" not in at and "grid-area" not in at


def test_there_is_still_one_rank_style():
    """tests/test_theme.py: <Rank> and .aprank only. A '#' typed into a template is a second one."""
    body = cards_component()
    assert "<Rank n={s.rank} />" in body
    assert "`#${" not in matchup(), "a rank is being written out by hand"


# ------------------------------------------------------------------ the line


def test_tv_spread_and_total_are_three_labelled_tiles():
    body = matchup()
    labels = re.findall(r'<span className="mu__statk">([^<]+)</span>', body)
    assert labels == ["TV", "Spread", "O/U"], labels
    assert body.count('className="mu__statv') == 3
    sheet = css()
    assert px(rule(sheet, ".mu__statv"), "font-size") >= 26, "the values are meant to be easy to see"


# ------------------------------------------------------------------ the lettering


def test_the_sheet_headings_name_the_led_face():
    """An h2 or h4 takes the Slate display face from theme.css, not the wall it sits on."""
    sheet = css()
    for selector in (".mu__title", ".mu__h"):
        # The declaration that wins: an !important one if any, else the last.
        decls = re.findall(r"font-family:\s*([^;]+);", rule(sheet, selector))
        assert decls, f"{selector} names no face, so it takes Archivo from theme.css"
        winning = next((d for d in decls if "!important" in d), decls[-1])
        assert "'Big Shoulders Display'" in winning, f"{selector} fell back to {winning}"


def test_nothing_on_the_matchup_sheet_is_under_13px():
    """Walks every rule that names the sheet anywhere in app.css, not one section of it."""
    small = []
    for selector, body in rules(css()):
        if re.search(r"\.mu\b|\.mu__|sheet--jumbo", selector):
            for size in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", body):
                if float(size) < 13:
                    small.append(f"{selector} {size}px")
    assert not small, "under 13px on the matchup sheet: %s" % small


# ------------------------------------------------------------------ the options are gone


def test_none_of_the_rejected_options_shipped():
    body = matchup()
    for tell in ("__muTop", "__muLook", "variant", "LampBar", "FormLamps", "FaceOff"):
        assert tell not in body, f"options-board code left in Matchup.jsx: {tell}"
    sheet = css()
    for gone in (".mu__head--", ".mu__plate2", ".mu__poster", ".mu__half", ".mu__bank",
                 ".mu__mod", ".mu__tile", ".mu__team", ".pbar", ".form__"):
        assert gone not in sheet, f"a rejected option's rule is still in app.css: {gone}"
