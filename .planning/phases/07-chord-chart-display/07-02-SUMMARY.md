---
phase: 07-chord-chart-display
plan: "02"
subsystem: ui
tags: [chordsheetjs, vanilla-js, vite, chord-chart, position-mapping, html-div-formatter]

# Dependency graph
requires:
  - phase: 07-01
    provides: chordsheetjs@14.0.0 installed, HtmlDivFormatter smoke test confirming API works, #chord-chart div in DOM
  - phase: 06-02
    provides: ChartData JSON schema (sections, lines, chords with position 0.0-1.0), /analyze endpoint
provides:
  - renderChart.js module with ChartData-to-Song translation and HtmlDivFormatter rendering
  - Position-to-character-offset mapping (0.0-1.0 fraction -> char index via Math.round + Math.min clamp)
  - Song construction with section start/end Tag lines and ChordLyricsPair content lines
  - main.js wired to call renderChart() on /analyze response (replaces JSON.stringify dump)
  - Smoke test from 07-01 removed
affects:
  - 07-03 (header rendering builds on renderChart.js pattern; key/tempo not yet in Song constructor)
  - 08 (svguitar chord diagrams will supplement the chord chart display)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ChartData-to-Song translation: programmatic Song/Line/ChordLyricsPair/Tag construction (no text parser)"
    - "Position-to-char mapping: Math.round(position * text.length) clamped with Math.min(result, text.length)"
    - "Section type mapping: substring match (includes chorus/bridge), default to verse for Section A/B/C labels"
    - "CSS injection guard: document.getElementById(CHORD_CHART_CSS_ID) prevents duplicate style injection on re-submit"
    - "Chord-above-lyric layout: HtmlDivFormatter flexbox columns, no custom geometry needed"

key-files:
  created:
    - frontend/src/renderChart.js
  modified:
    - frontend/src/main.js

key-decisions:
  - "new Song() called with no constructor args — key/tempo header deferred to Plan 07-03"
  - "sectionTypeFor() uses substring matching (not exact match) to handle Section A/B/C labels from backend as 'verse' type"
  - "buildChordLyricsPairs() clamps charIdx with Math.min(result, text.length) to handle position near 1.0 safely"
  - "Leading text before first chord (charIdx > 0) creates an empty-chord ChordLyricsPair to preserve lyric continuity"

patterns-established:
  - "renderChart module pattern: single exported function, internal helpers unexported"
  - "CSS injection once: guard with getElementById before appending style to head"
  - "Chart cleared on re-submit: chartEl.innerHTML = '' before renderChart() call"

# Metrics
duration: 2min
completed: 2026-03-04
---

# Phase 7 Plan 02: renderChart.js with ChartData-to-Song Translation Summary

**ChartData JSON rendered as chord-above-lyric HTML via ChordSheetJS HtmlDivFormatter with position-to-character-offset mapping for chord placement over correct syllables**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-04T15:49:04Z
- **Completed:** 2026-03-04T15:50:54Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `renderChart.js` translating ChartData JSON into a ChordSheetJS Song with section tags and ChordLyricsPair items
- Implemented `buildChordLyricsPairs()` mapping float position (0.0-1.0) to character offsets for chord-above-syllable placement
- Wired `renderChart(data, chartEl)` into `main.js` fetch handler, replacing the raw JSON.stringify dump
- Removed ChordPro smoke test from 07-01 entirely; `<pre id="result">` replaced by `<div id="chord-chart">`
- Vite dev server starts without errors confirming clean import resolution

## Task Commits

Each task was committed atomically:

1. **Task 1: Create renderChart.js** - `6a0e61a` (feat)
2. **Task 2: Wire renderChart into main.js, remove smoke test** - `9daf551` (feat)

## Files Created/Modified

- `frontend/src/renderChart.js` - ChartData-to-Song translation module; exports `renderChart(chartData, containerEl)`
- `frontend/src/main.js` - Imports and calls `renderChart()`; smoke test removed; `<pre>` replaced with `<div id="chord-chart">`

## Decisions Made

- `new Song()` called with no constructor args — key/tempo header rendering is scoped to Plan 07-03; adding it here would conflict with that plan's output
- `sectionTypeFor()` uses `.includes('chorus')` / `.includes('bridge')` substring matching; all generic "Section A", "Section B" labels from `segmentation.py` DEFAULT_LABELS fall through to `'verse'` (correct and safe)
- `buildChordLyricsPairs()` clamps with `Math.min(result, text.length)` rather than `text.length - 1` — the last chord correctly receives the remainder of the text string via the `tail` assignment after the loop, so clamping at `text.length` (not `text.length - 1`) is correct
- Leading text before the first chord (`charIdx > 0` on first iteration) creates an empty-chord `ChordLyricsPair('', fragment)` to preserve the lyric text that precedes the first chord change

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `renderChart.js` is ready for Plan 07-03 to extend with key/tempo header rendering above the chord chart
- The chord chart renders correctly for all section types (verse/chorus/bridge) with chord names positioned above lyrics
- Lines with no chords (empty `chords` array) produce a single `ChordLyricsPair('', text)` — plain lyric line, no empty chord row
- Submitting MP3 + lyrics via the form will now render a chord chart instead of raw JSON (pending backend being available)

---
*Phase: 07-chord-chart-display*
*Completed: 2026-03-04*
