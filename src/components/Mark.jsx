import { useState } from 'react'

/**
 * A school's mark on a dark ground, with no disc behind it.
 *
 * Tries the drawing made for a dark background first, which every FBS school has, then the
 * plain one, then the abbreviation, so an FCS opponent missing from the library still gets
 * something readable rather than a broken image. Shared by the Week tab's recap and the
 * Board's jumbotron.
 */
export default function Mark({ id, abbr, size = 34, className = '' }) {
  const [step, setStep] = useState(0)
  const base = `${import.meta.env.BASE_URL}logos/`
  if (!id || step > 1) {
    return (
      <span className={`wf-mark wf-mark--text ${className}`} style={{ width: size, height: size }} aria-hidden="true">
        {(abbr || '?').slice(0, 4)}
      </span>
    )
  }
  return (
    <img
      className={`wf-mark ${className}`}
      src={`${base}${id}${step === 0 ? '-dark' : ''}.png`}
      width={size}
      height={size}
      alt=""
      loading="lazy"
      decoding="async"
      onError={() => setStep((s) => s + 1)}
    />
  )
}
