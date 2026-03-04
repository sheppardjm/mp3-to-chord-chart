---
phase: 06-lyrics-input-chart-builder-and-api-contract
plan: "02"
subsystem: api
tags: [fastapi, pydantic, lyrics, chord-alignment, chart-builder, python]

# Dependency graph
requires:
  - phase: 06-01
    provides: ChordAnnotation, LyricLine, Section, ChartData Pydantic v2 models
  - phase: 04-structural-segmentation
    provides: build_sections() returning labeled sections with chord_sequence lists
  - phase: 02-audio-loading-and-key-detection
    provides: detect_key() returning "ROOT:mode" key string

provides:
  - chart_builder.py with _parse_lyrics(), _align_chords_to_lines(), build()
  - /analyze endpoint wired to accept lyrics Form param and return ChartData JSON
  - Proportional chord-to-lyric-line alignment algorithm
  - Key detection integrated into _run_pipeline() return dict

affects:
  - 06-03
  - 07-frontend-chord-chart-rendering
  - 08-svguitar-chord-diagrams

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Zip truncation for mismatched section counts (more lyrics vs more pipeline sections)"
    - "Equal time-slice partitioning: line i owns [start + i/n * dur, start + (i+1)/n * dur)"
    - "Chord position as 0.0-1.0 fraction within line duration, rounded to 3 decimals"
    - "unique_chords built with seen set preserving first-appearance order, filtering N/None/empty"
    - "Section end time = next_section.start; last section = last_chord.time + 8.0 seconds"
    - "build_chart() runs in-process (not threadpool) as fast pure Python"

key-files:
  created:
    - backend/audio/chart_builder.py
  modified:
    - backend/main.py

key-decisions:
  - "zip() truncation (not zip_longest) chosen for mismatched section counts — shorter list wins, no crash, no padding"
  - "Section end for last section = last_chord['time'] + 8.0 s (not audio duration) — pipeline doesn't expose total duration"
  - "build_chart() runs in-process after run_in_threadpool returns — no second threadpool needed for pure Python"
  - "Lyrics validated after pipeline completes (not before) — validate as late as possible to avoid 422 on slow path"

patterns-established:
  - "Form params alongside File in FastAPI multipart: File(...) + Form(None) in same signature"
  - "ValidationError/KeyError/ValueError all caught and re-raised as HTTPException(422)"

# Metrics
duration: 2min
completed: 2026-03-04
---

# Phase 6 Plan 02: Chart Builder and /analyze Endpoint Wiring Summary

**chart_builder.py with proportional chord-to-lyric alignment via equal time slices, wired into /analyze endpoint returning ChartData JSON with detect_key() integration**

## Performance

- **Duration:** 2 min 20 s
- **Started:** 2026-03-04T14:40:36Z
- **Completed:** 2026-03-04T14:42:56Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created `backend/audio/chart_builder.py` with `_parse_lyrics()`, `_align_chords_to_lines()`, and `build()` — the core algorithm that maps audio pipeline output to lyric-aware ChartData
- Wired `detect_key()` into `_run_pipeline()` so the returned dict carries a `'key'` field consumed by `build()`
- Updated `/analyze` endpoint to accept `lyrics: str = Form(None)`, return `response_model=ChartData`, and handle 422 for missing lyrics or malformed pipeline output

## Task Commits

Each task was committed atomically:

1. **Task 1: Create chart_builder.py with lyrics parsing, alignment, and build function** - `2c9782c` (feat)
2. **Task 2: Wire key detection, lyrics param, and chart builder into main.py** - `50df7a0` (feat)

## Files Created/Modified

- `backend/audio/chart_builder.py` - _parse_lyrics (blank-line section split), _align_chords_to_lines (equal time-slice proportional placement), build (ChartData assembly from pipeline result + lyrics)
- `backend/main.py` - Added detect_key call in _run_pipeline(), lyrics Form param and response_model=ChartData on /analyze, 422 handling for missing lyrics and malformed output

## Decisions Made

- **zip() truncation (not zip_longest):** Mismatched section counts (more lyrics sections than pipeline sections or vice versa) are silently truncated at the shorter list — no crash, no padding with empty data. Plan specified this explicitly.
- **Section end time for last section:** Uses `last_chord['time'] + 8.0 s` because the pipeline return dict does not expose total audio duration. The 8-second trailing buffer is a reasonable estimate for last-section coverage.
- **build_chart() in-process:** Fast pure Python, no threadpool needed. Runs synchronously after `run_in_threadpool(_run_pipeline)` returns.
- **Lyrics validated after pipeline:** The `if not lyrics` check occurs after the pipeline completes. This is intentional — the pipeline runs regardless, and lyrics absence is caught before chart building begins.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. One minor edit-tool mismatch on the first attempt to update the module docstring (a trailing whitespace difference in the original); corrected by re-reading the file and applying the correct string. No functional impact.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `/analyze` now accepts MP3 + lyrics and returns validated `ChartData` JSON; backend API contract is complete
- Frontend (Phase 7) can begin rendering chord charts against this response shape
- Chord diagram rendering (Phase 8) requires `unique_chords` list which is now correctly produced
- Known limitation from Phase 3 still applies: :7 quality confusion for chord templates; root detection is accurate but quality may be wrong for complex chords

---
*Phase: 06-lyrics-input-chart-builder-and-api-contract*
*Completed: 2026-03-04*
