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
- JetBrains Mono (weights 200..700), ligatures off, `tabular-nums slashed-zero` on every live number
- sizes: 30 px light hero numerals, 14 px critical, 12.5 px data, 11 px ticks, 10 px uppercase micro-labels (`0.12em` tracking); every value has a unit
- numbered instrument headers (`01`..`11`), discrete 24-segment load/thermal meters, and 3-column/4-column footer metric strips separated by 1 px hairlines
- central interactive 3D CAD/Point-Cloud Hologram (`OdriveHologram`) of the ODESC 3.6 56V PCB, 6x 56V bus capacitors, M0/M1 MOSFET stages, STM32F405 MCU, coupled 90KV BLDC actuator (20:1), and AS5047P SPI encoder with 6 spatial HUD callouts and 3D leader lines
- concentric dotted polar radar dial (`EncoderCard`) showing mechanical shaft angle (`0..360 deg`) and electrical phase vector
- missing data shows `NO DATA` / `--`, never placeholder values
- bento grid: 12 columns, `ResizeObserver`-driven width, ordered by operational use case (`bench`, `tuning`, `thermal`), locked in operate mode, editable in `edit grid` mode
- status bar and DISARM ALL are pinned and cannot be moved
- keyboard: `Esc` disarm, `:` or Ctrl+K palette, Alt+1..9/0/F/A views (bare keys never switch
  views, so stray typing cannot change the screen mid-test)
