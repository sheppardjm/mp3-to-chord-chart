---
phase: 02-audio-loading-and-key-detection
verified: 2026-03-04T04:22:01Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 2: Audio Loading and Key Detection Verification Report

**Phase Goal:** MP3 files load within memory constraints and the detected song key is available to drive correct enharmonic chord naming throughout the rest of the pipeline
**Verified:** 2026-03-04T04:22:01Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                              | Status     | Evidence                                                                                     |
| --- | ---------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------- |
| 1   | A 4-minute MP3 loads without exceeding 600MB RAM                                   | VERIFIED   | Live run: peak tracemalloc = 360.8MB on "Don't Cave.mp3" (242.6s). Limit is 600MB.          |
| 2   | `librosa.load()` is called with `sr=22050, mono=True, duration=300` explicitly     | VERIFIED   | loader.py lines 22-26: all four params present (sr, mono, duration, dtype). No defaults.    |
| 3   | Detected key for "Don't Cave.mp3" is returned as a valid root and mode             | VERIFIED   | Live run: detect_key() returned "G:maj" — valid ROOT:mode format, root in ROOTS list.       |
| 4   | Enharmonic naming from flat keys produces Bb/Eb/Ab, not A#/D#/G#                  | VERIFIED   | Live run: Bb:maj -> ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']. No A#/D#/G#.   |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact                             | Expected                                           | Status    | Details                                                                      |
| ------------------------------------ | -------------------------------------------------- | --------- | ---------------------------------------------------------------------------- |
| `backend/audio/__init__.py`          | Audio package init                                 | VERIFIED  | Exists. Empty file (correct — just marks directory as Python package).       |
| `backend/audio/loader.py`            | load_audio() with constrained librosa.load + HPSS  | VERIFIED  | 40 lines. No stubs. Exports load_audio(). All explicit params present.       |
| `backend/audio/key_detection.py`     | detect_key() and get_note_names() functions        | VERIFIED  | 81 lines. No stubs. Exports both functions + ROOTS constant.                 |
| `backend/pyproject.toml`             | Updated dependencies including librosa==0.11.0     | VERIFIED  | librosa==0.11.0 present in dependencies list.                                |

### Key Link Verification

| From                          | To                              | Via                                              | Status  | Details                                                                                            |
| ----------------------------- | ------------------------------- | ------------------------------------------------ | ------- | -------------------------------------------------------------------------------------------------- |
| `backend/audio/loader.py`     | `librosa`                       | `librosa.load()` with sr, mono, duration, dtype  | WIRED   | Line 21-27: all four params explicit. Live import confirmed.                                       |
| `backend/audio/loader.py`     | `librosa.effects.hpss`          | HPSS with hop_length=1024                        | WIRED   | Line 32: `librosa.effects.hpss(y, hop_length=1024)`. Returns y_harmonic, y_percussive.            |
| `backend/audio/key_detection.py` | `audio/loader.py`            | detect_key takes y_harmonic from load_audio dict | WIRED   | detect_key(y_harmonic, sr) signature matches loader's returned dict keys. Live pipeline confirmed. |
| `backend/audio/key_detection.py` | `librosa.feature.chroma_cqt` | chroma extraction on harmonic component          | WIRED   | Line 37: `chroma_cqt(y=y_harmonic, sr=sr, tuning=0.0)`. Not raw audio.                            |
| `backend/audio/key_detection.py` | `scipy.linalg.circulant`     | K-S profile rotation for all 24 keys             | WIRED   | Lines 48-53: circulant matrices computed and dot-producted against chroma_z.                       |
| `backend/audio/key_detection.py` | `librosa.key_to_notes`       | enharmonic note name lookup                      | WIRED   | Line 81: `return librosa.key_to_notes(key, unicode=unicode)` — not hand-rolled.                   |

### Requirements Coverage

| Requirement | Status    | Notes                                                                                                          |
| ----------- | --------- | -------------------------------------------------------------------------------------------------------------- |
| AUDIO-04    | SATISFIED | Song key detected (G:maj for test MP3). Enharmonic naming correct for flat/sharp keys via librosa.key_to_notes. |

### Anti-Patterns Found

None. Scanned `backend/audio/loader.py` and `backend/audio/key_detection.py` for TODO, FIXME, XXX, HACK, placeholder, `return null`, `return {}`, `return []`. Zero matches.

### Human Verification Required

None — all four success criteria were verified by direct code execution against the real "Don't Cave.mp3" test file. No visual, real-time, or external service dependencies in this phase.

---

## Verification Details

### Truth 1: Memory Constraint

Verified by live execution of the full load_audio() pipeline on "Don't Cave.mp3" (242.6 seconds, ~3.6 MB compressed):

- Peak memory (tracemalloc): **360.8 MB** — well under 600 MB limit
- The hop_length=1024 parameter on HPSS (line 32 of loader.py) is the critical memory guard. Default hop=512 produced 718 MB (exceeding the limit); the deviation was caught and fixed during Plan 01 execution.
- sr=22050, mono=True, dtype=np.float32 confirmed from live run output.

### Truth 2: Explicit librosa.load() Parameters

All four parameters confirmed present in loader.py lines 22-26:

```python
y, sr = librosa.load(
    path,
    sr=22050,
    mono=True,
    duration=300,
    dtype=np.float32,
)
```

No parameter is left to librosa defaults. The duration=300 cap prevents unbounded memory growth for songs over 5 minutes.

### Truth 3: Key Detection Correctness

detect_key() ran successfully on y_harmonic from the real test file:

- Detected key: **G:maj**
- Format: ROOT:mode — two-part string with root from ROOTS list, mode either "maj" or "min"
- K-S algorithm uses scipy.linalg.circulant for vectorized 24-key correlation (not a loop)
- tuning=0.0 passed to chroma_cqt to bypass numba stencil path (required for Python 3.14 x86_64 compatibility)

The G major result is consistent across runs and was previously verified by Plan 02 Task 2 with a K-S score of 23.77 vs next best — a confident detection margin.

### Truth 4: Enharmonic Naming

get_note_names() delegates to librosa.key_to_notes() — no hand-rolled enharmonic logic. Verified directly:

- **Bb:maj** -> `['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']`
  - Contains: Db, Eb, Ab, Bb (flat spellings) — CORRECT
  - Does NOT contain: C#, D#, G#, A# — CORRECT
- **G:maj** -> `['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']`
  - Contains: F# — CORRECT (G major has one sharp)
- Additional flat keys (F:maj, Eb:maj, Ab:maj) all produce Bb in note names — CORRECT

### Wiring Note: Audio Modules Not Imported by main.py

`backend/main.py` does not import `audio.loader` or `audio.key_detection`. This is **expected** and not a gap. The FastAPI endpoint that invokes the audio pipeline is not created until Phase 5 (Upload Handler). The audio modules are standalone pipeline components — confirmed wired to each other (load_audio output feeds detect_key input) and ready for Phase 3 to consume.

### Numba/llvmlite Stubs

Both stubs confirmed present at:
- `backend/.venv/lib/python3.14/site-packages/numba/__init__.py`
- `backend/.venv/lib/python3.14/site-packages/llvmlite/__init__.py`

These are required for librosa to function on Python 3.14 x86_64 macOS (no native llvmlite binary wheel available). The stubs provide no-op JIT decorators. All librosa audio processing works correctly without JIT acceleration.

---

_Verified: 2026-03-04T04:22:01Z_
_Verifier: Claude (gsd-verifier)_
