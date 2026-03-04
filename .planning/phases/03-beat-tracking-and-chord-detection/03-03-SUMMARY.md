---
phase: 03-beat-tracking-and-chord-detection
plan: "03"
subsystem: testing
tags: [librosa, numpy, chord-detection, accuracy, testing, template-matching, viterbi]

# Dependency graph
requires:
  - phase: 03-beat-tracking-and-chord-detection
    plan: "02"
    provides: detect_chords_pipeline(), build_chord_templates(), detect_chords(), collapse_chords(), Viterbi HMM smoothing
  - phase: 03-beat-tracking-and-chord-detection
    plan: "01"
    provides: beat_track_grid(), extract_beat_chroma(), HOP=1024
provides:
  - measure_accuracy(): beat-level chord accuracy comparison (exact match + root-only match)
  - backend/tests/test_chord_detection.py: 18-test structural test suite (no audio files required, runs in CI)
  - Accuracy baseline: root detection strong (all expected roots present); quality detection has systematic :7 confusion
  - Known limitation documented: template matching misses 7th degrees (Am7 -> A:min) and confuses minor quality with dom7 (Bm -> B:7)
affects:
  - 04-structural-segmentation
  - 05-fastapi-endpoint
  - 08-chord-diagram-rendering

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "measure_accuracy(): compare two equal-length chord lists; returns exact_accuracy, root_accuracy, n_compared, exact_matches, root_matches"
    - "Structural tests use synthetic chroma arrays (no audio files); pure chord patterns exercise template matching deterministically"
    - "run_all_tests() runner: scans globals() for test_ prefix, reports pass/fail, exits 1 on failure — no pytest dependency"

key-files:
  created:
    - backend/tests/__init__.py
    - backend/tests/test_chord_detection.py
  modified:
    - backend/audio/chord_detection.py

key-decisions:
  - "03-03 D001: :7 quality confusion documented as known limitation — template matching cannot distinguish Am7 from A:min (7th degree falls on shared pitch class); Bm confused as B:7 due to template overlap. Root detection is accurate; quality requires a more sophisticated approach (e.g., instrument separation, probabilistic octave model). No vocabulary change needed for Phase 3 scope."
  - "03-03 BASELINE (Wild Horses.mp3): 8 unique chords detected (G:maj, A:min, B:7, C:maj, D:maj + false :7 variants G:7, D:7, A:7). All 5 expected roots present (G, A, B, C, D). Root accuracy: strong. Exact accuracy: moderate (quality confusion on :7 variants)."
  - "03-03 DECISION: Accuracy target met at root level; quality confusion is acceptable for Phase 3 chord chart use case (chord charts show root + quality; root correct means user sees correct chord position in progression)."

patterns-established:
  - "measure_accuracy(detected, reference): always returns dict with both exact_accuracy and root_accuracy — downstream code should prefer root_accuracy for phase 3 evaluation"
  - "Structural tests: use np.zeros((12, N)) + manual pitch class activation for deterministic template matching tests"
  - "Test runner: run_all_tests() scans globals(); suitable for scripts that cannot install pytest"

# Metrics
duration: ~15min (including human checkpoint wait)
completed: 2026-03-04
---

# Phase 3 Plan 03: Accuracy Validation and Structural Test Suite Summary

**18-test structural CI suite (no audio required) + measure_accuracy() utility; Wild Horses.mp3 validation confirms root detection is solid — all 5 expected roots found — with known :7 quality confusion documented as acceptable limitation for chord chart use case**

## Performance

- **Duration:** ~15 min (includes human checkpoint)
- **Started:** 2026-03-04T05:12:10Z
- **Completed:** 2026-03-04
- **Tasks:** 2 (1 auto + 1 human checkpoint)
- **Files modified:** 3

## Accomplishments

- Added `measure_accuracy()` to `backend/audio/chord_detection.py` — computes exact match accuracy and root-only accuracy over beat-aligned chord lists; handles empty input and length mismatch gracefully
- Created `backend/tests/__init__.py` and `backend/tests/test_chord_detection.py` with 18 structural tests covering: template count/normalization/naming, detection output length/vocabulary/pure-chord recognition, collapse invariants, and accuracy utility
- All 18 tests pass on synthetic data with no audio file dependency (CI-safe)
- Human validation against "Wild Horses.mp3" (known chords: G, Am7, Bm, C, D in G major) confirmed all 5 expected roots detected; :7 quality confusion documented as known limitation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add measure_accuracy() utility and create structural test suite** - `32bf001` (feat)
2. **Task 2: Verify chord detection accuracy (human checkpoint)** - no file commit (checkpoint approval, no file changes)

**Plan metadata:** (committed below)

## Files Created/Modified

