import { useEffect, useState } from 'react'

/**
 * TEMPORARY. Delete this file, its import in App.jsx and the .diag block in app.css
 * once the tab bar gap is fixed.
 *
 * The bar is painted about 50px too high on a cold standalone launch and snaps into
 * place the moment any tab is switched. That is not reproducible on any machine this
 * project is developed on: it needs a real iPhone, a real home-screen launch, and a
 * first paint that lands before the viewport has settled. Three fixes have been shipped
 * on inference from desktop measurements and all three were wrong.
 *
 * So this reads the numbers off the device instead. It shows two rows: what the layout
 * looked like at first paint, and what it looks like now. Switch tabs once and the
 * second row becomes the corrected state, which makes the difference between them the
 * entire diagnosis.
 *
 * Seat 1 only, so nobody else in the family ever sees it.
 */

/** Module scope on purpose: a tab switch remounts the component, and losing the
 *  first-paint snapshot at exactly that moment would throw away the only interesting
 *  half of the comparison. */
let atLoad = null

function snap() {
  const bar = document.querySelector('.tabbar')
  const r = bar ? bar.getBoundingClientRect() : null
  const vv = window.visualViewport
  const de = document.documentElement
  return {
    ih: window.innerHeight,
    vvH: vv ? Math.round(vv.height) : null,
    vvTop: vv ? Math.round(vv.offsetTop) : null,
    vvScale: vv ? Number(vv.scale.toFixed(2)) : null,
    clientH: de.clientHeight,
    scrollH: de.scrollHeight,
    scrollY: Math.round(window.scrollY),
    barTop: r ? Math.round(r.top) : null,
    barBottom: r ? Math.round(r.bottom) : null,
    barH: r ? Math.round(r.height) : null,
    // The bar's own resolved padding-bottom, which is 6px plus the safe-area inset.
    // Reading the custom property instead can hand back the unresolved env() text.
    padB: bar ? getComputedStyle(bar).paddingBottom : '?',
    mode: window.matchMedia('(display-mode: standalone)').matches ? 'standalone' : 'browser',
    screenH: window.screen ? window.screen.height : null,
    dpr: window.devicePixelRatio,
  }
}

/**
 * The first reading, taken from Diag's own mount effect so the tab bar is guaranteed to
 * be in the DOM.
 *
 * Synchronous rather than inside requestAnimationFrame. rAF looked like the more correct
 * place to read a painted layout, and it silently never fired in the environment this
 * was built in, which would have shipped a diagnostic whose most important row was
 * permanently blank. A post-commit read is close enough and cannot be skipped.
 */
export function captureAtLoad() {
  if (!atLoad) atLoad = snap()
}

/** A second reading a beat later, to catch the viewport settling without a tab switch. */
let atSettle = null

const line = (s) =>
  s
    ? [
        `bar ${s.barTop}-${s.barBottom} h${s.barH} pad${s.padB}`,
        `ih${s.ih} vv${s.vvH}@${s.vvTop}x${s.vvScale}`,
        `cli${s.clientH} scr${s.scrollH} y${s.scrollY}`,
        `${s.mode} scr${s.screenH}@${s.dpr}x`,
      ].join('  ')
    : '-'

export default function Diag() {
  const [, bump] = useState(0)

  useEffect(() => {
    captureAtLoad()
    const rerender = () => bump((n) => n + 1)
    const settle = setTimeout(() => {
      if (!atSettle) atSettle = snap()
      rerender()
    }, 1200)
    const tick = setInterval(rerender, 500)
    window.addEventListener('resize', rerender)
    window.visualViewport?.addEventListener('resize', rerender)
    return () => {
      clearTimeout(settle)
      clearInterval(tick)
      window.removeEventListener('resize', rerender)
      window.visualViewport?.removeEventListener('resize', rerender)
    }
  }, [])

  const now = snap()
  const drift = (a, b) =>
    a && b && a.barBottom != null && b.barBottom != null
      ? `${b.barBottom - a.barBottom > 0 ? '+' : ''}${b.barBottom - a.barBottom}`
      : '?'

  return (
    <div className="diag">
      <p className="diag__h">
        bar drift load&rarr;1.2s {drift(atLoad, atSettle)}px &middot; load&rarr;now{' '}
        {drift(atLoad, now)}px
      </p>
      <p>
        <b>load </b> {line(atLoad)}
      </p>
      <p>
        <b>1.2s </b> {line(atSettle)}
      </p>
      <p>
        <b>now  </b> {line(now)}
      </p>
    </div>
  )
}
