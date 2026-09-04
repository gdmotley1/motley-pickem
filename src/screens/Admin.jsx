import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import TeamLogo from '../components/TeamLogo.jsx'
import { Empty, IconClock, Screen, Spinner, Toast } from '../components/ui.jsx'
import { dayKey, dayLabel, kickoffLabel } from '../lib/format.js'
import { availableConferences, inConference } from '../lib/conferences.js'

const SLATE_SIZE = 20

/** What the search box matches: both abbreviations and both school names. */
const haystack = (g) =>
  `${g.away_abbr} ${g.home_abbr} ${g.away_school || ''} ${g.home_school || ''}`.toLowerCase()

/**
 * Rows cut into day sections, in the order they arrive.
 *
 * get_pool already orders by kickoff, so this only has to notice where the local date
 * changes. Local, not Eastern: the headings have to agree with the times printed under
 * them, and a west-coast night game is still "Saturday" to the person reading it.
 */
function byDay(rows) {
  const out = []
  for (const g of rows) {
    const key = dayKey(g.kickoff)
    if (out[out.length - 1]?.key !== key) out.push({ key, label: dayLabel(g.kickoff), games: [] })
    out[out.length - 1].games.push(g)
  }
  return out
}

/**
 * Where Dad builds the week. Every FBS game in the window, the best twenty already
 * ticked, and one tap to swap any of them. Publish writes the slate and opens it to
 * the family.
 *
 * The pool was the top forty by interest until 2026-09-04, which quietly hid fifty of
 * the ninety-one games in a week. Grant asked for Kennesaw State as the example: it
 * ranked 39th of 70 alternates, so the cap alone put it out of Dad's reach. Ninety-one
 * rows only work on a phone with a way to cut them down, which is what the search box
 * and the conference chips are for.
 */
export default function Admin({ weekId }) {
  const [pool, setPool] = useState(null)
  const [chosen, setChosen] = useState(() => new Set())
  const [view, setView] = useState('slate') // slate | pool
  const [query, setQuery] = useState('')
  const [conf, setConf] = useState(null) // conference id, or null for every conference
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

  const conferences = useMemo(() => availableConferences(pool), [pool])

  const shown = useMemo(() => {
    if (!pool) return []
    // The twenty is short enough to read whole, so the filters only apply to the pool.
    if (view === 'slate') return pool.filter((g) => chosen.has(g.game_id))
    let rows = pool
    if (conf !== null) rows = rows.filter((g) => inConference(g, conf))
    const needle = query.trim().toLowerCase()
    if (needle) rows = rows.filter((g) => haystack(g).includes(needle))
    return rows
  }, [pool, view, chosen, conf, query])

  const sections = useMemo(() => byDay(shown), [shown])

  function clearFilters() {
    setQuery('')
    setConf(null)
  }

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
  const filtered = view === 'pool' && (conf !== null || query.trim() !== '')

  return (
    <Screen
      eyebrow="Commissioner"
      title="Build the week"
      sub={`Pick ${SLATE_SIZE} from all ${pool.length} games. The best ${SLATE_SIZE} are already ticked, sourced from ESPN's top games and balanced so the confidence points still mean something. Search for any other game you want in.`}
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
          Every game ({pool.length})
        </button>
      </div>

      {view === 'pool' && (
        <div className="adm__filters">
          <div className="adm__search">
            <SearchIcon />
            <input
              type="search"
              className="adm__input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search a team, e.g. Kennesaw"
              aria-label="Search for a team"
              autoCapitalize="off"
              autoCorrect="off"
              spellCheck={false}
              enterKeyHint="search"
            />
            {query && (
              <button className="adm__clear" onClick={() => setQuery('')} aria-label="Clear search">
                <span aria-hidden="true">&times;</span>
              </button>
            )}
          </div>

          {/* Horizontal scroll rather than a wrapping grid: eleven conference chips wrap
              to three rows on a 375px phone and push the games off the screen. */}
          <div className="adm__confs" role="group" aria-label="Filter by conference">
            <button
              className={`fchip${conf === null ? ' is-on' : ''}`}
              onClick={() => setConf(null)}
              aria-pressed={conf === null}
            >
              All
            </button>
            {conferences.map((c) => (
              <button
                key={c.id}
                className={`fchip${conf === c.id ? ' is-on' : ''}`}
                onClick={() => setConf(conf === c.id ? null : c.id)}
                aria-pressed={conf === c.id}
              >
                {c.name} <span className="fchip__n">{c.count}</span>
              </button>
            ))}
          </div>

          {filtered && shown.length > 0 && (
            <p className="adm__count">
              {shown.length} of {pool.length} games
              {' · '}
              <button className="adm__reset" onClick={clearFilters}>
                show all
              </button>
            </p>
          )}
        </div>
      )}

      {view === 'slate' && count === 0 && (
        <Empty icon={<IconClock />} title="Nothing selected">
          Switch to &ldquo;Every game&rdquo; and tick the games you want.
        </Empty>
      )}

      {view === 'pool' && shown.length === 0 && (
        <Empty icon={<IconClock />} title="No game matches">
          Nothing this week{' '}
          {query.trim() ? `matches “${query.trim()}”` : 'is in that conference'}.
          <br />
          <button className="adm__reset" onClick={clearFilters}>
            Clear the filters
          </button>
        </Empty>
      )}

      {sections.map((sec) => (
        <section key={sec.key} className="adm__day">
          <h3 className="adm__dayhead">
            {sec.label}
            <span className="adm__daycount num">{sec.games.length}</span>
          </h3>
          <ul className="alist">
            {sec.games.map((g) => {
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
                      {/* One status chip only. Three of them wrapped onto a second line
                          and made every row twice as tall. A game with no line has no
                          tier and shows none, which is fine: .arow__meta is a fixed 18px
                          whether or not it holds a chip. */}
                      <span className="arow__meta">
                        <span>{kickoffLabel(g.kickoff)}</span>
                        <span className="num">{api.spreadLabel(g)}</span>
                        {g.locked ? (
                          <span className="chip chip--bad">kicked off</span>
                        ) : g.featured ? (
                          <span className="chip chip--accent">ESPN top</span>
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
        </section>
      ))}

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

const SearchIcon = () => (
  <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" className="adm__searchicon">
    <circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" strokeWidth="2" />
    <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
)
