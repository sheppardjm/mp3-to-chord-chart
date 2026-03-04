# Phase 2: Audio Loading and Key Detection - Research

**Researched:** 2026-03-03
**Domain:** librosa audio loading, Krumhansl-Schmuckler key detection, enharmonic naming
**Confidence:** MEDIUM-HIGH (librosa API verified via official docs; Python 3.14 compatibility is MEDIUM — numba 0.64.0 with Python 3.14 wheels exists as of Feb 2026, but librosa 0.11.0's `setup.cfg` lists classifiers only through Python 3.13 and has no upper bound in `python_requires`)

---

## Summary

Phase 2 installs librosa into the Python 3.14.2 venv and implements two distinct capabilities: (1) a constrained audio loader that calls `librosa.load()` with explicit `sr=22050, mono=True, duration=300` to cap memory usage, and (2) a key detection stage that uses chroma features and the Krumhansl-Schmuckler algorithm to produce an enharmonic-aware note name list via `librosa.key_to_notes()`.

**Python 3.14 compatibility is the most important risk.** Librosa 0.11.0 is the current release (March 11, 2025). Its `setup.cfg` lists `python_requires = >=3.8` with no upper bound but classifiers only through 3.13. Numba 0.64.0 (February 18, 2026) now ships Python 3.14 wheels (`cp314`), which removes the major historical blocker. `audioread` on Python 3.13+ requires `standard-aifc` and `standard-sunau` shims; librosa's `setup.cfg` lists these as conditional dependencies for Python 3.13+, so `pip install librosa` should handle them automatically. The install should succeed on Python 3.14 but must be verified in the actual venv — if it fails, the `--no-deps` + manual dep install workaround is the escape hatch.

Key detection uses librosa's `chroma_cqt` on the harmonic component (after HPSS separation) summed to a single 12-element pitch-class vector, correlated against Krumhansl-Schmuckler profiles. The detected key string (e.g. `"Bb:maj"`) is passed to `librosa.key_to_notes()` which returns the canonical 12-note spelling for that key — flat keys produce `Bb/Eb/Ab`, not `A#/D#/G#`. This note list is stored and reused by Phase 3 (chord naming) and Phase 6 (chart builder).

**Primary recommendation:** `pip install librosa` in the Phase 1 venv; verify with `python -c "import librosa; print(librosa.__version__)"`. If blocked, manually install `numba==0.64.0` first. Implement key detection as `detect_key(y_harmonic, sr) -> str` returning `"ROOT:mode"` format, backed by Krumhansl-Schmuckler correlation over the mean chroma vector from `chroma_cqt`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| librosa | 0.11.0 | Audio loading, HPSS, chroma extraction, enharmonic naming | The canonical Python audio/music analysis library; nothing else provides the full pipeline in one package |
| numba | 0.64.0 | JIT compilation used internally by librosa | Required by librosa; 0.64.0 is the first release with Python 3.14 wheels |
| numpy | >=1.22.3 | Array backend for audio data | librosa dependency; already present |
| scipy | >=1.6.0 | Signal processing (resampling, FFT) | librosa dependency; provides `scipy.stats.zscore` for K-S correlation |
| soundfile | >=0.12.1 | Primary MP3/WAV decoder (libsndfile backend) | librosa uses this first before falling back to audioread |
| audioread | >=2.1.9 | Fallback MP3 decoder (uses ffmpeg) | librosa falls back to this when soundfile cannot decode |
| standard-aifc | any | Shim for removed Python 3.13+ stdlib module | librosa conditional dependency for 3.13+; required for audioread compat |
| standard-sunau | any | Shim for removed Python 3.13+ stdlib module | librosa conditional dependency for 3.13+; required for audioread compat |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tracemalloc | (stdlib) | Peak memory sampling during load | Verify 4-min MP3 stays under 600MB RAM limit |
| psutil | >=5.x | Process-level RSS memory measurement | Alternative to tracemalloc for wall-clock peak measurement |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Krumhansl-Schmuckler (manual impl) | `keyedin` library | `keyedin` wraps K-S but adds another dependency; hand-rolling K-S is 30 lines and has no hidden state |
| `chroma_cqt` on harmonic | `chroma_stft` on raw signal | CQT bins align with musical pitch intervals; STFT can bleed percussive energy into chroma — HPSS + CQT is the documented best practice |
| `librosa.effects.hpss()` | `librosa.effects.harmonic()` | `harmonic()` is a shortcut that does the same HPSS internally; either works. `hpss()` returns both components which is useful if Phase 3 needs percussive for beat tracking |

### Installation

```bash
# From project root, activate the Phase 1 venv
source backend/.venv/bin/activate

# Install librosa (pulls in numba 0.64.0, numpy, scipy, soundfile, etc.)
pip install librosa==0.11.0

# Verify Python 3.14 install succeeded
python -c "import librosa; print(librosa.__version__)"

# If numba blocks install, install it first:
pip install numba==0.64.0
pip install librosa==0.11.0
```

**MP3 decoding backend note:** On macOS, `soundfile` (libsndfile) now supports MP3 directly as of libsndfile 1.1.0+ (bundled in the soundfile wheel). If soundfile fails for a specific MP3, librosa automatically falls back to `audioread` which uses ffmpeg. Ensure ffmpeg is installed on the dev machine (`brew install ffmpeg`) as the fallback.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── audio/
│   ├── __init__.py
│   ├── loader.py        # load_audio() -> (y, sr, y_harmonic)
│   └── key_detection.py # detect_key(y_harmonic, sr) -> str, get_note_names(key) -> list[str]
├── main.py              # FastAPI app
└── pyproject.toml
```

The `audio/` package is built in Phase 2 and consumed by Phase 3 (beat tracking uses `y` from `loader.py`; chord naming uses note names from `key_detection.py`). Design these as pure functions — no global state — so they can be called from the FastAPI threadpool executor added in Phase 5.

### Pattern 1: Constrained Audio Loader

**What:** Call `librosa.load()` with explicit, non-default parameters so memory and duration are bounded.
**When to use:** Every audio load in the system — never call `librosa.load(path)` with defaults.

```python
# Source: https://librosa.org/doc/main/generated/librosa.load.html
import librosa
import numpy as np

def load_audio(path: str) -> tuple[np.ndarray, int, np.ndarray]:
    """
    Load MP3 with constrained parameters.
    Returns: (y, sr, y_harmonic)
      - y: full audio signal, mono, float32
      - sr: sample rate (always 22050)
      - y_harmonic: harmonic component for chroma/key detection
    """
    y, sr = librosa.load(
        path,
        sr=22050,       # explicit: never use native rate
        mono=True,      # explicit: always collapse to mono
        duration=300,   # cap at 5 minutes (300s)
        dtype=np.float32,  # explicit: 4 bytes/sample
    )
    # Separate harmonic/percussive for cleaner chroma
    y_harmonic, _ = librosa.effects.hpss(y)
    return y, sr, y_harmonic
```

**Memory math:** 300s × 22050 samples/s × 4 bytes = ~26 MB for `y`. HPSS creates `y_harmonic` of the same size (~26 MB). Peak during HPSS includes the STFT spectrogram: for hop_length=512 and n_fft=2048, the STFT matrix is ~(1025, ~12,900) × 8 bytes (complex64) ≈ ~105 MB. Total peak: well under 600MB. A 4-minute song (240s) is even lower.

### Pattern 2: Krumhansl-Schmuckler Key Detection

**What:** Sum chroma features across time to get a 12-element pitch-class energy vector, then correlate against K-S major/minor profiles to find the best-matching key.
**When to use:** Once per song, using `y_harmonic` (not raw `y`).

```python
# Source: Brian McFee's reference implementation https://gist.github.com/bmcfee/1f66825cef2eb34c839b42dddbad49fd
# and librosa.feature.chroma_cqt docs https://librosa.org/doc/main/generated/librosa.feature.chroma_cqt.html
import librosa
import numpy as np
import scipy.linalg
from scipy.stats import zscore

# Krumhansl-Schmuckler key profiles (psychoacoustic experiment data)
KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

# Chromatic root names (C=0 through B=11) — used to build key string
ROOTS = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

def detect_key(y_harmonic: np.ndarray, sr: int = 22050) -> str:
    """
    Returns key as "ROOT:mode" string, e.g. "Bb:maj" or "G:min".
    Uses chroma_cqt on harmonic component + Krumhansl-Schmuckler correlation.
    """
    # Extract chromagram from harmonic signal
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr)
    # Sum across time -> 12-element pitch-class energy vector
    chroma_mean = chroma.mean(axis=1)

    # Normalize profiles
    major_z = zscore(KS_MAJOR)
    minor_z = zscore(KS_MINOR)
    chroma_z = zscore(chroma_mean)

    # Build circulant matrices (all 12 rotations of each profile)
    major_circulant = scipy.linalg.circulant(major_z)
    minor_circulant = scipy.linalg.circulant(minor_z)

    # Correlation scores for all 24 keys
    major_scores = major_circulant.T.dot(chroma_z)
    minor_scores = minor_circulant.T.dot(chroma_z)

    # Find best key
    best_major_idx = np.argmax(major_scores)
    best_minor_idx = np.argmax(minor_scores)

    if major_scores[best_major_idx] >= minor_scores[best_minor_idx]:
        return f"{ROOTS[best_major_idx]}:maj"
    else:
        return f"{ROOTS[best_minor_idx]}:min"


