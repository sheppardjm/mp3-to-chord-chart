---
phase: 04-structural-segmentation
plan: "02"
subsystem: api
tags: [fastapi, uvicorn, python-multipart, segmentation, chord-detection, audio-pipeline, rest-api]

# Dependency graph
requires:
  - phase: 03-beat-tracking-and-chord-detection
    provides: detect_chords_pipeline(), beat_track_grid(), extract_beat_chroma() returning tempo_bpm, chord_segments, chord_sequence, beat_times, n_beats, n_segments
  - phase: 04-01
    provides: segment_song(), build_sections() producing labeled sections array with collapsed chord sequences
provides:
  - POST /analyze endpoint accepting MP3 file upload via multipart form
  - Unified JSON response with tempo_bpm, chord_segments, sections, n_beats, n_segments
  - Full end-to-end audio pipeline: load -> detect_chords -> segment -> respond
  - Temp file lifecycle management with finally-block cleanup
affects:
  - 05-api-layer (primary API contract established here)
  - 06-lyrics-alignment (sections array schema this endpoint returns)
  - 07-chord-chart (chord_segments and sections data this endpoint provides)
  - 08-ui (end-to-end flow validated by this endpoint)

# Tech tracking
tech-stack:
  added:
    - python-multipart (auto-installed: FastAPI UploadFile requires it for multipart form parsing)
  patterns:
    - "FastAPI UploadFile + tempfile.NamedTemporaryFile pattern for MP3 file upload handling"
    - "Re-compute chroma_sync from beat_track_grid + extract_beat_chroma rather than modifying Phase 3 contract"
    - "os.unlink in finally block for temp file cleanup even on exception"
    - "HTTPException(status_code=500) wrapping all pipeline errors for consistent error response"

key-files:
  created: []
  modified:
    - backend/main.py

key-decisions:
  - "Re-compute chroma_sync rather than exposing it from detect_chords_pipeline() -- preserves Phase 3 contract; re-computation is cheap (~0.5s per 4-min song)"
  - "python-multipart auto-installed as blocking dependency (Rule 3) -- FastAPI UploadFile silently fails without it"
  - "File size and MIME validation deferred to Phase 5 -- out of scope for pipeline integration"

patterns-established:
  - "Temp file pattern: NamedTemporaryFile(delete=False) + finally os.unlink -- safe cleanup even on pipeline exception"
  - "Unified API response schema: {tempo_bpm, chord_segments, sections, n_beats, n_segments} -- contract for downstream phases"

# Metrics
duration: ~10min (includes human verification checkpoint wait)
completed: 2026-03-04
---

# Phase 4 Plan 02: /analyze Endpoint Integration Summary

**POST /analyze endpoint wiring load_audio + detect_chords_pipeline + segment_song + build_sections into a single multipart MP3 upload returning 8 labeled sections, 4 chords (G:maj/A:min/C:maj/D:maj), and 107.7 BPM for "Don't Cave.mp3"**

## Performance

- **Duration:** ~10 min (includes human verification checkpoint)
- **Started:** 2026-03-04T06:00:00Z
- **Completed:** 2026-03-04T06:10:00Z
- **Tasks:** 2 (1 auto + 1 checkpoint:human-verify)
- **Files modified:** 1

## Accomplishments
- /analyze POST endpoint added to backend/main.py, accepting MP3 file uploads via multipart form (FastAPI UploadFile)
- Full audio pipeline integrated: load_audio -> detect_chords_pipeline -> beat_track_grid + extract_beat_chroma -> segment_song -> build_sections
- Unified JSON response validated against all 4 Phase 4 success criteria on "Don't Cave.mp3" (~4 min song)
- curl test confirmed 8 sections, correct G major chords, plausible beat-aligned section boundaries

## Task Commits

Each task was committed atomically:

1. **Task 1: Add /analyze POST endpoint integrating chord detection and segmentation** - `15902aa` (feat)
2. **Task 2: Validate /analyze endpoint with curl against Don't Cave.mp3** - CHECKPOINT APPROVED (human verification, no code commit)

**Plan metadata:** (added in final docs commit)

## Files Created/Modified
- `backend/main.py` - Added /analyze POST endpoint; preserved /health GET; imports from audio.loader, audio.chord_detection, audio.segmentation

## Decisions Made
- Re-compute chroma_sync inside /analyze via beat_track_grid() + extract_beat_chroma() rather than modifying detect_chords_pipeline() to expose intermediate state -- preserves the Phase 3 module contract; the ~0.5s re-computation cost is acceptable for a 4-minute song
- File size validation and MIME-type checking deferred to Phase 5 (out of scope per plan)
- Async/background processing deferred to Phase 5 (out of scope per plan)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Auto-installed python-multipart dependency**
- **Found during:** Task 1 (server startup verification)
- **Issue:** FastAPI UploadFile requires python-multipart for multipart form parsing; package was not installed in .venv; server started but /analyze would fail silently on file uploads
- **Fix:** Ran `pip install python-multipart` in backend/.venv before verifying the endpoint
- **Files modified:** backend/.venv (package installed; no requirements.txt change needed -- consistent with existing project pattern)
- **Verification:** curl POST with "Don't Cave.mp3" returned valid JSON with 8 sections
- **Committed in:** `15902aa` (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking dependency)
**Impact on plan:** python-multipart is a required runtime dependency for FastAPI file uploads -- without it the endpoint silently rejects multipart data. Auto-fix was necessary for the endpoint to function. No scope creep.

## Issues Encountered
None beyond the python-multipart blocking dependency handled via Rule 3.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- /analyze endpoint is the primary API contract for Phases 5-8; schema is stable: `{tempo_bpm, chord_segments, sections, n_beats, n_segments}`
- Phase 4 complete: segmentation module (04-01) and API integration (04-02) both done
- Phase 5 (API layer) can add: file size/MIME validation, async processing via run_in_executor, error handling improvements
- Section label editing should be supported in UI from Phase 8 (no reliable Verse/Chorus auto-detection; users will want to rename Section A/B/C)

---
*Phase: 04-structural-segmentation*
*Completed: 2026-03-04*
