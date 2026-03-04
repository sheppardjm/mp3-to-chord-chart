# Project Research Summary

**Project:** dontCave
**Domain:** MP3-to-chord-chart personal tool (audio chord detection, lyric alignment, web display)
**Researched:** 2026-03-03
**Confidence:** MEDIUM-HIGH

## Executive Summary

dontCave is a personal-use web tool that takes an MP3 file and user-supplied lyrics as input and produces a guitarist-readable chord chart as output — chords displayed above lyrics in the Ultimate Guitar two-line format, organized by song section. This is a well-understood class of problem in Music Information Retrieval (MIR), and a mature Python stack exists to implement it: librosa for audio analysis, pychord for chord object representation, FastAPI for the backend, and ChordSheetJS + svguitar for frontend rendering. The core technical differentiator over tools like Chordify or Chord AI is the one-shot flow — audio and lyrics go in together and a unified chart comes out, rather than requiring manual assembly.

The recommended implementation is a sequential 7-stage audio pipeline (load, key detection, beat tracking, chroma extraction, chord classification, structural segmentation, simplification) backed by a FastAPI REST endpoint and a lightweight vanilla JS frontend. Chord detection accuracy at 60-75% (template matching) is adequate for the personal-tool goal state; more accurate alternatives (essentia, madmom) either require AGPL licensing or support only Python 3.7. The lyric-to-chord alignment is best handled with a line-count heuristic rather than forced phoneme-level alignment — the latter is a separate research problem and would stall MVP delivery.

The two risks that can cause project failure if ignored are: (1) using raw chroma argmax for chord labeling instead of beat-synchronized template matching with Viterbi smoothing — this produces unusable output and requires a full backend rewrite to correct; and (2) running audio analysis synchronously in the request handler — a 4-minute MP3 takes 10-60 seconds of CPU and will hang the server. Both must be addressed in Phase 1 before any UI work begins.

---

## Key Findings

### Recommended Stack

The Python audio stack is mature and well-specified. librosa 0.11.0 (released March 2025) is the standard library for MIR in Python: it covers CQT chromagrams, beat tracking, harmonic-percussive separation, and structural segmentation. soundfile 0.13.1 handles MP3 loading natively via libmpg123, eliminating the pydub/ffmpeg dependency for most files. FastAPI 0.135.1 with uvicorn handles the async requirement — audio processing must run in a threadpool to avoid blocking the event loop. On the frontend, ChordSheetJS 14.0.0 handles the hard problem of chord-above-lyric horizontal alignment, and svguitar 2.5.1 (TypeScript-native, pure SVG, published Feb 2026) renders chord fingering diagrams. Vite bundles the frontend with zero framework overhead.

All recommended library versions have been verified against PyPI/npm as of 2026-03-03. Alternatives considered (madmom: Python 3.7 max, unmaintained; autochord: 67% accuracy, TensorFlow, 2021; essentia: AGPL-3.0, hard macOS install; pydub: unmaintained, slow) are explicitly excluded.

**Core technologies:**
- **FastAPI 0.135.1** — async REST backend for file upload and pipeline orchestration — native async prevents audio processing from blocking requests
- **librosa 0.11.0** — all audio analysis (chroma, beat tracking, segmentation) — de facto MIR standard, 800k+ weekly downloads, actively maintained
- **pychord 1.3.2** — chord object representation (naming, quality, slash chords) — lightweight, works with detected chord names post-template-matching
- **soundfile 0.13.1** — MP3/WAV/FLAC loading — native MP3 via libmpg123, significantly faster than pydub for read-only analysis
- **ChordSheetJS 14.0.0** — frontend chord-over-lyric layout — only maintained JS library that handles horizontal alignment correctly
- **svguitar 2.5.1** — frontend SVG chord fingering diagrams — TypeScript-native, pure SVG, no canvas dependency, barre chord support
- **Vite (>=5.x)** — frontend build tooling — zero-config for vanilla JS, no framework overhead needed for a personal tool

### Expected Features

The competitor landscape (Chordify, Ultimate Guitar, Chord AI, Yamaha Chord Tracker, Moises) establishes clear table stakes. The core differentiator — one-shot generation of a unified chord chart from audio + lyrics — is absent from all surveyed tools, which either handle audio analysis or lyrics display but not both as an integrated single step.