def get_note_names(key: str, unicode: bool = False) -> list[str]:
    """
    Returns 12-element list of note names spelled correctly for the key.
    E.g. "Bb:maj" -> ['C', 'Db', 'D', 'Eb', 'E', 'F', 'G', 'Ab', 'A', 'Bb', 'B']
    unicode=False uses ASCII (b/# not ♭/♯) for downstream string processing.
    """
    # Source: https://librosa.org/doc/latest/generated/librosa.key_to_notes.html
    return librosa.key_to_notes(key, unicode=unicode)
```

**Enharmonic guarantee:** `librosa.key_to_notes()` applies the rule: "If the tonic has an accidental, that accidental is used consistently for all notes." So `Bb:maj` produces all-flat spellings; `F#:maj` produces all-sharp spellings. The implementation in `librosa/core/notation.py` uses `tonic_number` on the circle of fifths to decide flat vs sharp when the tonic is natural. This matches standard music theory conventions.

### Pattern 3: Key-Aware Enharmonic Naming Table

**What:** After `detect_key()`, store the 12-note list and use it as a lookup table throughout Phase 3 for chord root naming.
**When to use:** At the top of the audio processing pipeline; pass note names into chord detection functions.

```python
# Downstream usage in Phase 3
note_names = get_note_names(key)  # e.g. ['C', 'Db', 'D', 'Eb', ...]
# To name a chord root at semitone index 3 (Eb in Bb major):
chord_root = note_names[3]  # -> "Eb", not "D#"
```

