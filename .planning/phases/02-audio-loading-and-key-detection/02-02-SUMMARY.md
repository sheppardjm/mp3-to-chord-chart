---
phase: 02-audio-loading-and-key-detection
plan: "02"
subsystem: audio
tags: [librosa, scipy, numpy, key-detection, krumhansl-schmuckler, chroma, enharmonic, music-theory]

# Dependency graph
requires:
  - phase: 02-01
    provides: load_audio() returning y_harmonic from HPSS separation
provides:
  - detect_key(y_harmonic, sr) -> "ROOT:mode" string (e.g. "G:maj", "Bb:min")
  - get_note_names(key) -> 12-element list of correctly spelled note names
  - Established baseline key for "Don't Cave.mp3": G major
affects:
  - 03-chord-detection (key drives enharmonic chord naming throughout the pipeline)
  - All downstream phases that name chords

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "K-S key detection: chroma_cqt mean -> zscore normalize -> circulant dot product over 24 keys"
    - "chroma_cqt with tuning=0.0 bypasses numba stencil path (required for Python 3.14/x86_64 compat)"
    - "get_note_names() thin wrapper over librosa.key_to_notes() — never hand-roll enharmonic logic"

key-files:
  created:
    - backend/audio/key_detection.py
  modified: []

key-decisions:
  - "02-02 D001: tuning=0.0 passed to chroma_cqt — bypasses estimate_tuning/piptrack/numba stencil which fails with no-op stub"
  - "02-02 D002: ROOTS list uses flat-side convention (Db/Eb/Ab/Bb, F# for tritone) matching music theory standard"
  - "02-02 BASELINE: Don't Cave.mp3 detected as G:maj (one sharp, F#) — plausible for guitar/rock; validate in Phase 3"

patterns-established:
  - "Key string format: ROOT:mode (e.g. G:maj, Bb:min) — compatible with librosa.key_to_notes()"
  - "Always use y_harmonic (not raw y) for chroma extraction — reduces percussive noise in pitch-class analysis"
  - "Use scipy.linalg.circulant for vectorized K-S rotation — avoids explicit loop over 24 keys"

# Metrics
duration: ~8min
completed: 2026-03-04
---

# Phase 2 Plan 02: Key Detection Summary

**Krumhansl-Schmuckler key detection over chroma_cqt with flat/sharp enharmonic naming, detecting G:maj for "Don't Cave.mp3"**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-04T04:16:01Z
- **Completed:** 2026-03-04T04:24:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Implemented `detect_key(y_harmonic, sr)` using Krumhansl-Schmuckler correlation over `chroma_cqt` features with `scipy.linalg.circulant` for vectorized 24-key scoring
- Verified enharmonic naming: flat keys (Bb:maj, F:maj, Eb:maj, Ab:maj) produce Db/Eb/Ab/Bb spellings; sharp keys (G:maj) produce F#
- Established key baseline for "Don't Cave.mp3": **G major** (note names: C, C#, D, D#, E, F, F#, G, G#, A, A#, B)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create key detection module with K-S algorithm and enharmonic naming** - `8d67585` (feat)
2. **Task 2: Validate key detection and enharmonic naming against test data + numba stencil fix** - `660bc16` (fix)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `backend/audio/key_detection.py` - K-S key detection (detect_key, get_note_names) — 81 lines

## Decisions Made

- **D001: tuning=0.0 in chroma_cqt** — `estimate_tuning()` internally calls `piptrack()` -> `_parabolic_interpolation()` -> `_pi_stencil` (numba `@stencil`). The no-op numba stub (installed for Python 3.14/x86_64 compat) does not JIT-compile stencils; the raw function receives array inputs where Python scalar comparison (`if np.abs(b) >= np.abs(a)`) is ambiguous. Passing `tuning=0.0` (standard A=440 Hz) skips this path entirely. Correct for recorded commercial music.
- **D002: ROOTS flat-side convention** — `['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']` matches circle-of-fifths conventions. When detect_key selects a root, `get_note_names()` via `librosa.key_to_notes()` produces consistent enharmonic spelling for all 12 notes.
- **BASELINE: "Don't Cave.mp3" = G:maj** — K-S algorithm converges on G major with 23.77 score vs next best. G major has one sharp (F#), musically plausible for guitar-based rock. Phase 3 chord detection should expect F# in chord names, not Gb.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] chroma_cqt -> estimate_tuning -> numba stencil ValueError**

- **Found during:** Task 2 (validation against "Don't Cave.mp3")
- **Issue:** `librosa.feature.chroma_cqt()` without explicit tuning calls `estimate_tuning()`, which calls `piptrack()`, which calls `_parabolic_interpolation()`, which uses a numba `@stencil` decorated function `_pi_stencil`. The no-op numba stub (required for Python 3.14 x86_64 compatibility, documented in 02-01) passes `@stencil` through without JIT compilation. The raw stencil function uses `if np.abs(b) >= np.abs(a)` — a scalar comparison on array inputs — producing `ValueError: The truth value of an array with more than one element is ambiguous`.
- **Fix:** Added `tuning=0.0` parameter to `chroma_cqt()` call. This bypasses `estimate_tuning()` entirely. `tuning=0.0` = standard A=440 Hz, correct assumption for recorded commercial music.
- **Files modified:** `backend/audio/key_detection.py` (line 37: `chroma_cqt(y=y_harmonic, sr=sr, tuning=0.0)`)
- **Verification:** Full pipeline (load_audio -> detect_key -> get_note_names) runs without error; G:maj detected for "Don't Cave.mp3"
- **Committed in:** `660bc16` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — numba stencil path triggered by tuning estimation)
**Impact on plan:** Fix necessary for correctness on Python 3.14/x86_64. No scope creep. tuning=0.0 is a sound default for commercial recordings.

## Issues Encountered

The numba stub issue (documented in 02-01 STATE.md concern) manifested specifically in the `chroma_cqt` -> `estimate_tuning` -> `piptrack` -> `_parabolic_interpolation` -> `@stencil` call chain. The fix (tuning=0.0) is minimal and correct. No other numba stub failures encountered.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Key detection complete: `detect_key(y_harmonic, sr)` returns "ROOT:mode" string for any audio
- Enharmonic naming verified: `get_note_names(key)` returns correctly spelled notes
- **Baseline established: "Don't Cave.mp3" is G major** — Phase 3 chord templates should expect F# naming (not Gb)
- All numba stencil paths in the chroma/key pipeline now handled (tuning=0.0 pattern)
- Phase 3 (chord detection) can import both `load_audio` and `detect_key` and proceed with template matching

---
*Phase: 02-audio-loading-and-key-detection*
*Completed: 2026-03-04*
