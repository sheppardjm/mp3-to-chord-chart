---
phase: 03-beat-tracking-and-chord-detection
verified: 2026-03-04T00:00:00Z
status: gaps_found
score: 4/5 success criteria verified
gaps:
  - truth: "Chord detection accuracy on 5 known test songs is at or above 60% compared to manually verified chord sheets"
    status: failed
    reason: "Only 2 songs were validated (Don't Cave.mp3 and Wild Horses.mp3); the roadmap requires 5. No numeric accuracy percentage was computed via measure_accuracy() — validation was qualitative human approval ('all 5 expected roots present'). A numeric 60% figure against a beat-aligned reference was never produced."
    artifacts:
      - path: "backend/tests/test_chord_detection.py"
        issue: "Test suite covers structural invariants on synthetic data only; no integration test runs detect_chords_pipeline() against real audio with a numeric reference"
      - path: "backend/audio/chord_detection.py"
        issue: "measure_accuracy() exists and is correct, but was never called with actual pipeline output vs a reference chord list to produce a reported percentage"
    missing:
      - "Run detect_chords_pipeline() on at least 3 additional songs beyond Don't Cave and Wild Horses"
      - "Produce beat-aligned reference chord lists for each song"
      - "Call measure_accuracy(detected_chord_sequence, reference_chord_sequence) and report the numeric exact_accuracy and root_accuracy"
      - "Confirm root_accuracy >= 0.60 on each of the 5 songs (or document why the criteria is met on the available 2)"
human_verification:
  - test: "Play or inspect Wild Horses.mp3 pipeline output and compute root_accuracy against the 5-chord reference (G, Am7, Bm, C, D) at beat level"
    expected: "root_accuracy >= 0.60 when measure_accuracy() is called with detected chord_sequence and a reference list of the same length"
    why_human: "No numeric root_accuracy figure was logged in any summary; only 'all 5 expected roots present' qualitative statement. A human needs to run the pipeline and call measure_accuracy() with the actual beat-aligned reference to get a number."
---

# Phase 3: Beat Tracking and Chord Detection — Verification Report

**Phase Goal:** The pipeline produces beat-synchronized, template-matched chord labels that are musically readable — not frame-level noise
**Verified:** 2026-03-04
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Beat positions detected with plausible count (80-160 beats / 3-min 100BPM song) | VERIFIED | `beat_track_grid()` produces 435 beats at 107.7 BPM over 242.6s — ratio 1.00 within 80-120% window. Grid algorithm present at `chord_detection.py:18-66`. |
| 2 | Chord labels change on beat boundaries, not on every audio frame | VERIFIED | `detect_chords()` produces one label per beat column of `chroma_sync` (12, n_beats). `detect_chords_pipeline()` explicitly sequences beat_track_grid → extract_beat_chroma → detect_chords. Frame-level output is impossible by construction. |
| 3 | Adjacent identical chords are collapsed | VERIFIED | `collapse_chords()` at line 170-198 uses `if not result or result[-1]['chord'] != chord` — only appends on change. `test_collapse_no_duplicates` confirms no adjacent dupes. 03-02 SUMMARY documents 14 segments from 436 beats of Don't Cave.mp3. |
| 4 | Chord detection produces only major, minor, and 7th chord labels | VERIFIED | `build_chord_templates()` hardcodes exactly 3 quality suffixes: `':maj'`, `':min'`, `':7'`. No other suffix can appear. Confirmed by `test_build_chord_templates_names` (18 tests pass). |
| 5 | Chord detection accuracy on 5 known test songs >= 60% vs manually verified chord sheets | FAILED | Only 2 songs validated: Don't Cave.mp3 (visual inspection) and Wild Horses.mp3 (qualitative: "all 5 expected roots present"). No numeric accuracy percentage was computed via `measure_accuracy()`. The 5-song threshold in the success criterion was not met. |

**Score:** 4/5 truths verified

