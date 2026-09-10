# Hand-supplied logo artwork

Source files for schools whose mark cannot be pulled from a URL. Read by
`scripts/fetch_extra_teams.py` for any entry in `inputs/extra_teams.json` that has a
`source_file`, and never by the app: the shaped 500px result lands in `static/logos/`
and that is what ships.

Tracked rather than ignored, because `inputs/` is source data and losing the original
means the mark can only be rebuilt from whatever ended up in `static/logos/`.

## What to put here

| file | school | why it is not a URL |
|---|---|---|
| `gcsu-source.png` | Georgia College & State | The Wikipedia file carries a GCSU wordmark that overlaps the bobcat's jaw, so no `crop_bottom` keeps the whole animal and drops the lettering. Grant supplied the wordmark-free mark on 2026-09-10. |

## What the artwork needs

The shaper trims to the ink, squares on the bounding box and resizes to 500px, so
margins and canvas size do not matter. Two things do:

- **A keyline, or a background the mark does not itself use.** This is a hard
  requirement, not a preference. GCSU's field measures `(23,55,125)` and a quarter of
  the bobcat is `#123184`, which is **10.7 units of RGB away**: no tolerance separates
  them, so nothing about `key_background` can be tuned to cope. What saves the mark is
  that its white keyline seals the navy off from the frame, and the flood only clears
  background it can reach from an edge. Artwork whose own outline runs to the frame in
  the background colour gets eaten, and if it is eaten completely the script stops
  rather than writing an empty PNG. See `tests/test_logo_keying.py`.
- **No wordmark.** These render at 22px on the Board. Lettering turns to mush.

Then run:

```
python scripts/fetch_extra_teams.py
python -m pytest tests/test_logo_keying.py -q
```