### Anti-Patterns to Avoid

- **Calling `librosa.load(path)` with defaults:** Default `sr=22050` is fine but `duration=None` and `mono=True` default are version-dependent. Always pass all four parameters explicitly.
- **Running chroma on raw `y` without HPSS:** Percussion contributes broadband energy across all chroma bins, degrading key detection. Always use `y_harmonic` for chroma.
- **Using `chroma_mean` from stereo:** `librosa.load(..., mono=True)` ensures mono input. If ever loading stereo, collapse to mono before chroma extraction.
- **Passing `key` strings with wrong format to `key_to_notes`:** The format is strictly `TONIC:mode` where tonic is uppercase and mode is lowercase (e.g. `"Bb:maj"`, not `"Bb major"` or `"bb:MAJ"`). Invalid format raises `ParameterError`.
- **Assuming `librosa.key_to_notes` has built-in key detection:** It does not. `key_to_notes` is a spelling helper — you must detect the key yourself (K-S algorithm) and then pass the result.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Enharmonic note spelling | Custom flat/sharp lookup table | `librosa.key_to_notes(key)` | librosa implements the full circle-of-fifths tiebreaking logic including double accidentals; a naive table will miss edge cases like Gb vs F# and Cb vs B |
| HPSS separation | Manual median filtering | `librosa.effects.hpss(y)` | HPSS is a well-tuned spectrogram median filter; hand-rolling median filtering misses the margin parameter that controls bleed |
| K-S circulant correlation | Loop over 24 keys manually | `scipy.linalg.circulant` + matrix multiply | Circulant matrix vectorizes all 24 rotations in one operation; loop version is correct but 24x slower |
| Audio resampling | `scipy.signal.resample` | `librosa.load(..., sr=22050)` | librosa uses soxr (Sox Resampler) by default which is higher quality than scipy's FFT resampler for audio |
| MP3 decoding | `subprocess + ffmpeg` | `librosa.load()` | librosa orchestrates soundfile -> audioread -> ffmpeg fallback chain automatically |

