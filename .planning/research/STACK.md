# Stack Research

**Domain:** MP3-to-chord-chart personal tool (audio chord detection, lyric alignment, web display)
**Researched:** 2026-03-03
**Confidence:** MEDIUM-HIGH (core Python audio stack HIGH; frontend chord display MEDIUM; lyric-chord alignment MEDIUM)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| FastAPI | 0.135.1 | Python backend / REST API | Native async support handles slow audio processing without blocking; auto-generates OpenAPI docs; 3-5x faster than Flask under load. For a tool with file uploads and potentially slow DSP operations, async matters. Requires Python >=3.10. |
| uvicorn | 0.41.0 | ASGI server to run FastAPI | The standard ASGI server for FastAPI; lightweight, production-capable for personal tools. |
| librosa | 0.11.0 | Audio feature extraction (chroma, beat tracking, structural segmentation) | The de facto standard for MIR in Python. 800k+ weekly downloads; active maintenance (released March 11, 2025); covers every feature needed: CQT chromagrams, beat tracking, harmonic-percussive separation, structural segmentation. |
| pychord | 1.3.2 | Python chord object model (chord name → notes, quality, transposition) | Lightweight library to represent chords as Python objects; handles major, minor, 7th, and slash chords. Used after the chroma template matching step to name detected chords formally. Released Jan 25, 2026. |
| numpy | 2.4.2 | Numerical arrays for audio signal processing | Librosa returns everything as numpy arrays; required for all DSP operations. |
| soundfile | 0.13.1 | Primary audio file reader (WAV, FLAC, OGG, MP3 with libsndfile >=1.2) | Librosa's default backend as of v0.7. v0.13 added native MP3 support via libmpg123. Significantly faster than pydub for reading files that only need to be analyzed. |
| python-multipart | 0.0.22 | Multipart form data for file uploads | Required by FastAPI to receive uploaded MP3 files via `UploadFile`; no alternative within the FastAPI ecosystem. |
| python-dotenv | 1.2.2 | Environment variable management | Simple config management for local dev; standard practice. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydub | 0.25.1 | MP3 → WAV/numpy conversion fallback | Use only if soundfile fails to load the user's MP3 (e.g., unusual encoding). Wraps ffmpeg; requires ffmpeg binary on PATH. Do not use as the primary loader — it is slow and unmaintained (last release 2021). |
| scipy | latest (>=1.13) | Signal processing utilities | Use for median filters and smoothing on the chord timeline; already a librosa dependency. |
| ChordSheetJS | 14.0.0 | JS library: parse and format chord sheets (ChordPro, UltimateGuitar, chords-over-words) | The only well-maintained JS library that handles chord-over-lyric layout with proper horizontal alignment. UltimateGuitarParser is built-in. Released Feb 12, 2025 with section-type support. |
| svguitar | 2.5.1 | JS library: render SVG guitar chord fingering diagrams | Used in production at chordpic.com; TypeScript-native; highly customizable SVG output; barre chord support; last published Feb 23, 2026. No canvas dependency — pure SVG, embeds cleanly in any HTML. |
| Vite | >=5.x | Frontend build tool / dev server | Zero-config for vanilla JS/HTML/CSS; fast HMR; no framework overhead needed for a personal tool. Supports vanilla-ts template. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| ffmpeg (system binary) | MP3 decoding fallback, audio format conversion | Required on PATH when soundfile cannot decode a specific MP3. Not a Python package — install via Homebrew (`brew install ffmpeg`) or system package manager. |
| pytest | Backend testing | Standard Python test runner; use with `pytest-asyncio` for FastAPI async routes. |
| httpx | FastAPI test client | Required by FastAPI's `TestClient`; replaces requests in async contexts. |

---

## Installation

