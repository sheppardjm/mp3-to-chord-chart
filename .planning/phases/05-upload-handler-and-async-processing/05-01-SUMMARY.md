---
phase: 05-upload-handler-and-async-processing
plan: "01"
subsystem: api
tags: [fastapi, starlette, threadpool, validation, async, uvicorn, mp3, file-upload]

# Dependency graph
requires:
  - phase: 04-structural-segmentation
    provides: /analyze POST endpoint with load_audio + detect_chords_pipeline + segment_song + build_sections pipeline
provides:
  - File size validation guard (HTTP 413) before any file I/O
  - MIME type validation guard (HTTP 415) before any file I/O
  - Synchronous pipeline extracted into _run_pipeline(tmp_path) module-level function
  - run_in_threadpool offloading so event loop is never blocked during 10-60s analysis
affects:
  - Phase 6+ (any phase that calls /analyze or extends the pipeline)
  - Phase 8 (frontend) — /analyze now returns validation errors with clear HTTP codes

# Tech tracking
tech-stack:
  added: [starlette.concurrency.run_in_threadpool]
  patterns:
    - Validation-first guard pattern — size check before MIME check before I/O
    - Threadpool offloading via run_in_threadpool for blocking synchronous pipelines
    - HTTPException re-raise before generic Exception catch to prevent 500-wrapping of 4xx errors
    - tmp_path = None before try block with "if tmp_path:" in finally (vs locals() check)

key-files:
  created: []
  modified:
    - backend/main.py

key-decisions:
  - "05-01 D001: ALLOWED_MIME_TYPES includes both audio/mpeg and audio/mp3 — browsers send audio/mpeg, curl must pass type=audio/mpeg explicitly"
  - "05-01 D002: file.size guard uses 'is not None' check — UploadFile.size may be None when Content-Length header is missing; guard is advisory, not a bypass"

patterns-established:
  - "Validation order: size (cheapest) -> MIME type -> file I/O -> pipeline"
  - "Synchronous pipeline functions prefixed with _run_pipeline extracted as module-level for threadpool compatibility"

# Metrics
duration: 2min
completed: 2026-03-04
---

# Phase 5 Plan 01: Upload Handler and Async Processing Summary

**HTTP 413/415 validation guards and starlette run_in_threadpool offloading added to /analyze — event loop stays responsive during 10-60s audio pipeline processing**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-04T06:49:58Z
- **Completed:** 2026-03-04T06:52:10Z
- **Tasks:** 2 (1 implementation, 1 verification)
- **Files modified:** 1 (backend/main.py)

## Accomplishments

- File size validation (HTTP 413) rejects uploads >50 MB before any I/O
- MIME type validation (HTTP 415) rejects non-MP3 files with clear error message before any I/O
- Synchronous audio pipeline extracted into module-level `_run_pipeline(tmp_path: str) -> dict` function
- `await run_in_threadpool(_run_pipeline, tmp_path)` offloads blocking pipeline; /health responds in 0.008s during active /analyze
- Existing pipeline baseline preserved: Don't Cave.mp3 returns 107.7 BPM, 8 sections, 436 beats

## Task Commits

Each task was committed atomically:

1. **Task 1: Add file validation guards and extract pipeline to threadpool** - `8eb561b` (feat)
2. **Task 2: Verify validation and threadpool behavior with curl** - verification only, no code changes

**Plan metadata:** committed with docs commit below

## Files Created/Modified

- `backend/main.py` - Added MAX_FILE_SIZE, ALLOWED_MIME_TYPES constants; HTTP 413/415 guards; _run_pipeline() extraction; run_in_threadpool offloading; re-raised HTTPException before generic catch; tmp_path = None pattern

## Decisions Made

- **D001: ALLOWED_MIME_TYPES = {"audio/mpeg", "audio/mp3"}** — browsers send `audio/mpeg` for MP3 files; curl requires explicit `type=audio/mpeg` flag; `application/octet-stream` (curl default) is not accepted
- **D002: file.size guard uses `is not None` check** — UploadFile.size is None when no Content-Length header; guard runs when size is known, skips gracefully otherwise; this is advisory not a bypass

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Curl test for threadpool responsiveness required explicit `type=audio/mpeg` flag — curl sends `application/octet-stream` by default which the new MIME guard correctly rejects. Using `type=audio/mpeg` flag in curl confirmed the guard works and the pipeline still produces correct results.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- /analyze endpoint is production-ready: validates input, runs pipeline asynchronously, server stays responsive
- Any future phase extending /analyze should add validation guards in the same order (size -> MIME -> I/O) before pipeline
- Phase 6+ can call /analyze with confidence: 413 for oversized, 415 for non-MP3, 500 for pipeline errors, 200 for success

---
*Phase: 05-upload-handler-and-async-processing*
*Completed: 2026-03-04*
