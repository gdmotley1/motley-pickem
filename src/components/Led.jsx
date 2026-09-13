/**
 * Numbers and words drawn in LED dots: the glyphs are cut by a mask, and the glow sits on
 * the wrapper so it lights the dots rather than the gaps.
 *
 * The jumbotron's lettering, shared so the Board and the Picks tab are one stadium rather
 * than two copies of it. The styles are `.jb-led` in app.css.
 */
export default function Led({ children, className = '' }) {
  return (
    <span className={`jb-led ${className}`}>
      <span className="num">{children}</span>
    </span>
  )
}