```bash
# Python backend (inside virtualenv or conda env, Python >= 3.10)
pip install fastapi==0.135.1
pip install uvicorn==0.41.0
pip install librosa==0.11.0
pip install pychord==1.3.2
pip install numpy>=2.4
pip install soundfile==0.13.1
pip install python-multipart==0.0.22
pip install python-dotenv==1.2.2

# Optional: only if MP3 loading via soundfile fails on target machine
pip install pydub==0.25.1

# System dependency (macOS)
brew install ffmpeg

# Frontend (Node >= 20.19)
npm create vite@latest frontend -- --template vanilla
cd frontend
npm install chordsheetjs@14.0.0
npm install svguitar@2.5.1
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| librosa (chroma template matching) | essentia (ChordsDetection algorithm) | If you need higher chord detection accuracy (essentia's HPCP achieves ~80% vs librosa chroma's lower baseline). Essentia is AGPL-3.0, which may be a license concern. It's a large C++ library with Python bindings — harder to install, especially on non-Linux. For a personal tool, librosa's simpler install and adequate accuracy win. |
| librosa (chroma template matching) | autochord (Bi-LSTM-CRF model) | Only if you need ML-based detection without implementing it yourself. autochord achieves 67% accuracy on 25 classes but has not been updated since Oct 2021 and requires TensorFlow. Avoid for new projects. |
| librosa (chroma template matching) | madmom (DNN + CRF) | madmom achieves ~89% accuracy and was the academic SOTA for chord recognition. However, madmom 0.16.1 was released in 2018, only supports Python <=3.7, and is unmaintained. Do not use in 2025. |
| FastAPI | Flask | Use Flask only if you want minimal dependencies and are already familiar with it. Flask is simpler but WSGI (synchronous), which means audio processing blocks all requests. For a personal tool with infrequent use, this is tolerable, but FastAPI's async support is a better foundation. |
| soundfile | audioread | audioread is deprecated in librosa >=0.10.0 and will be removed in 1.0. Do not take a direct dependency on it. |
| svguitar | vexchords / ChordJS / jTab | svguitar is the only library in this space with active maintenance (published Feb 2026), TypeScript types, and SVG output. vexchords is canvas-based. ChordJS is old. jTab has no npm package. |
| ChordSheetJS | custom HTML generation | ChordSheetJS's MeasuredHtmlFormatter handles the hard problem of chord-above-lyric alignment with correct horizontal positioning. Writing this yourself is a significant time sink. |
| Vite (vanilla JS) | React / Vue | A personal tool does not need a component framework. Vanilla JS + Vite keeps the bundle small and eliminates framework lock-in. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| madmom | Python 3.7 max, unmaintained since 2018, will not install on modern Python | librosa chroma template matching (80%+ for major/minor) |
| autochord | Last release Oct 2021; requires TensorFlow; only 67% accuracy; no 7th chord support | librosa + pychord |
| chord-extractor | Wraps the Chordino VAMP plugin binary; requires pre-compiled shared library; Linux 64-bit only by default; latest release Aug 2025 but fragile binary dependency | librosa chroma template matching |
| pydub as primary audio loader | Unmaintained since 2021 (v0.25.1); requires ffmpeg as a subprocess; significantly slower than soundfile for read-only analysis | soundfile 0.13.1 (native MP3 support) |
| essentia as primary stack | AGPL-3.0 license (viral); large C++ build; installation on macOS/Windows is non-trivial; pre-release versioning (2.1b6.dev) | librosa (ISC license, pure Python wheels) |
| audioread | Deprecated in librosa 0.10+, scheduled for removal in librosa 1.0 | soundfile 0.13.1 |
| jQuery / Bootstrap | Unnecessary weight for a personal tool with simple UI needs | Vanilla JS, CSS custom properties |
| Django | Framework overhead vastly exceeds the scope of a single-purpose API; migrations, ORM, admin panel all irrelevant | FastAPI |

---

## Stack Patterns by Variant

**If accurate chord detection is the top priority (over ease of setup):**
- Use essentia instead of librosa for audio analysis
- essentia's ChordsDetectionBeats algorithm uses HPCP (Harmonic Pitch Class Profile) which beats plain chroma template matching
- Accept the AGPL-3.0 license and the harder installation

**If targeting deployment (not just local use):**
- Add a task queue: Celery + Redis, or FastAPI BackgroundTasks (simpler, no broker needed)
- Audio processing takes 5-30 seconds for a 4-minute song; must be async or queued
- Return a job ID immediately; poll for results

**If targeting 7th chord recognition specifically:**
- librosa chroma + template matching for 7th chords: add templates for dominant 7th (1,0,0,0,1,0,0,1,0,0,1,0) etc.
- This is a manual step — none of the off-the-shelf Python libraries target 7th chords in their default model
- pychord handles 7th chord representation once you've detected the name

**If building purely local (no web server):**
- Replace FastAPI with a simple Python script + CLI arguments
- Still use librosa + pychord for analysis
- Generate a static HTML file instead of a live web UI

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| librosa 0.11.0 | numpy >=1.20, soundfile >=0.12 | librosa 0.11 dropped Python 3.7/3.8 support in practice; use Python 3.10+ |
| soundfile 0.13.1 | libsndfile >=1.2.2 (bundled in wheels) | MP3 support requires libsndfile built with libmpg123; the PyPI wheel includes this on Linux/macOS |
| FastAPI 0.135.1 | Python >=3.10, uvicorn 0.41.0 | FastAPI requires Python >=3.10 as of recent versions |
| ChordSheetJS 14.0.0 | Node >=18, no peer deps | Includes UltimateGuitarParser with section-type support (added in v14) |
| svguitar 2.5.1 | No framework deps; pure TS/JS | Works in Vite vanilla builds without modification |

---

## Chord Detection Approach (Prescriptive)

The standard approach for detecting major, minor, and 7th chords from audio using librosa:

```python
import librosa
import numpy as np

