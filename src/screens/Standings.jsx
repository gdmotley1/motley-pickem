import { useEffect, useState } from 'react'
import * as api from '../lib/api.js'
import { Avatar, Empty, IconTrophy, Screen, Spinner } from '../components/ui.jsx'

/**
 * Season standings plus the two cuts worth arguing about: raw accuracy, and whether the
 * points you spent actually landed on the games you got right.
 */
export default function Standings() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    api
      .getStandings()
      .then((r) => alive && setRows(r))
      .catch((e) => alive && setError(e.message))
    return () => {
      alive = false
    }
  }, [])

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
