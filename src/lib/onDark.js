/**
 * Lift a seat colour until it can be seen on a dark ground, without changing whose it is.
 *
 * The Season tab is book mode now: the form chart sits in a felt well and the legend sits
 * on wood. The four seat colours were chosen against Slate's white card and none of them
 * survives the move. Measured against the felt (#0f3120, the midpoint of the well's
 * gradient):
 *
 *     Grant  #B85C1F  4.06        James  #1F6F4A  3.03
 *     Parker #2E5C8A  2.67        Nicole #8A2E4F  2.29
 *
 * WCAG 1.4.11 puts a non-text graphic at 3:1 and a 2px polyline is a graphic, so three of
 * the four fail and James, dark green on dark green felt, all but disappears. This is the
 * same trap as the scorebug's `--lead`, which measures 10.8:1 on near-black and 1.5:1 on
 * a light card: a colour picked against one ground does not travel to the other.
 *
 * Hand-picking four replacement hexes was the first version and it is wrong for one
 * reason: it is four magic numbers that no longer mean "Grant" if a seat colour is ever
 * edited, and nothing would catch it. This raises LIGHTNESS ONLY, in HSL, one step at a
 * time until the target ratio is met. Hue never moves, so orange stays orange and the
 * chart still reads as the same four people. Saturation is nudged up slightly because
 * lightening in HSL washes colour out and a pastel chart is its own kind of unreadable.
 */

/** #rrggbb to {r,g,b} in 0..1. */
function rgb(hex) {
  const h = hex.replace('#', '')
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  return {
    r: parseInt(full.slice(0, 2), 16) / 255,
    g: parseInt(full.slice(2, 4), 16) / 255,
    b: parseInt(full.slice(4, 6), 16) / 255,
  }
}

const hex2 = (v) => Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, '0')

/** Relative luminance, WCAG 2.x. */
export function luminance(hex) {
  const { r, g, b } = rgb(hex)
  const f = (x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4)
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}

/** Contrast ratio between two hex colours, 1 to 21. */
export function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

function toHsl(hex) {
  const { r, g, b } = rgb(hex)
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const l = (max + min) / 2
  const d = max - min
  if (!d) return { h: 0, s: 0, l }
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
  let h
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6
  else if (max === g) h = ((b - r) / d + 2) / 6
  else h = ((r - g) / d + 4) / 6
  return { h, s, l }
}

function toHex({ h, s, l }) {
  if (!s) return '#' + hex2(l).repeat(3)
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s
  const p = 2 * l - q
  const ch = (t) => {
    if (t < 0) t += 1
    if (t > 1) t -= 1
    if (t < 1 / 6) return p + (q - p) * 6 * t
    if (t < 1 / 2) return q
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6
    return p
  }
  return '#' + hex2(ch(h + 1 / 3)) + hex2(ch(h)) + hex2(ch(h - 1 / 3))
}

/** The felt well, at the midpoint of its gradient. The darkest ground book mode draws on. */
export const FELT = '#0f3120'

/**
 * @param hex     the seat's own colour
 * @param ground  what it has to be seen against
 * @param target  the ratio to clear. 3:1 is the WCAG floor for a graphic; 3.5 leaves room
 *                for the ground's own gradient, which runs darker than its midpoint at
 *                one end and lighter at the other.
 */
export function onDark(hex, ground = FELT, target = 3.5) {
  const c = toHsl(hex)
  /* Already fine, and a colour that does not need lifting must not be lifted: the point
     is to change as little as possible. */
  if (contrast(hex, ground) >= target) return hex
  for (let l = c.l; l <= 1; l += 0.01) {
    /* Saturation climbs a third as fast as lightness. Pure HSL lightening desaturates,
       and four pastels are as hard to tell apart as four dark colours. */
    const out = toHex({ h: c.h, s: Math.min(1, c.s + (l - c.l) / 3), l })
    if (contrast(out, ground) >= target) return out
  }
  return '#ffffff'
}
