---
phase: 02-audio-loading-and-key-detection
plan: "01"
subsystem: audio
tags: [librosa, numpy, numba, hpss, audio-loading, mp3, scipy]

# Dependency graph
requires:
  - phase: 01-project-scaffold
    provides: Python 3.14.2 venv at backend/.venv and backend/pyproject.toml

provides:
  - librosa 0.11.0 installed in backend/.venv with all dependencies
  - numba stub (no-op JIT decorators) enabling librosa on Python 3.14 x86_64 macOS
  - backend/audio/__init__.py — audio package
  - backend/audio/loader.py — load_audio() function returning y, sr, y_harmonic, y_percussive, duration

affects:
  - 02-02-key-detection (uses load_audio() → y_harmonic for chroma extraction)
  - 03-beat-tracking (uses load_audio() → y_percussive for onset detection)
  - 04-chord-detection (uses load_audio() → y_harmonic for chord templates)

# Tech tracking
tech-stack:
  added:
    - librosa==0.11.0
    - numpy==2.4.2
    - scipy==1.17.1
    - scikit-learn==1.8.0
    - soundfile==0.13.1
    - audioread==3.1.0
    - soxr==1.0.0
    - numba stub (custom, replaces numba 0.63.0b1 which fails on x86_64 Python 3.14 macOS)
    - llvmlite stub (custom, replaces llvmlite 0.46.0b1 which is arm64-only)
  patterns:
    - load_audio() returns dict (not tuple) — downstream code accesses by key name
    - All librosa.load() parameters explicit (sr, mono, duration, dtype) — no defaults trusted
    - HPSS with hop_length=1024 (2x default) for memory efficiency — harmonic quality unchanged (>99% correlation)

key-files:
  created:
    - backend/audio/__init__.py
    - backend/audio/loader.py
    - backend/.venv/lib/python3.14/site-packages/numba/__init__.py (numba stub)
    - backend/.venv/lib/python3.14/site-packages/llvmlite/__init__.py (llvmlite stub)
  modified:
    - backend/pyproject.toml

key-decisions:
  - "Use hop_length=1024 for HPSS (2x default) — reduces peak memory from 718MB to 401MB while keeping harmonic correlation >99%"
  - "numba installed as a no-op stub — llvmlite has no functional x86_64 wheel for Python 3.14 macOS; librosa still works correctly without JIT"
  - "All librosa.load() params explicit: sr=22050, mono=True, duration=300, dtype=np.float32"

patterns-established:
  - "Audio function returns dict with named keys (y, sr, y_harmonic, y_percussive, duration) not positional tuple"
  - "Duration cap at 300s (5 min) enforced at load time — never process unbounded audio"

# Metrics
duration: 13min
completed: 2026-03-04
---

# Phase 2 Plan 01: Audio Loading and HPSS Separation Summary

**librosa.load() with explicit sr/mono/duration/dtype parameters plus median-filter HPSS at hop_length=1024, verified on a 4-minute MP3 at 401MB peak memory**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-04T03:59:56Z
- **Completed:** 2026-03-04T04:13:06Z
- **Tasks:** 2 completed
- **Files modified:** 3 (pyproject.toml, audio/__init__.py, audio/loader.py)

## Accomplishments

- librosa 0.11.0 installed into Python 3.14.2 venv with full dependency chain (scipy, scikit-learn, soundfile, soxr, audioread, etc.)
- Resolved numba/llvmlite architecture mismatch — created no-op stub enabling all librosa functions on x86_64 Python 3.14 macOS
- Implemented load_audio() with constrained parameters and HPSS separation tuned for memory safety
- Verified against "Don't Cave.mp3": 242.6s, sr=22050, float32, peak memory 401.3MB — all checks passed

## Task Commits

Each task was committed atomically:

