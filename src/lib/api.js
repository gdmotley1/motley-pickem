/**
 * The only place the app talks to the outside world.
 *
 * Every call is a Postgres RPC, never a table read. The tables deny the anon key
 * everything (RLS on, no policies), so the kickoff lock and the pick-visibility rule
 * cannot be bypassed from the browser. See migrations/001_init.sql.
 *
 * When Supabase env vars are absent the module falls back to an in-memory mock backed by
 * static/data/week01.json, so the UI can be built and demoed before the database exists.
 */
import { createClient } from '@supabase/supabase-js'
import * as mock from './mock.js'

const URL = import.meta.env.VITE_SUPABASE_URL
const ANON = import.meta.env.VITE_SUPABASE_ANON_KEY

export const MOCK = import.meta.env.VITE_MOCK === '1' || !URL || !ANON

const sb = MOCK ? null : createClient(URL, ANON, { auth: { persistSession: false } })

const TOKEN_KEY = 'pickem.token'
export const getToken = () => {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null // private mode, or storage blocked
  }
}
const setToken = (t) => {
  try {
    t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* nothing we can do; the session just will not persist */
  }
}

/** Postgres raises turn into readable messages instead of "unknown error". */
function unwrap({ data, error }) {
  if (error) {
    const msg = (error.message || 'Something went wrong')
      .replace(/^.*?violates row-level security.*$/i, 'Not allowed')
      .replace(/\s*\(SQLSTATE.*\)$/, '')
    throw new Error(msg)
  }
  return data
}

const rpc = (fn, args) => (MOCK ? mock.rpc(fn, args) : sb.rpc(fn, args).then(unwrap))

/* ------------------------------------------------------------------ identity */

export const listSeats = () => rpc('list_seats', {})

export async function claimSeat(seat, name, pin) {
  const token = await rpc('claim_seat', { p_seat: seat, p_name: name, p_pin: pin })
  setToken(token)
  return token
}

export async function signIn(seat, pin) {
  const token = await rpc('sign_in', { p_seat: seat, p_pin: pin })
  setToken(token)
  return token
}

/** Returns null rather than throwing when there is simply no valid session. */
export async function whoami() {
  const token = getToken()
  if (!token) return null
  try {
    const rows = await rpc('whoami', { p_token: token })
    const me = Array.isArray(rows) ? rows[0] : rows
    if (!me) {
      setToken(null)
      return null
    }
    return me
  } catch {
    setToken(null)
    return null
  }
}

export async function signOut() {
  const token = getToken()
  setToken(null)
  if (token) {
    try {
      await rpc('sign_out', { p_token: token })
    } catch {
      /* the local session is gone either way */
    }
  }
}

/* ------------------------------------------------------------------ the pool */

const withToken = (args) => ({ p_token: getToken(), ...args })

export const getSlate = (weekId) => rpc('get_slate', withToken({ p_week: weekId }))
export const getBoard = (weekId) => rpc('get_board', withToken({ p_week: weekId }))
export const getStandings = () => rpc('get_standings', withToken({}))

/**
 * picks: [{ game_id, pick, confidence }] for the whole slate.
 * The server rejects a partial set, a repeated confidence value, or any change to a
 * game that has kicked off, so the UI never has to be the last line of defence.
 */
export const savePicks = (weekId, picks) =>
  rpc('save_picks', withToken({ p_week: weekId, p_picks: picks }))

export const publishSlate = (weekId, gameIds) =>
  rpc('publish_slate', withToken({ p_week: weekId, p_game_ids: gameIds }))

/** Week metadata for the header. Week numbers follow ESPN's published CFB calendar. */
export const getWeek = (weekId) => rpc('get_week', withToken({ p_week: weekId }))

/** Admin only: the full 40-game pool for a week, with in_slate flags. */
export const getPool = (weekId) => rpc('get_pool', withToken({ p_week: weekId }))

/* ------------------------------------------------------------------ helpers */

/** Logos are vendored per ESPN team id, light and dark variants. */
export const logoUrl = (teamId) => `${import.meta.env.BASE_URL}logos/${teamId}.png`

/** "LSU -10" from the stored favourite and line. */
export function spreadLabel(game) {
  if (game.spread_line === null || game.spread_line === undefined) return 'no line'
  const n = Number(game.spread_line)
  if (!game.favorite_abbr || n === 0) return "PK"
  return `${game.favorite_abbr} -${n % 1 === 0 ? n : n.toFixed(1)}`
}

/**
 * "O/U 52.5", or null when there is nothing to show.
 *
 * Null is common and not an error: ESPN stops publishing odds once a game is final, so
 * anything that kicked off before the total was ever stored has no number and never
 * will. Callers drop the label rather than printing a placeholder.
 */
export function totalLabel(game) {
  if (game.over_under === null || game.over_under === undefined) return null
  const n = Number(game.over_under)
  if (!Number.isFinite(n)) return null
  return `O/U ${n % 1 === 0 ? n : n.toFixed(1)}`
}

export const isUnderdog = (game, abbr) =>
  !!game.underdog_abbr && game.underdog_abbr === abbr
