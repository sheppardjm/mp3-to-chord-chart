# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** Accurately detect chord changes from an MP3 and align them to the right positions in user-provided lyrics, producing a readable chord chart.
**Current focus:** Phase 3 in progress — beat tracking complete, chord template matching next

## Current Position

Phase: 3 of 8 (Beat Tracking and Chord Detection) — In progress
Plan: 1 of 3 in current phase
Status: In progress — 03-01 complete, ready for 03-02
Last activity: 2026-03-04 — Completed 03-01-PLAN.md (beat tracking, beat-synced chroma, 107.7 BPM / 435 beats baseline)

Progress: [████░░░░░░] 31% (5/16 estimated plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: ~6.1 minutes
- Total execution time: 0.41 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-project-scaffold | 2 | ~3.5 min | ~1.75 min |
| 02-audio-loading-and-key-detection | 2 | ~21 min | ~10.5 min |

**Recent Trend:**
- Last 5 plans: 01-01 (1.5 min), 01-02 (2 min), 02-01 (13 min), 02-02 (~8 min), 03-01 (~2 min)
- Trend: Audio plans slower due to library compat and empirical verification; 03-01 fast (clean implementation, no new compat issues)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: Pipeline-first order mandated — audio pipeline must produce correct chord data before any UI work begins
- Roadmap: Beat-synchronized template matching with Viterbi smoothing required (raw chroma argmax produces unusable output)
- Roadmap: FastAPI threadpool (run_in_executor) required for async audio processing — synchronous handling hangs the server
- 01-01 D001: Install fastapi and uvicorn as separate packages (not fastapi[standard]) — fastapi[standard] fails on Python 3.14 due to transitive binary build failures
- 02-01 D001: numba installed as no-op stub — llvmlite 0.46.0b1 "universal2" wheel is arm64-only; Python 3.14 runs x86_64 (Rosetta); stub provides jit/stencil/guvectorize as passthrough decorators
- 02-01 D002: HPSS uses hop_length=1024 (2x default) — default hop=512 produces 718MB peak exceeding 600MB limit; doubled hop gives 401MB peak with 99.09% harmonic correlation preserved
- 02-02 D001: tuning=0.0 passed to chroma_cqt — bypasses estimate_tuning/piptrack/numba stencil which fails with no-op stub; standard A=440 Hz is correct for commercial recordings
- 02-02 D002: ROOTS flat-side convention (Db/Eb/Ab/Bb, F# for tritone) — standard music theory, compatible with librosa.key_to_notes()
- 02-02 BASELINE: "Don't Cave.mp3" detected as G:maj — Phase 3 chord templates must use F# naming (not Gb)
- 03-01 D001: beat_track_grid() uses regular grid (not beat_track()) — librosa.beat.beat_track() broken with numba no-op stub (@guvectorize incompatible with stub passthrough)
- 03-01 BASELINE: "Don't Cave.mp3" = 107.7 BPM, 435 beats, (12, 436) chroma — baseline for 03-02 chord detection validation

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 3: 7th chord template detection accuracy has no published baseline — validate empirically before committing to chord vocabulary
- Phase 4: Laplacian segmentation k-parameter needs tuning per song type — allow section label editing in UI from the start
- Phase 8: svguitar chord coverage for edge-case chord names (Ebm, F#7) must be tested early; confirm fallback behavior
- 02-02 NOTE: numba stub @stencil path triggered in chroma_cqt -> estimate_tuning -> piptrack chain. Fixed with tuning=0.0. Watch for other librosa functions that call estimate_tuning or piptrack without explicit tuning parameter.

## Session Continuity

Last session: 2026-03-04T05:07:24Z
Stopped at: Completed 03-01-PLAN.md — beat_track_grid() and extract_beat_chroma() verified on Don't Cave.mp3 (107.7 BPM, 435 beats, (12, 436) chroma)
Resume file: None
