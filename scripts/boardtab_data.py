"""The example Saturday night every Board tab direction draws.

Week 1's real slate, picks and schools, frozen after game 15 of 20 in kickoff order
(UNLV at Hawaii). Fifteen games are final with their real scores. Two are live, with
in-game scores and clocks that are INVENTED for the example. The last three have not
kicked off, so only Grant's own pick shows, exactly as get_board would allow.
"""
from __future__ import annotations

import json
import os

from weektab_common import BY_NAME, ROOT, TEAMS

LIVE = json.load(open(os.path.join(ROOT, "outputs", "harness", "week_live.json"), encoding="utf-8"))
NAMES = ["Grant", "James", "Parker", "Nicole"]
ME = "Grant"
SLATE = {"%s@%s" % (g["away_abbr"], g["home_abbr"]): g for g in LIVE["slate"]}
ORDER = sorted(LIVE["slate"], key=lambda g: (g["kickoff"], g["game_id"]))
CUT = 15  # games final in the example

FINAL_IDS = {g["game_id"] for g in ORDER[:CUT]}
LIVE_STATE = {"CMU@UNM": (7, 24, "3rd", "4:12"), "WKU@NEV": (14, 21, "2nd", "1:45")}

SHOWN = [
    ("COLO@GT", "final"),
    ("UNLV@HAW", "final"),
    ("CMU@UNM", "live"),
    ("WKU@NEV", "live"),
    ("WIS@ND", "soon"),
]


def _rows(game_id):
    by = {r["player_name"]: r for r in LIVE["board"] if r["game_id"] == game_id}
    return [by[n] for n in NAMES]


def team(team_id):
    return TEAMS.get(team_id, {"abbr": "?", "school": "?", "bg": "#333333", "alt": "#555555"})


def standings():
    pts = {n: 0 for n in NAMES}
    right = {n: 0 for n in NAMES}
    played = 0
    for g in ORDER[:CUT]:
        played += 1
        for r in _rows(g["game_id"]):
            if r["pick_abbr"] == g["winner_abbr"]:
                pts[r["player_name"]] += r["confidence"]
                right[r["player_name"]] += 1
    in_play = {n: sum(r["confidence"] for g in ORDER[CUT:] for r in _rows(g["game_id"]) if r["player_name"] == n) for n in NAMES}
    order = sorted(NAMES, key=lambda n: (-pts[n], -right[n]))
    lead = pts[order[0]]
    out = []
    for i, n in enumerate(order):
        rank = 1 + sum(1 for m in NAMES if pts[m] > pts[n])
        out.append({"name": n, "team_id": BY_NAME[n]["team_id"], "team": team(BY_NAME[n]["team_id"]), "rank": rank,
                    "points": pts[n], "right": right[n], "wrong": played - right[n], "behind": lead - pts[n],
                    "in_play": in_play[n], "max": pts[n] + in_play[n], "me": n == ME})
    return out


def games():
    out = []
    for key, state in SHOWN:
        g = SLATE[key]
        away = {"abbr": g["away_abbr"], "id": g["away_id"], "school": g["away_school"], "team": team(g["away_id"])}
        home = {"abbr": g["home_abbr"], "id": g["home_id"], "school": g["home_school"], "team": team(g["home_id"])}
        if state == "final":
            away["score"], home["score"] = g["away_score"], g["home_score"]
            leader, clock, period = g["winner_abbr"], "Final", "Final"
        elif state == "live":
            a, h, period, clock = LIVE_STATE[key]
            away["score"], home["score"] = a, h
            leader = g["home_abbr"] if h > a else g["away_abbr"] if a > h else None
        else:
            away["score"] = home["score"] = None
            leader, period, clock = None, "Sat", "7:30 PM"
        picks = []
        for r in _rows(g["game_id"]):
            hidden = state == "soon" and r["player_name"] != ME
            pick_id = g["home_id"] if r["pick_abbr"] == g["home_abbr"] else g["away_id"]
            result = ("won" if r["pick_abbr"] == leader else "lost") if state == "final" else \
                     ("ahead" if r["pick_abbr"] == leader else "behind") if state == "live" and leader else "open"
            picks.append({"name": r["player_name"], "team_id": BY_NAME[r["player_name"]]["team_id"],
                          "pick": None if hidden else r["pick_abbr"], "pick_id": None if hidden else pick_id,
                          "confidence": None if hidden else r["confidence"], "result": "hidden" if hidden else result,
                          "me": r["player_name"] == ME})
        fav = g.get("favorite_abbr")
        line = ("%s -%g" % (fav, abs(float(g["spread_line"])))) if g.get("spread_line") is not None and fav else ""
        out.append({"key": key, "state": state, "away": away, "home": home, "period": period, "clock": clock,
                    "leader": leader, "line": line, "picks": picks})
    return out


STANDINGS = standings()
GAMES = games()
TOTALS = {"final": CUT, "live": len(LIVE_STATE), "slate": len(ORDER)}


def ticker():
    """Every other result on the slate, for the directions that run a crawl."""
    items = []
    for g in ORDER[:CUT]:
        items.append("%s %s  %s %s" % (g["away_abbr"], g["away_score"], g["home_abbr"], g["home_score"]))
    return items


if __name__ == "__main__":
    for s in STANDINGS:
        print(s["rank"], s["name"], s["points"], "%d-%d" % (s["right"], s["wrong"]), "in play", s["in_play"], "max", s["max"])
    for g in GAMES:
        print(g["key"], g["state"], g["away"].get("score"), g["home"].get("score"), g["leader"], g["line"],
              [(p["name"], p["pick"], p["confidence"], p["result"]) for p in g["picks"]])
