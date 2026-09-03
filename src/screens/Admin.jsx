import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import TeamLogo from '../components/TeamLogo.jsx'
import { Empty, IconClock, Screen, Spinner, Toast } from '../components/ui.jsx'
import { kickoffLabel } from '../lib/format.js'

const SLATE_SIZE = 20

/**
 * Where Dad builds the week. Forty candidate games, the best twenty already ticked, and
 * one tap to swap any of them. Publish writes the slate and opens it to the family.
 */
export default function Admin({ weekId }) {
  const [pool, setPool] = useState(null)
  const [chosen, setChosen] = useState(() => new Set())
  const [view, setView] = useState('slate') // slate | pool
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    let alive = true
    api
      .getPool(weekId)
      .then((rows) => {
        if (!alive) return
        setPool(rows)
        setChosen(new Set(rows.filter((g) => g.in_slate).map((g) => g.game_id)))
      })
      .catch((e) => alive && setError(e.message))
    return () => {
      alive = false
    }
  }, [weekId])

  const shown = useMemo(() => {
    if (!pool) return []
    return view === 'slate' ? pool.filter((g) => chosen.has(g.game_id)) : pool
  }, [pool, view, chosen])

  function toggle(g) {
    if (g.locked) {
      setToast('That game has already kicked off.')
      return
    }
    setError(null)
    setChosen((cur) => {
      const next = new Set(cur)
      if (next.has(g.game_id)) {
        next.delete(g.game_id)
      } else {
        if (next.size >= SLATE_SIZE) {
          setToast(`That is already ${SLATE_SIZE} games. Remove one first.`)
          return cur
        }
        next.add(g.game_id)
      }
      navigator.vibrate?.(8)
      return next
    })
  }

  async function publish() {
    setBusy(true)
    setError(null)
    try {
      await api.publishSlate(weekId, [...chosen])
      setToast('Published. Everyone can pick now.')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (error && !pool) return <p className="err">{error}</p>
  if (!pool) return <Spinner />
  if (!pool.length)
    return (
      <Screen eyebrow="Commissioner" title="Build the week">
        <Empty icon={<IconClock />} title="No games loaded">
          The weekly pull has not run yet for this week.
        </Empty>
      </Screen>
    )

  const count = chosen.size
  const ready = count === SLATE_SIZE

  return (
    <Screen
      eyebrow="Commissioner"
      title="Build the week"
      sub={`Pick ${SLATE_SIZE} from ${pool.length}. The best ${SLATE_SIZE} are already ticked, sourced from ESPN's top games and balanced so the confidence points still mean something.`}
    >
      <div className="adm__tabs" role="tablist">
        <button
          role="tab"
          aria-selected={view === 'slate'}
          className={`adm__tab${view === 'slate' ? ' is-on' : ''}`}
          onClick={() => setView('slate')}
        >
          The {SLATE_SIZE} ({count})
        </button>
        <button
          role="tab"
          aria-selected={view === 'pool'}
          className={`adm__tab${view === 'pool' ? ' is-on' : ''}`}
          onClick={() => setView('pool')}
        >
          All {pool.length}
        </button>
      </div>

      {view === 'slate' && count === 0 && (
        <Empty icon={<IconClock />} title="Nothing selected">
          Switch to “All {pool.length}” and tick the games you want.
        </Empty>
      )}

      <ul className="alist">
        {shown.map((g) => {
          const on = chosen.has(g.game_id)
          return (
            <li key={g.game_id}>
              <button
                className={`arow${on ? ' is-in' : ''}`}
                onClick={() => toggle(g)}
                disabled={g.locked}
                aria-pressed={on}
              >
                <span className="arow__box" aria-hidden="true">
                  ✓
                </span>
                <span className="arow__logos">
                  <TeamLogo teamId={g.away_id} abbr={g.away_abbr} size={22} />
                  <TeamLogo teamId={g.home_id} abbr={g.home_abbr} size={22} />
                </span>
                <span className="arow__body">
                  <span className="arow__match">
                    {g.away_abbr} {g.neutral_site ? 'vs' : '@'} {g.home_abbr}
                  </span>
                  {/* One status chip only. Three of them wrapped onto a second line and
                      made every row twice as tall. */}
                  <span className="arow__meta">
                    <span>{kickoffLabel(g.kickoff)}</span>
                    <span className="num">{api.spreadLabel(g)}</span>
                    {g.locked ? (
                      <span className="chip chip--red">kicked off</span>
                    ) : g.featured ? (
                      <span className="chip chip--amber">ESPN top</span>
                    ) : g.tier ? (
                      <span className="chip">{g.tier}</span>
                    ) : null}
                  </span>
                </span>
              </button>
            </li>
          )
        })}
      </ul>

      {error && <p className="err">{error}</p>}

      <div className="stickycta">
        <button className="btn" onClick={publish} disabled={!ready || busy}>
          {busy
            ? 'Publishing…'
            : ready
              ? `Publish these ${SLATE_SIZE} games`
              : count < SLATE_SIZE
                ? `Add ${SLATE_SIZE - count} more`
                : `Remove ${count - SLATE_SIZE}`}
        </button>
      </div>

      <Toast message={toast} onDone={() => setToast(null)} />
    </Screen>
  )
}
