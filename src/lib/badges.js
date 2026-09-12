/**
 * Grant's badge art, one file per record, as fingerprinted URLs.
 *
 * The files are built from inputs/badges by scripts/build_badges.py into src/assets/badges.
 * Importing them through Vite rather than serving them from static/ means a redrawn badge
 * gets a new file name, so no cache can keep showing the old one.
 *
 * Kept out of seasonRecords.js on purpose: that file runs under node in the gate, and
 * import.meta.glob only exists inside a Vite build.
 */
const files = import.meta.glob('../assets/badges/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
})

const BY_KEY = Object.fromEntries(
  Object.entries(files).map(([file, url]) => [file.split('/').pop().replace(/\.webp$/, ''), url]),
)

export const badgeUrl = (key) => BY_KEY[key]
