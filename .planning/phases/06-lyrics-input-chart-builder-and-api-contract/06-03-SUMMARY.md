---
phase: 06-lyrics-input-chart-builder-and-api-contract
plan: "03"
subsystem: ui
tags: [vite, javascript, formdata, multipart, lyrics, textarea, end-to-end]

# Dependency graph
requires:
  - phase: 06-02
    provides: /analyze endpoint that accepts lyrics form field and returns ChartData JSON
provides:
  - Lyrics textarea in the browser upload form
  - Lyrics value appended as 'lyrics' multipart field in FormData POST
  - Verified end-to-end: MP3 + lyrics -> ChartData JSON displayed in browser
affects: [07-chord-chart-display, 08-svguitar-chord-diagrams]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FormData multipart: no manual Content-Type header; browser sets boundary automatically"
    - "Lyric textarea placed between file input and submit button, id='lyrics' for querySelector"

key-files:
  created: []
  modified:
    - frontend/src/main.js

key-decisions: []

patterns-established:
  - "Textarea id='lyrics' used for querySelector; value accessed as document.querySelector('#lyrics').value"
  - "formData.append('lyrics', ...) placed immediately after formData.append('file', ...) to mirror backend param order"

# Metrics
duration: ~10min
completed: 2026-03-04
---

# Phase 6 Plan 03: Lyrics Input Frontend Summary

**Lyrics textarea added to the browser upload form; full MP3 + lyrics -> ChartData JSON end-to-end cycle verified by user with chord distribution across lines and 422 on empty lyrics.**

## Performance

- **Duration:** ~10 min (task 1 auto + checkpoint human-verify)
- **Started:** 2026-03-04T14:45:00Z (est)
- **Completed:** 2026-03-04T14:55:00Z (est)
- **Tasks:** 2 (1 auto + 1 checkpoint:human-verify)
- **Files modified:** 1

## Accomplishments

- Added multiline textarea (id="lyrics", rows=20) to the frontend upload form between the file picker and submit button
- Appended lyrics value to FormData as the 'lyrics' field, completing the multipart POST contract with the backend
- User verified full end-to-end cycle: MP3 upload + lyrics paste -> 10-30s processing -> ChartData JSON with key, bpm, unique_chords, sections, lines, and chord annotations
- User confirmed 422 error displayed (not crash) when textarea is left empty
- User confirmed chord annotations distributed across multiple lines, not collapsed to first line

## Task Commits

Each task was committed atomically:

1. **Task 1: Add lyrics textarea to upload form and append to FormData** - `a78a173` (feat)
2. **Task 2: Human verify full Phase 6 flow** - checkpoint approved (no code commit)

**Plan metadata:** (this commit)

## Files Created/Modified

- `frontend/src/main.js` - Added `<textarea id="lyrics">` to the HTML template and `formData.append('lyrics', document.querySelector('#lyrics').value)` in the submit handler

## Decisions Made

None - followed plan as specified. The two-line change (textarea in template + FormData append) was exactly as planned. No Content-Type header was set (browser sets multipart boundary automatically), as required by Phase 5 pattern.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 complete: Pydantic models, chart builder, key detection pipeline, lyrics textarea, and full end-to-end cycle all verified
- Phase 7 (chord chart display) can begin: ChartData JSON structure is confirmed and stable; backend contract is locked
- ChartData structure verified: `{ key, bpm, unique_chords, sections: [{ label, lines: [{ text, chords: [{ chord, beat_position }] }] }] }`
- Known concern from STATE.md: Laplacian segmentation k-parameter may need per-song tuning; Phase 7 UI should allow section label editing
- Known concern from STATE.md: svguitar chord coverage for edge-case chord names (Ebm, F#7) must be tested in Phase 8

---
*Phase: 06-lyrics-input-chart-builder-and-api-contract*
*Completed: 2026-03-04*