**Must have (table stakes):**
- MP3 file upload + chord detection (major/minor/7th) — without this, nothing else exists
- Chord names displayed above lyrics (UG two-line format) — the industry-standard chord chart layout
- Song section labels (Verse/Chorus/Bridge) — musicians navigate by section; auto-detection from audio is acceptable at 60-70% accuracy
- Chord fingering diagrams (static SVGs for ~20 chords in scope) — every comparable tool shows "how to play this chord"
- Detected song key displayed in chart header — low cost, meaningful musical context
- PDF/print export via browser print CSS — musicians take charts to rehearsals; print is expected

**Should have (competitive):**
- ChordPro text export — interoperability with OnSong, SongSheet Pro, and dozens of gigging apps at minimal implementation cost
- Section label editing (click to rename) — auto-detection is ~60-70% accurate; users need to correct errors
- Auto-detected key used to enforce enharmonic naming convention (flat keys use flats) — musicially correct notation
- Section confidence indicator — honest about detection uncertainty; none of the surveyed competitors do this

**Defer (v2+):**
- Real-time playback sync (audio + scrolling chord highlight) — doubles infrastructure scope; validate demand first
- Full key transposition — complex music theory logic; capo suggestion table covers most use cases at far lower cost
- User accounts and session persistence — turns a stateless tool into a full app; not needed for personal use
- MIDI export — useful only for DAW users, not the target guitarist audience

### Architecture Approach

