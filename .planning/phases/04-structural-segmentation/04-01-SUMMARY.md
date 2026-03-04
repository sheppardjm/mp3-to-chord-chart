---
phase: 04-structural-segmentation
plan: "01"
subsystem: audio
tags: [librosa, segmentation, agglomerative-clustering, chroma, numpy, structural-analysis]

# Dependency graph
requires:
  - phase: 03-beat-tracking-and-chord-detection
    provides: beat-synced chroma (chroma_sync), beat_times, chord_sequence from detect_chords_pipeline()
provides:
  - compute_k() heuristic for section count from song duration
  - segment_song() agglomerative clustering on stack_memory-enhanced beat-synced chroma
  - build_sections() sections array with label/start/chord_sequence for API response
  - DEFAULT_LABELS list of 12 generic section names (Section A through Section L)
  - 23-test structural test suite validating all invariants on synthetic data
affects:
  - 04-02 (section labels editing integration)
  - 05-api-layer (sections array in API response schema)
  - 08-ui (section display in chord chart UI)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "beat-synced segmentation: operate on Phase 3 chroma_sync arrays without new audio loading"
    - "stack_memory(n_steps=3, delay=1) temporal context enhancement before agglomerative clustering"
    - "filter boundary_beats < len(beat_times) to guard fix_frames off-by-one"
    - "collapse consecutive identical chords within each section (same pattern as Phase 3)"

key-files:
  created:
    - backend/audio/segmentation.py
    - backend/tests/test_segmentation.py
  modified: []

key-decisions:
  - "Generic Section A/B/C labels chosen over Verse/Chorus -- no reliable auto-detection from chroma alone"
  - "compute_k() floor of 4 ensures meaningful segmentation even for short songs"
  - "n_beats-1 guard in compute_k() prevents sklearn AgglomerativeClustering ValueError"
  - "beat_times length is authoritative n_beats, not chroma_sync.shape[1] (fix_frames off-by-one)"

patterns-established:
  - "Segmentation operates on Phase 3 output arrays only -- no new audio I/O"
  - "run_all_tests() pattern for self-contained test files (consistent with Phase 3)"

# Metrics
duration: 2min
completed: 2026-03-04
---

# Phase 4 Plan 01: Structural Segmentation Module Summary

**Beat-synced agglomerative clustering via librosa.segment.agglomerative() on stack_memory-enhanced chroma, with build_sections() producing labeled section arrays with collapsed chord sequences for API response**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-04T05:55:21Z
- **Completed:** 2026-03-04T05:57:49Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- segmentation.py module created with 4 exports: compute_k(), segment_song(), build_sections(), DEFAULT_LABELS
- segment_song() produces beat-aligned section boundaries using agglomerative clustering on stack_memory-enhanced chroma (no new audio loading)
- build_sections() produces sections array matching API response schema: label, start, chord_sequence with collapsed chords
- 23-test structural test suite validating all Phase 4 success criteria on synthetic data (CI-ready, no audio files)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create segmentation module** - `6090bb9` (feat)
2. **Task 2: Create structural test suite** - `b3e6312` (test)

**Plan metadata:** (to be added in final commit)

## Files Created/Modified
- `backend/audio/segmentation.py` - compute_k(), segment_song(), build_sections(), DEFAULT_LABELS
- `backend/tests/test_segmentation.py` - 23 structural tests for segmentation invariants

## Decisions Made
- Generic Section A/B/C labels chosen over Verse/Chorus naming -- no reliable auto-detection from chroma alone (research confirms)
- compute_k() floor of 4 ensures meaningful segmentation even for short/simple songs
- n_beats-1 guard in compute_k() prevents sklearn AgglomerativeClustering ValueError on songs with few beats
- beat_times length is authoritative for n_beats rather than chroma_sync.shape[1] -- guards against fix_frames off-by-one (Pitfall 3 from research)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - module imported cleanly, all 23 tests passed on first run, no regression in Phase 3 tests (18 passed, 0 failed).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- segmentation.py is ready to integrate with Phase 3's detect_chords_pipeline() output in Phase 5 API layer
- build_sections() output schema matches planned API response format
- Section label editing should be supported in UI from the start (Phase 4 concern: no reliable Verse/Chorus detection)
- 04-02 plan can proceed to integrate segmentation into the full pipeline

---
*Phase: 04-structural-segmentation*
*Completed: 2026-03-04*