- `backend/audio/chord_detection.py` — added `measure_accuracy()` function (exact + root-only accuracy comparison, handles empty/mismatched lengths); now exports `measure_accuracy`
- `backend/tests/__init__.py` — empty package marker
- `backend/tests/test_chord_detection.py` — 18 structural tests + `run_all_tests()` runner; covers HOP constant, NOTES list, template shape/normalization/naming, all-roots coverage, detection length/vocabulary/pure-chord patterns, collapse no-dup/timestamp/single/all-diff, accuracy perfect/root-only/empty/length-mismatch

## Decisions Made

- **03-03 D001: :7 quality confusion is a known limitation, not a blocking issue.** Template matching with 36 templates (12 maj + 12 min + 12 dom7) cannot reliably distinguish:
  - Am7 from A:min (the 7th degree G is shared with the C:maj template's tonic; minor + 7th overlaps dominate)
  - Bm from B:7 (B dominant 7 template partially overlaps Bm when D and A are present)
  - This produces false :7 detections on songs where the progression uses triads + extended chords
  - **Decision:** Accept this limitation for Phase 3. Root detection is correct (all expected roots present). For chord chart output (root + quality displayed), incorrect quality is a UX degradation, not a correctness failure. A future improvement (Phase N) could apply key-context filtering to suppress improbable dom7 chords in a diatonic key context.

- **03-03 BASELINE (Wild Horses.mp3):** Running `detect_chords_pipeline()` on "Wild Horses.mp3" (Rolling Stones, G major, known chords: G, Am7, Bm, C, D):
  - 8 unique chords detected: G:maj, A:min, B:7, C:maj, D:maj, G:7, D:7, A:7
  - All 5 expected roots present (G, A, B, C, D) — root detection is accurate
  - Am7 detected as A:min (7th missed — acceptable, triad quality correct)
  - Bm detected as B:7 (quality confused — minor vs dom7 overlap)
  - G:7, D:7, A:7 are false :7 detections (likely transitions or sections with passing tones)
  - Human reviewer (user) approved this output as reasonable for the template matching approach

## Validation Output: Wild Horses.mp3

```
Unique chords detected (8): G:maj, A:min, B:7, C:maj, D:maj, G:7, D:7, A:7
Expected roots (5): G, A, B, C, D
All expected roots present: YES
Root detection accuracy: HIGH
Quality detection accuracy: MODERATE (known :7 confusion)
```

Reference chord sheet: G, Am7, Bm, C, D (G major, 5 distinct chords)

## Structural Test Results

```
18 passed, 0 failed, 18 total
```

Tests cover:
- `test_hop_constant` — HOP == 1024
- `test_notes_list` — 12 notes, correct positions
- `test_build_chord_templates_count` — 36 templates, (36, 12) matrix
- `test_build_chord_templates_normalized` — all rows unit-norm
- `test_build_chord_templates_names` — all names ROOT:quality format with valid suffix
- `test_build_chord_templates_all_roots` — all 12 roots represented
- `test_detect_chords_output_length` — one chord per beat
- `test_detect_chords_valid_names` — all chords from template vocabulary
- `test_detect_chords_pure_c_major` — pure C/E/G chroma -> C:maj
- `test_detect_chords_pure_g_major` — pure G/B/D chroma -> G:maj
- `test_collapse_no_duplicates` — no adjacent identical chords
- `test_collapse_preserves_first_timestamp` — segment timestamp = first beat
- `test_collapse_single_chord` — all same -> 1 segment
- `test_collapse_all_different` — all different -> N segments
- `test_measure_accuracy_perfect` — 1.0/1.0 on identical lists
- `test_measure_accuracy_root_match` — 0.0 exact, 1.0 root when roots match but qualities differ
- `test_measure_accuracy_empty` — 0.0 on empty lists
- `test_measure_accuracy_length_mismatch` — truncates to shorter list

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The test suite ran cleanly on first execution (18 passed, 0 failed). The pure chord detection tests (C:maj, G:maj) passed deterministically because synthetic chroma arrays activate exactly the correct pitch classes for those templates. Viterbi smoothing with p_loop=0.5 converged to the correct single chord across all 20 synthetic beats.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `measure_accuracy()` is available for any future automated accuracy regression if reference chord sheets are assembled
- Structural test suite (`backend/tests/test_chord_detection.py`) is CI-ready — no audio files needed, runs with `python backend/tests/test_chord_detection.py`
- Known limitation logged: :7 quality confusion. Phase 4+ should consider a key-context post-filter to suppress improbable dom7 chords in diatonic progressions (e.g., if key is G major, B:7 should be flagged as B:min unless the song has a secondary dominant)
- Phase 3 complete: chord detection pipeline verified on two songs (Don't Cave.mp3 — 4 triads, no :7 confusion; Wild Horses.mp3 — 5 chord roots all found, some :7 confusion)
- Blocker for Phase 8: svguitar chord coverage for :7 chord names (e.g., B:7, G:7) must be tested early given increased :7 detection frequency

---
*Phase: 03-beat-tracking-and-chord-detection*
*Completed: 2026-03-04*