The system is a straightforward client-server architecture: a vanilla JS frontend submits a multipart POST (MP3 file + lyrics text) to a FastAPI backend, the backend runs a 7-stage sequential audio analysis pipeline, returns a JSON chart structure, and the frontend renders it. No database, no user accounts, no task queue required for the personal-tool scope (though FastAPI's threadpool via `run_in_executor` is needed to keep the event loop unblocked during processing). The pipeline is organized as separate modules per stage — each stage receives a typed dict and returns a typed dict — enabling per-stage unit testing and future stage swaps without touching the rest of the system. The chord-to-lyric alignment uses a line-count heuristic (distribute chords proportionally across lyric lines) rather than forced phoneme alignment, which is the correct pragmatic choice for this scope.

**Major components:**
1. **Upload Handler** — validates MIME type and file size (max 50MB), writes to temp file with UUID filename, passes file path to pipeline
2. **Audio Analysis Pipeline** — 7-stage sequential librosa-based pipeline producing `{sections: [{label, beats, chords, timestamps}]}`
3. **Chart Builder** — pure data transformation: aligns chord sequence with user lyric lines by section, produces ChartData JSON via Pydantic models
4. **Chart Display UI** — renders chord names as `<span>` elements above lyric text in section blocks using ChordSheetJS layout
5. **Fingering Diagram UI** — renders SVG guitar chord diagrams via svguitar.js for each unique chord in the detected set

### Critical Pitfalls

All five critical pitfalls identified target the audio processing layer. Four of the five must be solved in Phase 1 before any frontend work begins.

1. **Raw chroma argmax as chord labels** — produces ~30% accuracy; users immediately distrust output; requires full backend rewrite to fix. Use beat-synchronized template matching with cosine similarity. Validate against 5-10 known songs before building the chart layer.

2. **Synchronous audio processing in request handler** — 10-60 second CPU operation blocks all requests; users assume the app crashed. Run pipeline via `run_in_executor` in FastAPI; show progress indicator in UI ("Analyzing audio... Detecting beats... Mapping chords...").

3. **MP3 decompression memory explosion** — a 20MB MP3 decodes to 200-600MB RAM; multiple uploads exhaust server memory. Always load with `sr=22050, mono=True, duration=300`; explicitly `del y; gc.collect()` after pipeline completes.

4. **Missing beat alignment** — without `librosa.beat.beat_track()` and `librosa.util.sync()`, chords change every 0.02 seconds and the chart is musically unreadable. Beat sync reduces frame-level chords to ~100-200 beat-level chords per song.

5. **Key estimation errors causing wrong enharmonic names** — E7 presence can cause the key estimator to detect E major instead of A major; flat-key songs should use flat notation (Bb not A#). Run key estimation first, use detected key to constrain chord naming convention.

---

## Implications for Roadmap

Based on the dependency graph from FEATURES.md, the architecture build order from ARCHITECTURE.md, and the pitfall-to-phase mapping from PITFALLS.md, the following phase structure is recommended.

### Phase 1: Audio Pipeline Foundation

**Rationale:** Everything else depends on correct chord detection. The pitfalls research is unanimous: chord accuracy and beat alignment must be validated before any UI work begins. Building the pipeline first in isolation (Jupyter notebook → unit tests → FastAPI endpoint) allows early detection of accuracy problems when fixing them is cheap. The architecture explicitly calls this out as the correct build order.

**Delivers:** A working POST /analyze endpoint that accepts an MP3 and returns a structured JSON chord timeline with key, tempo, section boundaries, and beat-aligned chord labels. Testable with curl before any frontend exists.

**Addresses:** MP3 upload, audio chord detection (major/minor/7th), beat tracking, key detection, structural segmentation

**Avoids:** Raw chroma argmax (Pitfall 1), synchronous blocking (Pitfall 3), memory explosion (Pitfall 2), missing beat alignment (Pitfall 4), wrong enharmonic naming (Pitfall 5)

**Key implementation notes:**
- Load audio: `librosa.load(path, sr=22050, mono=True, duration=300)`
- Use `librosa.effects.hpss()` to isolate harmonic component before chroma extraction
- Use `librosa.feature.chroma_cqt()` not `chroma_stft` (more accurate for music)
- Beat-sync chroma with `librosa.util.sync()` before template matching
- Run pipeline in `run_in_executor` to avoid blocking FastAPI event loop
- Validate against 5-10 known songs before proceeding to Phase 2

### Phase 2: Chart Builder and Backend Contract

**Rationale:** Once the pipeline produces reliable chord+section data, the next dependency is the lyric-chord alignment and the JSON contract between backend and frontend. This is a pure data-transformation layer that is independent of audio signal processing and has its own unit tests. Defining the Pydantic models here locks in the API contract that the frontend will consume.

**Delivers:** `chart_builder.build(pipeline_result, lyrics_text)` returning a validated ChartData JSON structure. Pydantic models defining the backend-frontend API contract. The section-to-lyric heuristic alignment (distribute chord timeline across lyric lines by proportion).

**Addresses:** Chord-to-lyric alignment, section labels, the `unique_chords` list needed by fingering diagrams

**Uses:** pychord for chord object representation, Pydantic for response model validation

**Implements:** Chart Builder component; `chart/models.py` and `chart/builder.py`

### Phase 3: Frontend — Chord Chart Display

**Rationale:** With a stable JSON API, the frontend rendering is straightforward. ChordSheetJS handles the hardest part (horizontal chord-above-lyric alignment). Build against hardcoded JSON first to confirm layout, then wire to the live endpoint.

**Delivers:** A functional chord chart UI displaying chords above lyrics in UG two-line format, organized by detected sections. Upload form wired to the backend. Progress indicator during analysis. PDF/print export via print CSS.

**Addresses:** Chord chart display (table stakes), section labels, key display in header, print export

**Avoids:** UX pitfall of no processing feedback (show "Analyzing audio... Detecting beats... Mapping chords..."), chord display with no grouping (collapse adjacent identical chords first)

**Uses:** ChordSheetJS 14.0.0 for layout, Vite for build tooling

### Phase 4: Chord Fingering Diagrams and Polish

**Rationale:** Fingering diagrams are a self-contained frontend enhancement that enhances but does not block the core chart functionality. They are deferred to Phase 4 so earlier phases can be validated without this dependency. svguitar renders SVGs client-side from the `unique_chords` list — no backend changes needed.

**Delivers:** SVG guitar chord fingering diagrams for every chord detected in the song. Graceful fallback for unusual chords. Section label in-place editing. ChordPro text export.

**Addresses:** Chord fingering diagrams (table stakes), section label editing (should-have), ChordPro export (should-have)

**Uses:** svguitar 2.5.1

**Avoids:** Showing diagrams for chords not in the song (cognitive overload), generating diagrams server-side (slow, large payloads — generate client-side)

### Phase Ordering Rationale

- **Pipeline-first order** is mandated by the feature dependency graph: chord detection → timestamps → lyric alignment → chart display. There is no shortcut.
- **Backend before frontend** is mandated by the API contract: the frontend cannot be validated against live data until the JSON schema is finalized in Phase 2.
- **Diagrams last** because svguitar integration is entirely frontend-side and has no backend dependencies — it is the safest feature to defer.
- **No user accounts, no database** in any phase — the research clearly identifies these as scope-expanding anti-features for a personal tool.
- **No real-time playback sync** in v1 — the architecture and features research both classify this as a phase-doubling feature best validated after core functionality is proven.

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 1 (Audio Pipeline):** Structural segmentation (Stage 6) is the most complex and least deterministic step. Laplacian segmentation requires tuning the `k` parameter for number of sections. May need experimentation per song type. Consider researching `librosa.segment` examples against real pop songs before committing to the implementation.
- **Phase 1 (Audio Pipeline):** 7th chord template matching accuracy needs empirical validation. The research cites 60-75% overall accuracy for template-based methods, but 7th chords specifically have no published baseline for the recommended approach. Validate early.

Phases with standard patterns (skip research-phase):

- **Phase 2 (Chart Builder):** Pure data transformation with Pydantic. Well-documented FastAPI patterns. No novel engineering.
- **Phase 3 (Frontend):** ChordSheetJS is well-documented with examples. Vite vanilla template is straightforward. Print CSS for export is a standard browser capability.
- **Phase 4 (Diagrams + Polish):** svguitar has clear API documentation. ChordPro format is a published standard.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All library versions verified against PyPI/npm as of 2026-03-03. Version compatibility matrix documented. Installation instructions verified. No speculation. |
| Features | MEDIUM | Competitor feature survey based on WebSearch and WebFetch; some sources (Yamaha, UG) returned 403s. Core table stakes are well-established by industry convention. Feature prioritization is reasoned but not user-tested. |
| Architecture | MEDIUM-HIGH | Architecture derived from documented librosa patterns, ChordMiniApp reference implementation, and MIR literature. Pipeline stage order is academically verified. Specific chord detection accuracy numbers (60-75%) are research-based but vary by song/genre. |
| Pitfalls | MEDIUM | Pitfalls sourced from librosa GitHub issues, MIR research papers, and AudioLabs Erlangen academic materials. The critical pitfalls (raw chroma, beat alignment, blocking) are well-corroborated across multiple independent sources. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Structural segmentation accuracy on pop songs:** The research documents that `librosa.segment` Laplacian segmentation achieves ~60-70% on section boundary detection. This is the most unpredictable stage. Plan for the UI to allow section label editing from the start, not as a v1.x addition.

- **7th chord template accuracy baseline:** Published MIREX benchmarks cover 25-vocabulary (including 7ths) at ~65-70% overall, but the specific template-matching approach for dominant 7ths has no published baseline. This gap should be addressed in Phase 1 validation before committing to the chord vocabulary scope.

- **svguitar chord coverage for edge-case chord names:** The research confirms svguitar supports standard guitar chords but does not enumerate its full chord dictionary. Unusual detected chords (e.g., Ebm, F#7) must be tested early to confirm graceful fallback behavior or pre-validate the chord set the pipeline can produce.

- **ffmpeg availability in deployment environment:** The pitfalls research flags ffmpeg on PATH as a deployment risk. If the personal-tool environment is macOS only, `brew install ffmpeg` is sufficient. If there's any chance of deploying to a cloud server, verify ffmpeg availability in that environment explicitly.

---

## Sources

### Primary (HIGH confidence)
- librosa 0.11.0 official documentation — https://librosa.org/doc/0.11.0/
- FastAPI 0.135.1 PyPI — https://pypi.org/project/fastapi/
- uvicorn 0.41.0 PyPI — https://pypi.org/project/uvicorn/
- pychord 1.3.2 PyPI — https://pypi.org/project/pychord/
- soundfile 0.13.1 PyPI — https://pypi.org/project/soundfile/
- ChordSheetJS v14.0.0 GitHub releases — https://github.com/martijnversluis/ChordSheetJS/releases
- svguitar v2.5.1 GitHub releases — https://github.com/omnibrain/svguitar/releases
- Template-Based Chord Recognition (AudioLabs Erlangen) — https://www.audiolabs-erlangen.de/resources/MIR/FMP/C5/C5S2_ChordRec_Templates.html
- ChordMiniApp reference implementation — https://github.com/ptnghia-j/ChordMiniApp
- librosa GitHub issues #681, #406 — memory leak and memory constraints
- MIREX 2024 Audio Chord Estimation evaluation framework — https://music-ir.org/mirex/wiki/2024:Audio_Chord_Estimation

### Secondary (MEDIUM confidence)
- Chord AI official site — https://chordai.net/ (WebFetch verified)
- Hooktheory Chordify alternatives analysis — https://www.hooktheory.com/blog/chordify-alternatives/ (WebFetch verified)
- FastAPI vs Flask comparison 2025 — https://strapi.io/blog/fastapi-vs-flask-python-framework-comparison
- MDPI key detection via key-profiles — https://www.mdpi.com/2076-3417/12/21/11261
- ResearchGate: Automatic Chord Detection Incorporating Beat and Key Detection — https://www.researchgate.net/publication/224363462
- Moises Advanced Chord Detection blog — https://moises.ai/blog/moises-news/advanced-chord-detection/

### Tertiary (LOW confidence)
- Yamaha Chord Tracker features page (403 error; features inferred from secondary sources)
- Ultimate Guitar app store listing (features extrapolated from known UG product; direct fetch unavailable)

---
*Research completed: 2026-03-03*
*Ready for roadmap: yes*
