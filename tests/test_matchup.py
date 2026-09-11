"""The verification gate for the matchup preview's data shaping.

src/lib/matchup.js is JavaScript, so the assertions live in tests/matchup_check.mjs and
this module runs them under node and surfaces the output. Keeping them in the pytest run
means `python -m pytest tests/ -q` stays the one gate for the whole project rather than
two commands someone has to remember.

Runs against tests/fixtures/espn_summaries.json, never the live network, so it is
deterministic and works offline. Regenerate the fixture when ESPN changes shape:

    python - <<'PY'
    import json, urllib.request
    S = ("https://site.api.espn.com/apis/site/v2/sports/football/college-football")
    get = lambda u: json.load(urllib.request.urlopen(u, timeout=40))
    out = {}
    for name, eid in (("pregame", "401858425"), ("final", "401864425")):
        d = get(f"{S}/summary?event={eid}")
        out[name] = {k: d.get(k) for k in
                     ("predictor", "header", "lastFiveGames", "gameInfo")}
    json.dump(out, open("tests/fixtures/espn_summaries.json", "w"), indent=1)
    PY

Pick the two events for what they prove, not for who is playing: one game that has not
kicked off, so ESPN still publishes a predictor, and one already final, where ESPN has
dropped both the odds and the projection.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "tests", "matchup_check.mjs")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "espn_summaries.json")

# node ships with the toolchain this project already needs for `npm run build`, but the
# suite must not fail on a machine that only has Python.
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not on PATH")


def test_fixture_holds_both_game_states():
    with open(FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    assert set(fx) == {"pregame", "final"}
    assert fx["pregame"]["predictor"], "the pre-game fixture must carry a predictor"
    assert fx["final"]["predictor"] is None, (
        "the final fixture must have no predictor: that is the whole point of it, and "
        "ESPN dropping the block is what the no-projection branch renders for"
    )


@needs_node
def test_matchup_normalisation():
    proc = subprocess.run(
        [node, CHECK], capture_output=True, text=True, cwd=ROOT, timeout=60
    )
    # The .mjs prints one line per check, so a failure reads as a report rather than a
    # bare non-zero exit.
    assert proc.returncode == 0, "\n" + proc.stdout + proc.stderr


def test_the_preview_line_is_rendered_and_can_hide_itself():
    """ESPN writes a headline for big games and nothing for most others, so the section
    has to disappear rather than reserve an empty box. Added 2026-09-11."""
    with open(os.path.join(ROOT, "src", "components", "Matchup.jsx"), encoding="utf-8") as f:
        body = f.read()
    assert "data.story &&" in body, (
        "the preview section is not conditional, so a game ESPN ignored gets an empty box"
    )
    assert 'className="mu__story"' in body, "the preview line is not rendered"


def test_the_preview_line_is_clamped():
    """A bottom sheet on a phone is not an article. ESPN occasionally writes a long one
    and an unclamped quotation would push the venue off the bottom."""
    with open(os.path.join(ROOT, "src", "app.css"), encoding="utf-8") as f:
        css = f.read()
    import re
    m = re.search(r"^\.mu__story\s*\{(.*?)^\}", css, re.S | re.M)
    assert m, ".mu__story is gone"
    rule = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
    assert "-webkit-line-clamp" in rule, "the preview line is not clamped"
    assert "overflow: hidden" in rule, "line-clamp does nothing without overflow hidden"


def test_the_section_heading_has_no_default_top_margin():
    """The sheet's spacing bug, and the reason it survived being looked at.

    .mu__h set margin-bottom and left margin-top alone, so the browser's default 1.33em
    on an <h4> added 15.3px above every heading on top of the section's own 12px padding.
    Measured on a 375px iPhone: each section was 68px tall to show 17px of content, and
    the sheet was 460px. Resetting it took sections to 53px and the sheet to 414px, while
    ADDING the ESPN preview section.

    Grant asked for this after the sheet read as empty and spaced out, which is what a
    15px hole above every heading looks like.
    """
    import re
    with open(os.path.join(ROOT, "src", "app.css"), encoding="utf-8") as f:
        css = f.read()
    m = re.search(r"^\.mu__h\s*\{(.*?)^\}", css, re.S | re.M)
    assert m, ".mu__h is gone"
    rule = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
    assert re.search(r"margin:\s*0", rule) or re.search(r"margin-top:\s*0", rule), (
        "the heading's top margin is unreset again, which puts 15px of dead space above "
        "every section of the sheet"
    )
