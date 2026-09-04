import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { Avatar, Empty, IconTrophy, Screen, Spinner } from '../components/ui.jsx'
import { liveWinner } from '../lib/espn.js'
import { useLiveScores } from '../lib/useLiveScores.js'

/**
 * Season standings plus the two cuts worth arguing about: raw accuracy, and whether the
 * points you spent actually landed on the games you got right.
 */
export default function Standings({ weekId }) {
  const [base, setBase] = useState(null)
  const [slate, setSlate] = useState(null)
  const [picks, setPicks] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    Promise.all([api.getStandings(), api.getSlate(weekId), api.getBoard(weekId)])
      .then(([totals, sl, b]) => {
        if (!alive) return
        setBase(totals)
        setSlate(sl)
        setPicks(b)
      })
      .catch((e) => alive && setError(e.message))
    return () => {
      alive = false
    }
  }, [weekId])

  const live = useLiveScores(slate)

  /**
   * Season totals, plus this week's games that are over but not yet graded.
   *
   * get_standings counts a game only once games.winner_abbr is set, so a game stays
   * missing from the totals however long ago it actually finished, and the sync job that
   * sets it can be an hour late. Those picks are already in the board rows, so the same
   * arithmetic the server does is redone here and added on top. Nothing is counted
   * twice: a game the database has graded is skipped by the first condition.
   */
  const rows = useMemo(() => {
    if (!base) return null
    if (!live || !slate || !picks) return base

    const delta = new Map()
    for (const g of slate) {
      if (g.winner_abbr) continue
      const winner = liveWinner(g, live)
      if (!winner) continue
      for (const p of picks) {
        if (p.game_id !== g.game_id) continue
        const d = delta.get(p.player_id) || { correct: 0, games: 0, points: 0 }
        d.games += 1
        if (p.pick_abbr === winner) {
          d.correct += 1
          d.points += p.confidence
        }
        delta.set(p.player_id, d)
      }
    }
    if (!delta.size) return base

    return base
      .map((r) => {
        const d = delta.get(r.player_id)
        if (!d) return r
        return {
          ...r,
          correct: r.correct + d.correct,
          games: r.games + d.games,
          points: r.points + d.points,
        }
      })
      // Same order the server uses: points, then games called right.
      .sort((a, b) => b.points - a.points || b.correct - a.correct)
  }, [base, slate, picks, live])

  if (error) return <p className="err">{error}</p>
  if (!rows) return <Spinner />

  const played = rows.filter((r) => r.games > 0)

  if (!played.length)
    return (
      <Screen eyebrow="Season" title="Standings">
        <Empty icon={<IconTrophy />} title="No results yet">
          Once games start going final, the leaderboard fills in here with points, records
          and a few stats worth arguing about.
        </Empty>
      </Screen>
    )

  const maxPts = Math.max(...played.map((r) => r.points), 1)
  // Ties share a position: co-champions, per the house rule.
  let lastPts = null
  let lastPos = 0

  return (
    <Screen eyebrow="Season" title="Standings" sub="Ties stand. Two people can share a week.">
      <div className="stand">
        {played.map((r, i) => {
          if (r.points !== lastPts) {
            lastPos = i + 1
            lastPts = r.points
          }
          const pct = r.games ? Math.round((r.correct / r.games) * 100) : 0
          return (
            <div key={r.player_id} className={`srow${lastPos === 1 ? ' is-leader' : ''}`}>
              <span className="srow__pos num">{lastPos}</span>
              <Avatar name={r.player_name} color={r.player_color} size={36} />
              <span className="srow__body">
                <span className="srow__name">{r.player_name}</span>
                <span className="srow__meta num">
                  {r.correct}-{r.games - r.correct} · {pct}% right
                </span>
              </span>
              <span>
                <span className="srow__pts num">{r.points}</span>
                <span className="srow__ptslabel">pts</span>
              </span>
            </div>
          )
        })}
      </div>

      <div className="screen">
        <h3 className="h2">Points</h3>
        <p className="sub">Total confidence points banked on correct picks.</p>
      </div>
      <div className="bars">
        {played.map((r) => (
          <div className="bar" key={r.player_id}>
            <span className="bar__name">{r.player_name}</span>
            <span className="bar__track">
              <span
                className="bar__fill"
                style={{
                  width: `${(r.points / maxPts) * 100}%`,
                  background: r.player_color,
                }}
              />
            </span>
            <span className="bar__val num">{r.points}</span>
          </div>
        ))}
      </div>

      <div className="screen">
        <h3 className="h2">Accuracy</h3>
        <p className="sub">
          Share of picks that came in. High points with low accuracy means you are spending
          big numbers on the right games.
        </p>
      </div>
      <div className="bars">
        {played.map((r) => {
          const pct = r.games ? (r.correct / r.games) * 100 : 0
          return (
            <div className="bar" key={r.player_id}>
              <span className="bar__name">{r.player_name}</span>
              <span className="bar__track">
                <span
                  className="bar__fill"
                  style={{ width: `${pct}%`, background: r.player_color }}
                />
              </span>
              <span className="bar__val num">{Math.round(pct)}%</span>
            </div>
          )
        })}
      </div>
    </Screen>
  )
}