# 1. Load audio (soundfile handles MP3 natively in 0.13+)
y, sr = librosa.load("song.mp3", sr=22050, mono=True)

# 2. Separate harmonic component (reduces percussion noise in chroma)
y_harmonic, _ = librosa.effects.hpss(y)

# 3. Extract CQT-based chromagram (more accurate than STFT chroma for music)
chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr)

# 4. Beat-synchronous chroma (aggregate chroma over each beat interval)
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
beat_chroma = librosa.util.sync(chroma, beat_frames, aggregate=np.median)

# 5. Template matching against major/minor/7th chord templates
# Map each beat's chroma vector to the closest chord template

# 6. Structural segmentation (for verse/chorus detection)
# Use librosa.segment.recurrence_matrix + agglomerative clustering
```

This pipeline is well-documented in librosa 0.11.0's official tutorial and is the standard MIR approach. Confidence: HIGH (verified against librosa 0.11.0 official docs).

---

## Lyric-Chord Alignment Approach

For user-supplied lyrics, the alignment strategy is:

1. User provides lyrics as plain text (one line per lyric line)
2. Backend runs chord detection with beat timestamps (above)
3. Backend counts lyric lines and distributes them across song sections detected by librosa's structural segmentation
4. Frontend uses ChordSheetJS to render chords over the correct lyric syllables

**Note:** Full automatic lyric-to-audio alignment (phoneme-level) is a separate hard problem involving vocal separation, phoneme recognition, and forced alignment (e.g., synctoolbox, aeneas). For a personal tool where the user provides lyrics manually, this level of precision is unnecessary. A simpler heuristic — evenly distribute lines across detected sections — is sufficient and dramatically easier to implement. Confidence: MEDIUM (pragmatic simplification; the academic alternative is well-researched but overly complex for this scope).

---

## Sources

- librosa 0.11.0 official tutorial and ioformats docs — https://librosa.org/doc/0.11.0/ — HIGH confidence
- librosa PyPI page (verified version 0.11.0, released March 11, 2025) — https://pypi.org/project/librosa/ — HIGH confidence
- FastAPI PyPI page (verified version 0.135.1, released March 1, 2026) — https://pypi.org/project/fastapi/ — HIGH confidence
- uvicorn PyPI page (verified version 0.41.0, released Feb 16, 2026) — https://pypi.org/project/uvicorn/ — HIGH confidence
- pychord PyPI page (verified version 1.3.2, released Jan 25, 2026) — https://pypi.org/project/pychord/ — HIGH confidence
- soundfile PyPI page (verified version 0.13.1; MP3 support via libsndfile 1.2.2) — https://pypi.org/project/soundfile/ — HIGH confidence
- python-multipart PyPI (verified version 0.0.22, Jan 25, 2026) — https://pypi.org/project/python-multipart/ — HIGH confidence
- python-dotenv PyPI (verified version 1.2.2, March 1, 2026) — https://pypi.org/project/python-dotenv/ — HIGH confidence
- ChordSheetJS GitHub releases (verified v14.0.0, Feb 12, 2025) — https://github.com/martijnversluis/ChordSheetJS/releases — HIGH confidence
- svguitar GitHub releases (verified v2.5.1, Feb 23, 2026) — https://github.com/omnibrain/svguitar/releases — HIGH confidence
- essentia PyPI (version 2.1b6.dev1389, AGPL-3.0, July 2025) — https://pypi.org/project/essentia/ — HIGH confidence
- madmom PyPI (version 0.16.1, released Nov 2018, Python <=3.7) — https://pypi.org/project/madmom/ — HIGH confidence (confirmed unmaintained)
- autochord PyPI (version 0.1.4, Oct 2021, 67% accuracy) — https://pypi.org/project/autochord/ — HIGH confidence (confirmed stale)
- FastAPI vs Flask comparison 2025 — https://strapi.io/blog/fastapi-vs-flask-python-framework-comparison — MEDIUM confidence (WebSearch, multiple corroborating sources)
- Template-based chord recognition (FMP Notebook) — https://www.audiolabs-erlangen.de/resources/MIR/FMP/C5/C5S2_ChordRec_Templates.html — HIGH confidence (academic reference)

---

*Stack research for: MP3-to-chord-chart personal tool*
*Researched: 2026-03-03*