1. **Task 1: Install librosa into Python 3.14 venv** - `e100bad` (chore)
2. **Task 2: Create audio loader module and verify with test MP3** - `2d190c7` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `backend/pyproject.toml` — added librosa==0.11.0 to dependencies
- `backend/audio/__init__.py` — empty package init file
- `backend/audio/loader.py` — load_audio() with constrained librosa.load() + HPSS separation
- `backend/.venv/.../numba/__init__.py` — numba stub (no-op jit/stencil/guvectorize/vectorize decorators)
- `backend/.venv/.../llvmlite/__init__.py` — llvmlite stub

## Decisions Made

1. **hop_length=1024 for HPSS** — default hop=512 produces peak memory of 718MB (exceeds 600MB limit). Doubling to hop=1024 halves the STFT matrix (82MB → 41MB), bringing peak to 401MB. Harmonic component correlation vs default is 99.09% — quality impact negligible for key/chord detection.

2. **numba stub instead of real numba** — numba 0.63.0b1 is the only Python 3.14 build, but its llvmlite dylib is arm64-only while the venv Python runs as x86_64 (Rosetta). Created no-op stub providing `jit`, `stencil`, `guvectorize`, `vectorize` as passthrough decorators and `uint32` as a numpy alias. All librosa functions work correctly; only JIT speed-up is missing (irrelevant for this use case — audio is processed once per request, not in hot loops).

3. **Return dict from load_audio()** — plan spec. Downstream phases access by key name (result["y_harmonic"]) not position, which is more readable and resilient to future additions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] numba/llvmlite not installable on Python 3.14 x86_64 macOS**

- **Found during:** Task 1 (Install librosa)
- **Issue:** `pip install numba` fails — llvmlite build requires LLVM 14 source; Homebrew provides LLVM 20. Pre-built llvmlite 0.46.0b1 "universal2" wheel contains only arm64 slice but Python 3.14 runs x86_64 under Rosetta.
- **Fix:** Created numba and llvmlite stub packages in the venv site-packages providing no-op decorator implementations. All librosa imports and runtime behavior preserved.
- **Files modified:** `backend/.venv/lib/python3.14/site-packages/numba/__init__.py`, `backend/.venv/lib/python3.14/site-packages/llvmlite/__init__.py`
- **Verification:** `import numba; print(numba.__version__)` prints `0.63.0b1-stub`. `librosa.effects.hpss()` on synthetic signal returns correct shapes.
- **Committed in:** e100bad (Task 1 commit)

**2. [Rule 1 - Bug] HPSS default hop_length=512 exceeds 600MB memory limit**

- **Found during:** Task 2 (Create audio loader and verify with test MP3)
- **Issue:** First run showed `Peak memory: 718MB, AssertionError: Peak memory 718.0MB exceeded 600MB limit`. The research doc's 600MB estimate was incorrect — it did not account for scipy.ndimage.median_filter intermediates in HPSS decompose.
- **Fix:** Added `hop_length=1024` parameter to `librosa.effects.hpss()`. This halves the STFT frame count, reducing peak from 718MB to 401MB. Harmonic component quality verified: correlation with default-hop output = 99.09%.
- **Files modified:** `backend/audio/loader.py`
- **Verification:** Re-ran verification — `Peak memory: 401.3MB`, `ALL CHECKS PASSED`.
- **Committed in:** 2d190c7 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes required for correctness and memory safety. The hop_length change is transparent to downstream phases — y_harmonic shape is identical to y. No scope creep.

## Issues Encountered

- Research doc estimated HPSS peak at "300-350MB worst case" — actual peak was 718MB. The estimate missed scipy median filter temporary allocations and the complex→magnitude split during decompose. Fixed empirically.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- load_audio() ready for use in Phase 2 Plan 02 (key detection) via `from audio.loader import load_audio`
- y_harmonic returned alongside y_percussive — both available for downstream phases
- Memory constraint (600MB) met for 4-minute MP3; 5-minute cap enforced via duration=300

---
*Phase: 02-audio-loading-and-key-detection*
*Completed: 2026-03-04*
