---
phase: 03-beat-tracking-and-chord-detection
plan: "02"
subsystem: audio
tags: [librosa, numpy, chord-detection, viterbi, hmm, chroma, template-matching]

# Dependency graph
requires:
  - phase: 03-beat-tracking-and-chord-detection
    plan: "01"
    provides: beat_track_grid(), extract_beat_chroma(), HOP=1024, baseline 107.7 BPM / 435 beats
  - phase: 02-audio-loading-and-key-detection
    provides: load_audio() with y_harmonic and y_percussive from HPSS at hop_length=1024
provides:
  - build_chord_templates(): 36 L2-normalized templates (12 major + 12 minor + 12 dom7)
  - detect_chords(): beat-level chord labeling via cosine similarity + Viterbi HMM smoothing
  - collapse_chords(): merge consecutive identical labels into timestamped segments
  - detect_chords_pipeline(): full pipeline from load_audio() dict to collapsed chord segments
  - Empirical baseline: "Don't Cave.mp3" = 107.7 BPM, 436 beats, 14 segments, 4 unique chords (G:maj, A:min, C:maj, D:maj)
affects:
  - 03-03-accuracy-validation
  - 04-structural-segmentation
  - 05-fastapi-endpoint

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "36-chord vocabulary: 12 major (intervals 0,4,7) + 12 minor (0,3,7) + 12 dom7 (0,4,7,10), L2-normalized"
    - "Cosine similarity via template_matrix @ chroma_norm (no explicit arccos needed)"
    - "Viterbi smoothing with librosa.sequence.transition_loop(36, p_loop=0.5) — allows transitions at every beat"
    - "Collapse pass merges consecutive identical labels to produce human-readable timestamped segments"
    - "Flat-side note naming: C/Db/D/Eb/E/F/F#/G/Ab/A/Bb/B matching key_detection.py ROOTS"

key-files:
  created: []
  modified:
    - backend/audio/chord_detection.py

key-decisions:
  - "03-02 D001: p_loop=0.5 for Viterbi transition matrix — values above 0.7 collapse entire songs to 1-2 segments; 0.5 produces 14 musically coherent segments on Don't Cave.mp3"
  - "03-02 BASELINE: Don't Cave.mp3 = 4 unique chords (G:maj, A:min, C:maj, D:maj), 14 segments, 436 beats, 107.7 BPM — correct for a G major folk/pop song"

patterns-established:
  - "build_chord_templates(): always build fresh from root+intervals loop; never hardcode binary rows"
  - "detect_chords(): L2-normalize chroma columns before template dot product; clip negatives before softmax-style normalization"
  - "collapse_chords(): zip(chord_seq, beat_times); append only on chord change"
  - "detect_chords_pipeline(): pass audio dict directly from load_audio(); extract y_percussive and y_harmonic inside pipeline"

# Metrics
duration: 2min
completed: 2026-03-04
---

# Phase 3 Plan 02: Chord Template Matching and Viterbi Smoothing Summary

**36-template cosine similarity + Viterbi HMM (p_loop=0.5) chord detection producing 14 musically coherent segments (G:maj, A:min, C:maj, D:maj) from 436 beats of "Don't Cave.mp3" via librosa.sequence.viterbi and transition_loop**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-04T05:10:27Z
- **Completed:** 2026-03-04T05:12:10Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Implemented `build_chord_templates()` producing 36 L2-normalized 12-dimensional chord template vectors (12 major, 12 minor, 12 dominant 7th), verified shape (36, 12) and unit-norm rows
- Implemented `detect_chords()` using cosine similarity (template_matrix @ chroma_norm) + Viterbi smoothing with `librosa.sequence.transition_loop(36, 0.5)` — p_loop=0.5 produces musically coherent sequences without over-smoothing
- Implemented `collapse_chords()` merging consecutive identical chord labels into timestamped segments
- Implemented `detect_chords_pipeline()` orchestrating all five steps from `load_audio()` dict to collapsed segments
- Full end-to-end validation against "Don't Cave.mp3": 107.7 BPM, 436 beats, 14 chord segments, 4 unique chords — all 6 validation checks passed

## Task Commits

Each task was committed atomically:

1. **Task 1: Add chord templates, Viterbi smoothing, collapse, and pipeline** - `067f395` (feat)
2. **Task 2: Validate full pipeline against Don't Cave.mp3** - no separate commit (validation only, no file changes)

**Plan metadata:** (committed below)

## Files Created/Modified

- `backend/audio/chord_detection.py` — added NOTES constant, build_chord_templates(), detect_chords(), collapse_chords(), detect_chords_pipeline(); file now 243 lines with 7 public symbols

## Decisions Made

- **03-02 D001: p_loop=0.5 for Viterbi** — The plan specified p_loop=0.5 and documented that values above 0.7 over-smooth. Empirically confirmed: 0.5 produces 14 distinct segments on Don't Cave.mp3 (a 4-minute song with clear chord changes every 10–30 seconds). This is the correct setting.
- **03-02 BASELINE** — "Don't Cave.mp3" chord detection output:
  - 107.7 BPM, 436 beats (consistent with 03-01 baseline)
  - 14 chord segments, 4 unique chords: G:maj, A:min, C:maj, D:maj
  - Musically correct: G major song with relative minor (A:min = ii of G), subdominant (C:maj = IV), and dominant (D:maj = V)
  - First segment: G:maj at 0.0s; last segment: G:maj from 231.1s onward

## Chord Segments (full output for reference)

```
  0.0s  G:maj
 59.4s  A:min
 65.0s  G:maj
 77.3s  C:maj
106.8s  G:maj
124.6s  A:min
130.2s  G:maj
142.5s  C:maj
172.0s  G:maj
195.4s  D:maj
201.5s  A:min
207.1s  G:maj
219.4s  A:min
231.1s  G:maj
```

Unique chords (4): A:min, C:maj, D:maj, G:maj

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. All librosa.sequence functions (transition_loop, viterbi) worked correctly with the numba no-op stub — they do not use @guvectorize internally. The pipeline ran end-to-end without errors on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `detect_chords_pipeline()` is ready for Plan 03-03 accuracy validation
- Empirical baseline established: 4 chords (G:maj, A:min, C:maj, D:maj), 14 segments — Plan 03-03 can use this as the expected output for regression testing
- Note from STATE.md: 7th chord detection accuracy has no published baseline — if Plan 03-03 adds more test songs, look for :7 chord presence; "Don't Cave.mp3" appears to use only triads
- HOP=1024 constraint fully carried through; all frame-based operations consistent

---
*Phase: 03-beat-tracking-and-chord-detection*
*Completed: 2026-03-04*
