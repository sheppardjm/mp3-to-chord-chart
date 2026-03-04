# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** Accurately detect chord changes from an MP3 and align them to the right positions in user-provided lyrics, producing a readable chord chart.
**Current focus:** Phase 2 — audio loading complete, key detection next

## Current Position

Phase: 2 of 8 (Audio Loading and Key Detection) — In progress
Plan: 1 of ~2 in current phase
Status: In progress
Last activity: 2026-03-04 — Completed 02-01-PLAN.md (librosa install + audio loader with HPSS)

Progress: [██░░░░░░░░] 19% (3/16 estimated plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: ~5.6 minutes
- Total execution time: 0.23 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-project-scaffold | 2 | ~3.5 min | ~1.75 min |
| 02-audio-loading-and-key-detection | 1 | 13 min | 13 min |

**Recent Trend:**
- Last 5 plans: 01-01 (1.5 min), 01-02 (2 min), 02-01 (13 min)
- Trend: Audio plans take longer due to library compatibility and empirical verification

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

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 3: 7th chord template detection accuracy has no published baseline — validate empirically before committing to chord vocabulary
- Phase 4: Laplacian segmentation k-parameter needs tuning per song type — allow section label editing in UI from the start
- Phase 8: svguitar chord coverage for edge-case chord names (Ebm, F#7) must be tested early; confirm fallback behavior
- 02-01 NOTE: numba stub disables JIT compilation — if any librosa function produces wrong output (e.g., filter operations), investigate whether numba's @stencil was providing correct semantics. All tested paths (hpss, load) work correctly.

## Session Continuity

Last session: 2026-03-04
Stopped at: Completed 02-01-PLAN.md — librosa installed, load_audio() verified on Don't Cave.mp3
Resume file: None
