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
