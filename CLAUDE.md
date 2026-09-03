# cfb-pickem

TODO: one or two sentences on what this is and why it exists.

**Audience:** TODO: who uses this and what they do with it.

## The rule that outranks everything

TODO: the single thing that must never go wrong here. Delete this section only if
there genuinely is not one.

## Key commands

```bash
python -m pytest tests/ -q    # the gate. Run before saying anything is done.
TODO: the commands that actually matter
```

## Two things that will bite you

TODO: the non-obvious traps. Someone who does not know these will lose an hour.
If you cannot name any yet, delete this section and add it the first time one bites.

## Layout

```
cfb-pickem/
  CLAUDE.md      <- you are here, always loaded
  memory/        <- durable truth. decisions.md is @-imported.
  docs/          <- handoffs/ for workstreams, project-log.md for history
  app/           <- backend
  static/        <- frontend
  tests/         <- pytest, the gate
  scripts/       <- one builder per deliverable + the gate
```

Data flows one way: inputs to scripts to outputs. Deleting outputs must never break a
build. Source data is never edited in place.

## Detailed reference

@memory/decisions.md