---

## Required Artifacts

### From Plan 03-01

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/audio/chord_detection.py` | `beat_track_grid()`, `extract_beat_chroma()`, `HOP=1024` | VERIFIED | 289 lines. All 3 exports present and substantive. No stubs. |

### From Plan 03-02

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/audio/chord_detection.py` | `build_chord_templates()`, `detect_chords()`, `collapse_chords()`, `detect_chords_pipeline()`, `NOTES` | VERIFIED | All 4 functions and `NOTES` constant present. 7 public symbols total. Min 120 lines: file is 289 lines. |

### From Plan 03-03

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/tests/test_chord_detection.py` | Structural test suite, 18+ tests, no audio required | VERIFIED | 157 lines. 18 tests, all pass. Runs on synthetic data. |
| `backend/tests/__init__.py` | Package marker | VERIFIED | Exists (empty). |
| `backend/audio/chord_detection.py` | `measure_accuracy()` export | VERIFIED | Present at line 201-244. Handles exact, root-only, empty, and length-mismatch cases. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `chord_detection.py` | `loader.py` | `beat_track_grid(audio['y_percussive'])` | WIRED | Line 273: `beat_track_grid(audio['y_percussive'], audio['sr'])`. `loader.py` returns `y_percussive` (line 18, 38). |
| `chord_detection.py` | `librosa.onset.onset_strength` | `y=y_percussive, hop_length=HOP` | WIRED | Line 44: exact call confirmed. |
| `chord_detection.py` | `librosa.feature.chroma_cqt` | `tuning=0.0, hop_length=HOP` | WIRED | Line 92: `chroma_cqt(y=y_harmonic, sr=sr, hop_length=HOP, tuning=0.0)` |
| `chord_detection.py` | `librosa.util.sync` | `aggregate=np.median` | WIRED | Line 94: `librosa.util.sync(chroma, beat_frames_fixed, aggregate=np.median)` |
| `chord_detection.py` | `librosa.sequence.viterbi` | HMM smoothing of cosine scores | WIRED | Line 166: `librosa.sequence.viterbi(probs, transition)` |
| `chord_detection.py` | `librosa.sequence.transition_loop` | `p_loop=0.5` | WIRED | Line 165: `transition_loop(len(chord_names), 0.5)` |
| `chord_detection.py` | `librosa.frames_to_time` | `hop_length=HOP` | WIRED | Line 278: `librosa.frames_to_time(beat_frames_fixed[:len(chord_seq)], sr=audio['sr'], hop_length=HOP)` |
| `test_chord_detection.py` | `chord_detection.py` | `from audio.chord_detection import ...` | WIRED | Line 12: imports HOP, NOTES, build_chord_templates, detect_chords, collapse_chords, measure_accuracy. |
| `chord_detection.py` | FastAPI `main.py` | Not yet wired | ORPHANED | `main.py` contains only the `/health` endpoint. `chord_detection.py` is not imported anywhere outside of the test file. This is expected — Phase 5 wires the pipeline to an endpoint. Not a gap for Phase 3. |

**HOP consistency check:** `loader.py` line 32 uses `hop_length=1024`. `chord_detection.py` `HOP = 1024` (line 15). All frame-based operations use `HOP`. Alignment confirmed.

**`librosa.beat.beat_track()` absence check:** The broken function appears only in comments (lines 4, 37). No executable calls found. The workaround (`beat_track_grid` via `onset_strength` + `beat.tempo` + grid) is fully implemented.

---

## Requirements Coverage

| Requirement | Status | Notes |
|-------------|--------|-------|
| AUDIO-01: Detect major, minor, and 7th chords via chroma extraction | SATISFIED | 36-template cosine similarity produces :maj/:min/:7 labels. Vocabulary enforced by construction. |
| AUDIO-02: Chord changes snapped to musical beat positions | SATISFIED | One chord label per beat by pipeline design. `beat_track_grid()` + `extract_beat_chroma()` + `detect_chords()` chain ensures beat-level granularity. |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No TODO, FIXME, placeholder, empty returns, or console.log-only stubs found in any phase 3 file. |

---

## Human Verification Required

### 1. Numeric Accuracy Validation

**Test:** Run `detect_chords_pipeline()` on Wild Horses.mp3 (or any song with a known chord sheet), then call `measure_accuracy(result['chord_sequence'], reference_chords)` where `reference_chords` is a beat-aligned list of the correct chord at each beat.

**Expected:** `root_accuracy >= 0.60` in the returned dict.

**Why human:** No numeric figure was ever logged. The 03-03 SUMMARY states "Root detection accuracy: HIGH" and "all 5 expected roots present" but never calls `measure_accuracy()` with actual pipeline output to produce a percentage. A human must run the pipeline on audio and compare to a chord sheet.

**Command to run:**
```python
import sys; sys.path.insert(0, 'backend')
from audio.loader import load_audio
from audio.chord_detection import detect_chords_pipeline, measure_accuracy

