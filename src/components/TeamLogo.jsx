import { useState } from 'react'

/**
 * Logos are vendored per ESPN team id under static/logos. If one is missing we fall
 * back to the abbreviation in a chip rather than showing a broken image, which happens
 * for the occasional FCS opponent that was not in the library when the week was built.
 */
export default function TeamLogo({ teamId, abbr, size = 40 }) {
  const [failed, setFailed] = useState(false)
  const px = { width: size, height: size }

  if (!teamId || failed) {
    return (
      <span
        className="logo logo--fallback"
        style={{ ...px, fontSize: Math.max(10, size * 0.3) }}
        aria-hidden="true"
      >
        {(abbr || '?').slice(0, 4)}
      </span>
    )
  }

  return (
    <img
      className="logo"
      style={px}
      src={`${import.meta.env.BASE_URL}logos/${teamId}.png`}
      alt=""
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  )
}