**Key insight:** The enharmonic naming problem is deceptively hard. `Bb` and `A#` are acoustically identical but musically distinct. Getting it right requires tracking the song's key and deriving all note names from it — `librosa.key_to_notes()` does exactly this correctly.

---

## Common Pitfalls

### Pitfall 1: librosa install fails on Python 3.14

**What goes wrong:** `pip install librosa` errors with "Cannot install on Python version 3.14.x; only versions >=3.8,<3.14 are supported" — either from librosa's own metadata or from a transitive dependency.

**Why it happens:** librosa 0.11.0's `setup.cfg` classifiers list only through Python 3.13, and historically numba (which librosa requires) has blocked new Python versions. numba 0.64.0 adds Python 3.14 wheels but if pip resolves an older numba version, the block resurfaces.

**How to avoid:** Pin numba explicitly before installing librosa:
```bash
pip install "numba>=0.64.0"
pip install librosa==0.11.0
```
If librosa's own `python_requires` blocks 3.14, use `--ignore-requires-python` (acceptable for personal tool):
```bash
pip install librosa==0.11.0 --ignore-requires-python
```

**Warning signs:** Install error mentioning Python version constraint, or `ImportError: cannot import name 'NumbaPendingDeprecationWarning'` after install.

### Pitfall 2: audioread fails for MP3 on Python 3.14 due to missing aifc/sunau

**What goes wrong:** `librosa.load("song.mp3")` raises `audioread.DecodeError` or `ModuleNotFoundError: No module named 'aifc'`.

**Why it happens:** Python 3.13+ removed `aifc` and `sunau` from the stdlib. `audioread` uses them as part of its backend detection. librosa 0.11.0 conditionally installs `standard-aifc` and `standard-sunau` shims for Python 3.13+.

**How to avoid:** Let `pip install librosa` handle it (the conditional deps are in `setup.cfg`). If they're missing after install:
```bash
pip install standard-aifc standard-sunau
```

**Warning signs:** `ModuleNotFoundError: No module named 'aifc'` during `librosa.load()` of an MP3 file.

### Pitfall 3: Key detection returns wrong root for ambiguous keys

**What goes wrong:** A song in G major is detected as E minor (the relative minor), or a song in F# is detected as Gb.

**Why it happens:** The K-S algorithm works on pitch-class energy distributions. Relative major/minor keys share the same pitch classes, so the distinction requires the algorithm to correctly identify tonal center, not just pitch class salience. Ambiguous or chord-sparse songs may score nearly equally for relative keys.

**How to avoid:** Use `y_harmonic` (not raw `y`) for chroma extraction — removes percussive noise. Accept that key detection is probabilistic; validate against 3-5 known test songs during Phase 2 to establish a baseline. Consider logging both `major_scores[best_major_idx]` and `minor_scores[best_minor_idx]` so confidence can be assessed.

