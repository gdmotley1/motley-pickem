import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import * as api from './lib/api.js'
import { newBuildAvailable } from './lib/version.js'
import SignIn from './screens/SignIn.jsx'
import Picks from './screens/Picks.jsx'
import Board from './screens/Board.jsx'
import Standings from './screens/Standings.jsx'
import Admin from './screens/Admin.jsx'
import {
  Avatar,
  IconAdmin,
  IconBoard,
  IconPicks,
  IconTrophy,
  Sheet,
} from './components/ui.jsx'

const WEEK_ID = 1

const BASE_TABS = [
  { id: 'picks', label: 'Picks', Icon: IconPicks },
  { id: 'board', label: 'Board', Icon: IconBoard },
  { id: 'standings', label: 'Standings', Icon: IconTrophy },
]

export default function App() {
  const [me, setMe] = useState(undefined) // undefined = still checking
  // The Board is where the week actually is: scores, everyone's picks, and the running
  // point totals. Picks is a once-a-week errand, so it is somewhere you go, not where
  // you land.
  const [tab, setTab] = useState('board')
  const [menu, setMenu] = useState(false)
  const [week, setWeek] = useState(null)
  const [stale, setStale] = useState(false)

  useEffect(() => {
    api.whoami().then((p) => setMe(p ?? null))
  }, [])

  // Week label comes from ESPN's calendar via the backend, never hard-coded: Week 1 of
  // 2026 spans seventeen days and the app was previously mislabelling it as Week 2.
  useEffect(() => {
    if (!me) return
    api
      .getWeek(WEEK_ID)
      .then((rows) => setWeek(Array.isArray(rows) ? rows[0] : rows))
      .catch(() => setWeek(null))
  }, [me])

  // Check on load and whenever the app comes back to the foreground, which is exactly
  // when someone reopens it from their home screen.
  //
  // Three triggers, because one is not enough: an installed PWA resumed from the iOS
  // back-forward cache fires pageshow and not always visibilitychange, and a browser tab
  // switched back to fires focus. visibilitychange alone missed the case entirely.
  useEffect(() => {
    let done = false
    const check = () => {
      if (done) return
      newBuildAvailable().then((yes) => {
        if (yes) {
          done = true // stop polling once the banner is up
          setStale(true)
        }
      })
    }
    check()
    const onShow = () => {
      if (!document.hidden) check()
    }
    document.addEventListener('visibilitychange', onShow)
    window.addEventListener('focus', onShow)
    window.addEventListener('pageshow', onShow)
    return () => {
      document.removeEventListener('visibilitychange', onShow)
      window.removeEventListener('focus', onShow)
      window.removeEventListener('pageshow', onShow)
    }
  }, [])

  const signOut = useCallback(async () => {
    await api.signOut()
    setMenu(false)
    setMe(null)
    setTab('board')
  }, [])

  if (me === undefined) return <Splash />
  if (me === null) return <SignIn onSignedIn={setMe} />

  const tabs = me.is_admin
    ? [...BASE_TABS, { id: 'admin', label: 'Setup', Icon: IconAdmin }]
    : BASE_TABS

  return (
    <div className="app">
      <header className="apphdr">
        <div>
          <span className="apphdr__title">Motley Pick&apos;em</span>
          <span className="apphdr__week">
            {week ? `${week.label} · ${week.slate_size} games` : ' '}
          </span>
        </div>
        <button className="apphdr__me" onClick={() => setMenu(true)}>
          <Avatar name={me.name} color={me.color} size={24} />
          <span className="apphdr__name">{me.name}</span>
        </button>
      </header>

      {/*
        No AnimatePresence here on purpose. Wrapping the keyed screen in one with
        mode="wait" left the outgoing screen mounted forever under React 19: the tab
        button flipped to active, the old screen froze at its exit transform, and the new
        screen never mounted. A tab switch does not need an exit animation, so the new
        screen simply animates in on a fresh key.
      */}
      <main className="app__body">
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
          className="app__page"
        >
          {tab === 'picks' && (
            <Picks me={me} weekId={WEEK_ID} week={week} onNavigate={setTab} />
          )}
          {tab === 'board' && <Board me={me} weekId={WEEK_ID} week={week} />}
          {tab === 'standings' && <Standings me={me} weekId={WEEK_ID} />}
          {tab === 'admin' && <Admin me={me} weekId={WEEK_ID} />}
        </motion.div>
      </main>

      <nav
        className="tabbar"
        aria-label="Main"
        style={{ gridTemplateColumns: `repeat(${tabs.length}, 1fr)` }}
      >
        {tabs.map(({ id, label, Icon }) => (
          <button
            key={id}
            className={`tabbar__btn${tab === id ? ' is-on' : ''}`}
            aria-current={tab === id ? 'page' : undefined}
            onClick={() => setTab(id)}
          >
            <Icon />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      {stale && (
        <button className="update" onClick={() => window.location.reload()}>
          A newer version is ready. Tap to update.
        </button>
      )}

      <AccountSheet
        open={menu}
        me={me}
        onClose={() => setMenu(false)}
        onSignOut={signOut}
      />
    </div>
  )
}

/** Tapping your name used to sign you out instantly, which is far too easy to do by
    accident. It now opens this, so signing out is deliberate. */
function AccountSheet({ open, me, onClose, onSignOut }) {
  return (
    <Sheet open={open} onClose={onClose} label="Account">
      <div style={{ display: 'grid', placeItems: 'center', gap: 10, marginBottom: 6 }}>
        <Avatar name={me.name} color={me.color} size={56} />
        <h2 className="sheet__title">{me.name}</h2>
      </div>
      <p className="sheet__sub">
        {me.is_admin ? 'Commissioner · can publish the slate' : 'Player'}
      </p>
      <button className="btn" onClick={onClose}>
        Keep picking
      </button>
      <button className="btn btn--ghost" onClick={onSignOut}>
        Sign out and switch player
      </button>
    </Sheet>
  )
}

function Splash() {
  return (
    <div className="splash">
      <div className="splash__ball" />
    </div>
  )
}
