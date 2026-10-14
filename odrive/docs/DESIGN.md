# Design system

Terminal look, ISA-101 behaviour: the green ramp is the "grayscale"; color only means something
is abnormal. Tokens live in `frontend/src/styles/tokens.css`.

## Color

| token | hex | contrast on bg | use |
|---|---|---|---|
| bg | #0a0f0c | - | page (never pure black: halation) |
| surface / surface-2 | #0f1712 / #152019 | - | panels / hover |
| border | #24352b | - | 1 px hairlines |
| text | #c6f2d0 | 15.7:1 | values |
| text-2 | #8fc79e | 10.0:1 | labels |
| muted | #5e8a6b | 4.9:1 | units, captions |
| accent | #3df57a | 13.4:1 | focus, selection, series 1 only |
| warn | #ffb000 | 10.6:1 | warning fills (ink #1a1000) |
| error | #ff5a4f / fill #8f1d17 | 6.3:1 | alarm fills (ink #ffe9e7) |
| info | #59c8ff | 10.2:1 | "gui active" |

Chart series `#3df57a #7695b6 #b6aaff #b264fb #5cc3b0 #fddbfe`: color-blind checked, never alarm
hues, each with its own dash pattern.

## Rules

- normal states are plain text (`CLOSED_LOOP`); only faults get a fill and a glyph (■ alarm, ▲ warn)
- only unacknowledged alarms blink; nothing else animates (reduced-motion respected)
- JetBrains Mono, ligatures off, `tabular-nums slashed-zero` on every live number
- sizes: 15 px critical, 13 px data, 11 px ticks; every value has a unit
- radius <= 2 px, no shadows, no gradients, no glass/glow/scanlines, no emoji, no icon per label
- missing data shows `NO DATA` / `--`, never placeholder values
- bento grid: 12 columns, panel size follows decision importance, locked in operate mode,
  editable layouts saved per task (bench / tuning / thermal)
- status bar and DISARM ALL are pinned and cannot be moved
- keyboard: `Esc` disarm, `:` or Ctrl+K palette, Alt+1..9/0/F/A views (bare keys never switch
  views, so stray typing cannot change the screen mid-test)
