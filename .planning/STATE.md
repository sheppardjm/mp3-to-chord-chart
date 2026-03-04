# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-03)

**Core value:** Accurately detect chord changes from an MP3 and align them to the right positions in user-provided lyrics, producing a readable chord chart.
**Current focus:** Phase 5 in progress — upload validation (413/415) and threadpool async processing added to /analyze; event loop no longer blocked during 10-60s pipeline

## Current Position

Phase: 5 of 8 (Upload Handler and Async Processing) — In progress
Plan: 1 of 1 in current phase (05-01 complete)
Status: Phase 5 plan 1 complete — /analyze has HTTP 413/415 guards and run_in_threadpool offloading; baseline preserved (107.7 BPM, 8 sections, 436 beats)
Last activity: 2026-03-04 — Completed 05-01-PLAN.md (file validation + starlette threadpool; /health responds in 0.008s during active /analyze)

Progress: [█████░░░░░] 55% (11/20 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 8 (through 04-02, 2 plans counted for phase 4)
- Average duration: ~5.8 minutes
- Total execution time: ~0.78 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-project-scaffold | 2 | ~3.5 min | ~1.75 min |
| 02-audio-loading-and-key-detection | 2 | ~21 min | ~10.5 min |
| 03-beat-tracking-and-chord-detection | 3 | ~19 min | ~6.3 min |
| 04-structural-segmentation | 2 | ~12 min | ~6 min |
| 05-upload-handler-and-async-processing | 1 | ~2 min | ~2 min |

**Recent Trend:**
- Last 5 plans: 03-03 (~15 min w/ checkpoint), 04-01 (~2 min), 04-02 (~10 min w/ checkpoint), 05-01 (~2 min)
- Trend: Simple implementation plans run fast (~2 min); Phase 5 plan 1 was straightforward refactor with no blockers

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
- 03-02 D001: p_loop=0.5 for Viterbi transition matrix — values above 0.7 collapse songs to 1-2 segments; 0.5 produces 14 musically coherent segments
- 03-02 BASELINE: "Don't Cave.mp3" = 4 unique chords (G:maj, A:min, C:maj, D:maj), 14 segments, 436 beats — correct for G major folk/pop song (I, ii, IV, V chords)
- 03-03 D001: :7 quality confusion is a known limitation — template matching cannot distinguish Am7 from A:min, and Bm is confused as B:7 due to template overlap; root detection is accurate; quality requires more sophisticated approach; no vocabulary change for Phase 3
- 03-03 BASELINE: "Wild Horses.mp3" = 8 unique chords detected (G:maj, A:min, B:7, C:maj, D:maj + false G:7, D:7, A:7); all 5 expected roots present (G, A, B, C, D); approved by user as reasonable for template matching
- 04-01 D001: Generic Section A/B/C labels chosen over Verse/Chorus -- no reliable auto-detection from chroma alone (research confirms)
- 04-01 D002: compute_k() floor=4 and n_beats-1 guard -- ensures meaningful segmentation for short songs, prevents sklearn ValueError
- 04-02 D001: Re-compute chroma_sync in /analyze rather than modifying detect_chords_pipeline() -- preserves Phase 3 contract; ~0.5s re-computation cost acceptable for 4-min songs
- 04-02 D002: File size/MIME validation and async processing deferred to Phase 5 -- out of scope for pipeline integration
- 05-01 D001: ALLOWED_MIME_TYPES = {"audio/mpeg", "audio/mp3"} — browsers send audio/mpeg; curl requires explicit type=audio/mpeg flag; application/octet-stream (curl default) correctly rejected
- 05-01 D002: file.size guard uses "is not None" check — UploadFile.size is None when Content-Length header absent; guard is advisory when size known, skips gracefully otherwise

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 3 complete. :7 quality confusion documented as known limitation (see 03-03 D001). No blocker for Phase 4.
- Phase 4: Laplacian segmentation k-parameter needs tuning per song type — allow section label editing in UI from the start
- Phase 8: svguitar chord coverage for edge-case chord names (Ebm, F#7) must be tested early; confirm fallback behavior
- 02-02 NOTE: numba stub @stencil path triggered in chroma_cqt -> estimate_tuning -> piptrack chain. Fixed with tuning=0.0. Watch for other librosa functions that call estimate_tuning or piptrack without explicit tuning parameter.

## Session Continuity

Last session: 2026-03-04T06:52:10Z
Stopped at: Completed 05-01-PLAN.md — file validation guards (413/415) + run_in_threadpool offloading; /health responds in 0.008s during active /analyze; baseline preserved
Resume file: None
