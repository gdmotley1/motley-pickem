/**
 * The color a finished week is painted in: the winner's school.
 *
 * teams.json keeps two colors per school, the disc's and the other one. The field takes
 * whichever is louder, measured as HSL saturation, because the quiet one is often a white
 * or a charcoal chosen to sit behind the mark: Arkansas's disc is white, so its field is
 * the cardinal; Georgia's other color is charcoal, so its field is the red. The ink is
 * picked by luminance so a gold field (Kennesaw State) gets dark type.
 *
 * A seat with no school falls back to the player's own color, as the avatar does.
 */
const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)

function saturation(hex) {
  const [r, g, b] = rgb(hex)
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  if (max === min) return 0
  const light = (max + min) / 2
  return (max - min) / (1 - Math.abs(2 * light - 1))
}

function luminance(hex) {
  const lin = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  const [r, g, b] = rgb(hex).map(lin)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

const valid = (c) => typeof c === 'string' && /^#[0-9a-f]{6}$/i.test(c)

export function schoolField(team, fallback = '#28313d') {
  const options = [team?.bg, team?.alt].filter(valid)
  const field = options.length ? options.reduce((a, b) => (saturation(b) > saturation(a) ? b : a)) : valid(fallback) ? fallback : '#28313d'
  return { field, ink: luminance(field) > 0.36 ? '#111111' : '#ffffff' }
}