audio = load_audio("Wild Horses.mp3")
result = detect_chords_pipeline(audio)

# Manually construct a reference list matching the detected beat count
# Reference: G, Am7, Bm, C, D for Wild Horses (simplify to G:maj, A:min, B:min, C:maj, D:maj)
# Each chord held for approximate number of beats based on timestamps
# Then call:
ref = [...]  # beat-aligned reference list
acc = measure_accuracy(result['chord_sequence'], ref)
print(f"Exact accuracy: {acc['exact_accuracy']:.1%}")
print(f"Root accuracy: {acc['root_accuracy']:.1%}")
```

---

## Gaps Summary

**One gap blocking full goal achievement:**

**Success Criterion 5 — Accuracy on 5 known test songs >= 60%** was not met at the required standard.

The pipeline's accuracy measurement utility (`measure_accuracy()`) exists and works correctly. The human checkpoint in Plan 03-03 confirmed that the pipeline produces musically reasonable output on two songs. However:

1. Only 2 songs were evaluated (Don't Cave.mp3 and Wild Horses.mp3), not the required 5.
2. No numeric accuracy percentage was computed. "All 5 expected roots present" confirms root recall but not a beat-level accuracy rate (e.g., if a 4-minute song has 436 beats and roots are correct for 300 of them, that is 68% root accuracy — but this was never calculated).
3. The 03-03 PLAN explicitly required `measure_accuracy()` to be called against a reference list. The SUMMARY shows the function was created and tested on synthetic data but not applied to real audio with a reference.

**Root cause:** Plan 03-03 Task 2 was a human checkpoint that required running the pipeline and reviewing output. The human approved qualitatively ("all expected roots present") but the verification step of computing a numeric percentage with `measure_accuracy()` was skipped.

**What is NOT a gap:** All 4 structural success criteria (beat count plausibility, beat-synchronized labels, chord collapse, vocabulary restriction) are fully implemented and verified in code. The accuracy measurement infrastructure is complete and correct.

---

## Overall Assessment

The Phase 3 pipeline is structurally complete and correct. The core engineering goal — "beat-synchronized, template-matched chord labels that are musically readable, not frame-level noise" — is achieved:

- Beat tracking via onset_strength + grid produces plausible counts
- Chroma synced to beats via librosa.util.sync
- 36-template cosine similarity with Viterbi smoothing produces stable chord sequences
- Collapse eliminates adjacent duplicate labels
- Vocabulary strictly limited to :maj/:min/:7

The single gap is the **accuracy validation criterion**: 5 songs with numeric >= 60% accuracy. This is a validation and documentation gap, not an implementation gap. The pipeline is capable of producing measurable accuracy — the measurement was never formalized and logged for 5 songs.

---

_Verified: 2026-03-04_
_Verifier: Claude (gsd-verifier)_
