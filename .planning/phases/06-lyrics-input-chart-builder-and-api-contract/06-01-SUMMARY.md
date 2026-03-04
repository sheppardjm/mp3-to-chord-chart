---
phase: 06-lyrics-input-chart-builder-and-api-contract
plan: "01"
subsystem: api
tags: [pydantic, python, models, api-contract, response-schema]

# Dependency graph
requires:
  - phase: 05-upload-handler-and-async-processing
    provides: FastAPI /analyze endpoint that will use these response models
provides:
  - Pydantic v2 ChartData root model with key, bpm, unique_chords, sections fields
  - Pydantic v2 Section model with label and lines fields
  - Pydantic v2 LyricLine model with text and chords fields
  - Pydantic v2 ChordAnnotation model with chord and position fields
  - Importable from audio.models for use by chart_builder.py and main.py
affects:
  - 06-02 chart_builder.py constructs and returns ChartData instances
  - 06-03 main.py uses response_model=ChartData on /analyze endpoint

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pydantic v2 BaseModel for API response contracts (leaf-to-root definition order)
    - Built-in list[] generics (Python 3.9+) instead of typing.List

key-files:
  created:
    - backend/audio/models.py
  modified: []

key-decisions:
  - "No field validators, Config classes, or model_config — pure data containers only"
  - "Leaf-to-root definition order (ChordAnnotation -> LyricLine -> Section -> ChartData) to avoid forward references"
  - "position: float represents 0.0-1.0 proportional position within a lyric line"

patterns-established:
  - "API contract models: defined in audio/models.py, imported by chart_builder and main"
  - "Pydantic v2 syntax: from pydantic import BaseModel, use list[] not List[]"

# Metrics
duration: 1min
completed: 2026-03-04
---

# Phase 6 Plan 01: Pydantic v2 Response Models Summary

**Four Pydantic v2 BaseModel classes (ChordAnnotation, LyricLine, Section, ChartData) defining the /analyze API contract with nested chord-annotated lyric structure**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-04T14:37:47Z
- **Completed:** 2026-03-04T14:38:25Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created backend/audio/models.py with four Pydantic v2 BaseModel classes in dependency order
- All models import cleanly from audio.models
- ChartData constructs from valid nested data and serializes correctly via model_dump()
- Invalid data raises pydantic.ValidationError as expected
- Pure Pydantic v2 syntax: no v1 patterns, no typing imports, built-in list[] generics

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Pydantic v2 models in backend/audio/models.py** - `0321ecb` (feat)

**Plan metadata:** _(docs commit to follow)_

## Files Created/Modified
- `backend/audio/models.py` - Four Pydantic v2 BaseModel classes forming the API contract for the /analyze endpoint

## Decisions Made
- No field validators, Config classes, or model_config added — models are pure data containers per plan specification
- Leaf-to-root definition order ensures no forward references needed (ChordAnnotation defined before LyricLine which uses it, etc.)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- backend/audio/models.py is ready for import by chart_builder.py (Plan 06-02)
- ChartData can be passed as response_model= to /analyze in main.py (Plan 06-03)
- No blockers for Phase 6 continuation

---
*Phase: 06-lyrics-input-chart-builder-and-api-contract*
*Completed: 2026-03-04*
