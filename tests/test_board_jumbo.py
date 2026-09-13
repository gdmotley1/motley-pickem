"""The Board as the jumbotron Grant picked on 2026-09-12, with his one change.

"lets do 1 its phenomenal ... change the part where it shows the team we picked and points.
put that teams logo not our profile logo." The players' avatars are school logos too, so
beside "GT" an Arkansas avatar read as the pick.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def chip_body():
    body = read("src", "screens", "Board.jsx")
    start = body.index("function Chip(")
    return body[start: body.index("\nfunction ", start + 10)]


def test_a_pick_carries_the_picked_teams_logo_not_the_players():
    chip = chip_body()
    assert "<Mark id={teamId}" in chip, "the pick chip no longer draws the picked school's mark"
    assert "<Avatar" not in chip, "a pick chip is showing the player's avatar again"
    body = read("src", "screens", "Board.jsx")
    assert "teamId={idFor(game, p.pick_abbr)}" in body and "teamId={idFor(game, game.my_pick)}" in body


def test_the_leaderboard_reads_the_same_score_as_everything_else():
    body = read("src", "screens", "Board.jsx")
    assert "weekScore(games, rows, roster)" in body
    assert "<Leaderboard score={score}" in body
    assert "score.players.map" in body


def test_an_unplayed_pick_stays_hidden():
    """Visibility is the server's, but the tile must never try to draw another player's pick
    before kickoff: only your own card shows."""
    body = read("src", "screens", "Board.jsx")
    assert "if (!mine) return <Chip key={player.id} name={player.name} state=\"hidden\" />" in body


def test_the_board_wears_its_skin_only_on_its_own_tab():
    app = read("src", "App.jsx")
    assert "tab === 'board' ? 'jumbo' : undefined" in app


def test_the_lettering_it_is_set_in_is_loaded():
    link = re.search(r'href="(https://fonts\.googleapis\.com/css2[^"]+)"', read("index.html")).group(1)
    assert "family=Big+Shoulders+Display:wght@800;900" in link


def test_nothing_on_the_jumbotron_is_under_13px():
    css = read("src", "app.css")
    start = css.index("/* ================================================== board: the jumbotron === */")
    block = css[start: css.index("/* ====================================================== the pick nudge ===== */", start)]
    small = [s for s in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", block) if float(s) < 13]
    assert not small, "under 13px on the jumbotron: %s" % small