**Warning signs:** Detected key consistently produces wrong enharmonic naming for chord tones (e.g., all chords have # instead of b names in a flatkey song).

### Pitfall 4: Memory spike during HPSS on long audio

**What goes wrong:** HPSS on a 5-minute mono audio array temporarily allocates much more than the 26MB audio array suggests, due to the STFT spectrogram being held in memory during processing.

**Why it happens:** `librosa.effects.hpss()` internally computes a full STFT, applies median filtering, then ISTFT. The STFT matrix for 300s at sr=22050, hop_length=512, n_fft=2048 is approximately (1025 bins × 12,890 frames) × 8 bytes complex64 = ~106 MB. Plus two copies during median filtering.

**How to avoid:** The 600MB limit is safe — HPSS peak is ~300-350MB worst case for 5 minutes. Enforce `duration=300` in `librosa.load()` to cap at 5 minutes. Do not run HPSS on audio longer than 10 minutes.

**Warning signs:** MemoryError or kernel OOM kill on very long audio files; RSS growing past 500MB during load.

### Pitfall 5: `key_to_notes` format errors

**What goes wrong:** `librosa.key_to_notes("Bb major")` raises `librosa.util.exceptions.ParameterError`.

**Why it happens:** The key format is strictly `TONIC:mode` — colon separator, uppercase tonic, lowercase mode. Common wrong formats: `"Bb major"`, `"bb:maj"`, `"Bb Major"`, `"BbM"`.

**How to avoid:** Always construct the key string in the format returned by `detect_key()` — e.g. `"Bb:maj"` or `"G:min"`.

**Warning signs:** `ParameterError: key` exception from librosa.

---

## Code Examples

### Full Audio Load + Key Detection Pipeline

```python
# Source: librosa.load docs (https://librosa.org/doc/main/generated/librosa.load.html)
# and key_to_notes docs (https://librosa.org/doc/latest/generated/librosa.key_to_notes.html)
import librosa
import numpy as np
import scipy.linalg
from scipy.stats import zscore

KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
ROOTS    = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

def process_audio(path: str) -> dict:
    """Full pipeline: load -> HPSS -> key detection -> note names."""
    # 1. Load with explicit constraints
    y, sr = librosa.load(path, sr=22050, mono=True, duration=300, dtype=np.float32)

    # 2. Separate harmonic/percussive
    y_harmonic, y_percussive = librosa.effects.hpss(y)

    # 3. Chroma from harmonic only
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr)
    chroma_mean = chroma.mean(axis=1)

    # 4. Krumhansl-Schmuckler correlation
    chroma_z   = zscore(chroma_mean)
    major_z    = zscore(KS_MAJOR)
    minor_z    = zscore(KS_MINOR)
    maj_scores = scipy.linalg.circulant(major_z).T.dot(chroma_z)
    min_scores = scipy.linalg.circulant(minor_z).T.dot(chroma_z)

    best_maj = int(np.argmax(maj_scores))
    best_min = int(np.argmax(min_scores))
    if maj_scores[best_maj] >= min_scores[best_min]:
        key = f"{ROOTS[best_maj]}:maj"
    else:
        key = f"{ROOTS[best_min]}:min"

    # 5. Canonical note names for enharmonic naming
    note_names = librosa.key_to_notes(key, unicode=False)  # ASCII b/# for downstream

    return {
        "key": key,
        "note_names": note_names,
        "y": y,
        "y_harmonic": y_harmonic,
        "y_percussive": y_percussive,
        "sr": sr,
    }
```

### Memory Measurement Pattern

```python
# Source: Python stdlib tracemalloc docs
import tracemalloc
import librosa
import numpy as np

def load_audio_with_memory_check(path: str) -> tuple:
    tracemalloc.start()
    y, sr = librosa.load(path, sr=22050, mono=True, duration=300, dtype=np.float32)
    y_harmonic, _ = librosa.effects.hpss(y)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / 1024 / 1024
    assert peak_mb < 600, f"Peak memory {peak_mb:.1f}MB exceeded 600MB limit"
    return y, sr, y_harmonic
```

### Enharmonic Verification Test

```python
# Flat-key test: Bb major -> all flat names
note_names = librosa.key_to_notes("Bb:maj", unicode=False)
assert note_names[1]  == "Db"  # not C#
assert note_names[3]  == "Eb"  # not D#
assert note_names[8]  == "Ab"  # not G#
assert note_names[10] == "Bb"  # not A#

# Sharp-key test: G major -> natural/sharp names
note_names = librosa.key_to_notes("G:maj", unicode=False)
assert note_names[6]  == "F#"  # not Gb
assert note_names[1]  == "C#"  # not Db (G major has F# but no other sharps... actually C# doesn't appear in G major)
# Correct: G major has F# only; C is natural
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `audioread` as primary MP3 decoder | `soundfile` (libsndfile 1.1.0+) as primary | ~2022 | soundfile is faster and has no Python version issues; audioread is now fallback |
| `librosa.core.load()` (old API path) | `librosa.load()` (direct import) | librosa 0.8+ | `librosa.core.load` still works but `librosa.load` is canonical |
| K-S raw dot product | K-S normalized correlation (vector norms) | N/A (community improvement) | Normalized version keeps scores in [-1, 1] range, easier to threshold confidence |
| `chroma_stft` for key detection | `chroma_cqt` on harmonic component | Best practice evolved ~2018-2020 | CQT bins are pitch-aligned; HPSS removes percussive noise |

**Deprecated/outdated:**
- `librosa.beat.beat_track(units='frames')` without specifying `sr`: Units conversion changed in 0.8; always pass `sr` explicitly (relevant for Phase 3).
- `librosa.output.write_wav()`: Removed in librosa 0.8; use `soundfile.write()` instead if audio export is needed.

---

## Open Questions

1. **Does `pip install librosa==0.11.0` actually succeed in `backend/.venv` on Python 3.14.2?**
   - What we know: numba 0.64.0 has Python 3.14 wheels; librosa's `python_requires` has no upper bound (`>=3.8`); `standard-aifc`/`standard-sunau` are conditional deps for 3.13+
   - What's unclear: Whether pip resolves an old numba (pre-0.64.0) that blocks 3.14, or whether librosa classifiers cause pip to refuse; this must be run in the actual venv to confirm
   - Recommendation: **First task in Phase 2 plan must be a `pip install librosa` smoke test.** If blocked, pin `numba>=0.64.0` first or use `--ignore-requires-python`.

2. **Key detection accuracy baseline**
   - What we know: K-S algorithm works well on tonally clear music; accuracy degrades on atonal, jazz, or chord-sparse songs
   - What's unclear: No published benchmark for this specific pipeline (chroma_cqt on HPSS harmonic + K-S). The Phase 2 success criteria requires validating against 1 known song.
   - Recommendation: Use a well-known, tonally clear test song (e.g., "Let It Be" in C major, or any classic pop song with known key) and validate the pipeline returns the correct root and mode before declaring Phase 2 done.

3. **`ROOTS` list for the ROOTS array in detect_key()**
   - What we know: semitone 0=C, 1=C#/Db, 2=D, etc. The flat vs sharp choice for the ROOTS array affects what key string is formed, which then determines what `key_to_notes()` returns
   - What's unclear: Should ROOTS use flats or sharps for ambiguous semitones (1, 3, 6, 8, 10)? The K-S algorithm returns the best pitch class index — if that index is 1 and you name it "Db", `key_to_notes("Db:maj")` gives flat spellings. If you name it "C#", you get sharp spellings.
   - Recommendation: Use the ROOTS list in the code example above (`['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']`) which matches standard music theory conventions: flat names for semitones on the flat side of the circle of fifths, F# for the tritone (semitone 6). This gives correct flat-key behavior. Validate with the enharmonic test cases in Code Examples.

---

## Sources

### Primary (HIGH confidence)
- `https://librosa.org/doc/main/generated/librosa.load.html` — librosa.load() API: all parameters verified including `sr`, `mono`, `duration`, `dtype`
- `https://librosa.org/doc/latest/generated/librosa.key_to_notes.html` — key_to_notes() API: format, enharmonic rules, examples verified
- `https://librosa.org/doc/main/_modules/librosa/core/notation.html` — source code: flat/sharp decision logic via `tonic_number` and `offset` verified
- `https://librosa.org/doc/main/generated/librosa.feature.chroma_cqt.html` — chroma_cqt() API: parameters and return shape verified
- `https://librosa.org/doc/main/generated/librosa.effects.hpss.html` — hpss() API: return values (y_harmonic, y_percussive) verified
- `https://github.com/librosa/librosa/blob/main/setup.cfg` — dependency constraints: `python_requires = >=3.8`, numba >=0.51.0, standard-aifc/standard-sunau conditional deps
- `https://pypi.org/project/numba/` — numba 0.64.0 (Feb 18, 2026) confirmed: Python 3.14 wheels (`cp314`) present

### Secondary (MEDIUM confidence)
- `https://gist.github.com/bmcfee/1f66825cef2eb34c839b42dddbad49fd` — K-S reference implementation by Brian McFee (librosa author): verified as the canonical algorithm source
- `https://github.com/librosa/librosa/issues/1883` — Python 3.13 numba issue history: confirms numba 0.61+ resolved 3.13; 0.64.0 resolves 3.14
- `https://numba.discourse.group/t/ann-numba-0-63-0b1-llvmlite-0-46-0b1-python-3-14-support/3068` — numba 3.14 support announcement: 0.63.0b1 in Oct 2025, 0.63.1 stable Dec 2025, 0.64.0 Feb 2026

### Tertiary (LOW confidence)
- WebSearch results indicating librosa 0.11.0 was developed with Python 3.13 as highest tested version — classification only, not an install block

---

## Metadata

**Confidence breakdown:**
- librosa.load() API: HIGH — official docs verified
- key_to_notes() enharmonic behavior: HIGH — source code + API docs verified
- Python 3.14 install success: MEDIUM — numba 0.64.0 has py314 wheels; librosa has no upper bound; but actual install in venv is unverified
- K-S algorithm implementation: HIGH — reference implementation from librosa author
- Memory math: MEDIUM — calculation is straightforward but actual HPSS peak not measured in the target venv

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (30 days — librosa is stable; numba/Python 3.14 compat should be stable at this point)
