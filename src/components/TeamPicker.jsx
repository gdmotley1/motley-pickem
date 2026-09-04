import { useMemo, useRef, useState } from 'react'

import { markUrl, score, useTeams } from '../lib/teams.js'
import { Sheet, Spinner } from './ui.jsx'

/**
 * Pick the school you wear as your profile picture.
 *
 * 139 rows do not scroll well on a phone, which is the same problem the Setup screen
 * solved for the game pool, so this borrows the same answer: a search box at the top that
 * filters as you type. It is more generous than the Setup one because a family member may
 * know the mascot and not the school. Typing "bobcat" finds Georgia College; typing "uga"
 * finds Georgia. See `score` in lib/teams.js.
 *
 * Each row shows the mark on the exact background the avatar will use, so what you tap is
 * what you get. No preview step, no confirm: tapping a row saves and closes, and picking
 * again changes it. Nothing here is destructive enough to deserve a confirmation.
 */
export default function TeamPicker({ open, current, onClose, onPick }) {
  const teams = useTeams()
  const [query, setQuery] = useState('')
  const [saving, setSaving] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const rows = useMemo(() => {
    if (!teams) return []
    return teams
      .map((t) => [score(t, query), t])
      .filter(([s]) => s > 0)
      .sort((a, b) => b[0] - a[0] || a[1].school.localeCompare(b[1].school))
      .map(([, t]) => t)
  }, [teams, query])

  async function choose(team) {
    setSaving(team.id)
    setError(null)
    try {
      await onPick(team.id)
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(null)
    }
  }

  return (
    <Sheet open={open} onClose={onClose} label="Pick your team">
      <h2 className="sheet__title">Your team</h2>
      <p className="sheet__sub">
        Pick a school and its logo becomes your picture everywhere in the app.
      </p>

      <div className="adm__search tpick__search">
        <input
          ref={inputRef}
          type="search"
          className="adm__input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search a school or mascot"
          aria-label="Search for a school"
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

      {error && <p className="tpick__err">{error}</p>}

      {!teams ? (
        <Spinner />
      ) : (
        <div className="tpick__list">
          {rows.map((t) => (
            <button
              key={t.id}
              className={`tpick__row${t.id === current ? ' is-on' : ''}`}
              onClick={() => choose(t)}
              disabled={saving !== null}
            >
              <span className="tpick__disc" style={{ background: t.bg }}>
                <img src={markUrl(t)} alt="" width="26" height="26" loading="lazy" />
              </span>
              <span className="tpick__names">
                <span className="tpick__school">{t.school}</span>
                <span className="tpick__mascot">{t.mascot || t.conf}</span>
              </span>
              {t.id === current && <span className="tpick__on">Wearing</span>}
            </button>
          ))}
          {!rows.length && <p className="tpick__none">No school matches “{query}”.</p>}
        </div>
      )}

      {current && (
        <button
          className="btn btn--ghost"
          onClick={() => choose({ id: null })}
          disabled={saving !== null}
        >
          Go back to my initial
        </button>
      )}
    </Sheet>
  )
}
