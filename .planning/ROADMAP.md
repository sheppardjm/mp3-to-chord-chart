# Roadmap: dontCave

## Overview

dontCave is built in eight sequential phases, each delivering a distinct, verifiable capability. The order is mandated by the dependency graph: the audio analysis pipeline must produce correct, beat-synchronized chord data before any chart-building or UI work can be validated. Phases 1-4 build and validate the backend pipeline in isolation; Phases 5-6 wire it to user inputs and produce structured chart data; Phases 7-8 render the chart and fingering diagrams in the browser.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Project Scaffold** - FastAPI backend skeleton and Vite frontend skeleton, wired together and confirmed running
- [x] **Phase 2: Audio Loading and Key Detection** - MP3 loads correctly with memory constraints; detected key drives enharmonic naming
- [x] **Phase 3: Beat Tracking and Chord Detection** - Beat-synchronized, template-matched chord labels produced from audio
- [x] **Phase 4: Structural Segmentation** - Song sections (Verse, Chorus, Bridge) auto-detected from audio and labeled
- [x] **Phase 5: Upload Handler and Async Processing** - MP3 file upload with validation; pipeline runs off the request thread with progress feedback
- [ ] **Phase 6: Lyrics Input, Chart Builder, and API Contract** - User pastes lyrics; backend aligns chord timeline to lyric lines and returns ChartData JSON
- [ ] **Phase 7: Chord Chart Display** - Frontend renders chords above lyrics in Ultimate Guitar format, organized by section
- [ ] **Phase 8: Chord Fingering Diagrams** - SVG fingering diagrams rendered for every unique chord in the song

## Phase Details

### Phase 1: Project Scaffold
**Goal**: A running skeleton that proves the stack works end-to-end before any real logic is written
**Depends on**: Nothing (first phase)
**Requirements**: INTG-02
**Success Criteria** (what must be TRUE):
  1. `uvicorn main:app` starts the FastAPI server without errors on the development machine
  2. `vite dev` starts the frontend dev server and serves the HTML page in a browser
  3. A GET request to the backend health endpoint returns a 200 response
  4. The frontend successfully fetches and displays a response from the backend (CORS configured)
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md -- Set up FastAPI backend with pyproject.toml, venv, dependencies, and health endpoint
- [x] 01-02-PLAN.md -- Scaffold Vite vanilla JS frontend, configure proxy to backend, verify full-stack communication

---

### Phase 2: Audio Loading and Key Detection
**Goal**: MP3 files load within memory constraints and the detected song key is available to drive correct enharmonic chord naming throughout the rest of the pipeline
**Depends on**: Phase 1
**Requirements**: AUDIO-04
**Success Criteria** (what must be TRUE):
  1. A 4-minute MP3 file loads without exceeding 600MB RAM (verified by sampling peak memory during load)
  2. `librosa.load()` is called with `sr=22050, mono=True, duration=300` — confirmed in code, not left to defaults
  3. The detected key for a known test song (e.g., a G major song) is returned as the correct root and mode
  4. Enharmonic naming convention derived from key is applied: flat-key songs produce Bb/Eb/Ab, not A#/D#/G#
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md -- Install librosa into Python 3.14 venv and create audio loader module with constrained librosa.load() and HPSS separation
- [x] 02-02-PLAN.md -- Implement key detection with Krumhansl-Schmuckler algorithm and validate enharmonic naming against test audio

---

### Phase 3: Beat Tracking and Chord Detection
**Goal**: The pipeline produces beat-synchronized, template-matched chord labels that are musically readable — not frame-level noise
**Depends on**: Phase 2
**Requirements**: AUDIO-01, AUDIO-02
**Success Criteria** (what must be TRUE):
  1. Beat positions are detected for a test song and the count is plausible (80-160 beats for a 3-minute 100BPM song)
  2. Chord labels change on beat boundaries, not on every audio frame
  3. Adjacent identical chords are collapsed — a 4-bar C chord appears as one C entry, not 16 identical beats
  4. Chord detection produces only major, minor, and 7th chord labels (no other types slip through)
  5. Chord detection accuracy on 5 known test songs is at or above 60% compared to manually verified chord sheets
**Plans**: 3 plans

Plans:
- [x] 03-01-PLAN.md -- Beat tracking via grid placement (numba workaround) and beat-synced chroma extraction
- [x] 03-02-PLAN.md -- Chord template matching (cosine similarity + Viterbi smoothing) with pipeline function
- [x] 03-03-PLAN.md -- Accuracy measurement utility, 18 structural tests, human-verified accuracy on Wild Horses.mp3

---

### Phase 4: Structural Segmentation
**Goal**: Song sections are auto-detected and labeled so the chord timeline is organized by musical structure
**Depends on**: Phase 3
**Requirements**: AUDIO-03
**Success Criteria** (what must be TRUE):
  1. The pipeline returns 2 or more labeled sections for any test song longer than 90 seconds
  2. Section boundaries fall on beat positions, not at arbitrary audio frames
  3. Default section labels (Verse, Chorus, Bridge or Section A, Section B) are assigned to each segment
  4. The `/analyze` endpoint returns a JSON response that includes a `sections` array with label, start time, and chord sequence per section
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md -- Create segmentation module (compute_k, segment_song, build_sections) with agglomerative clustering and 23 structural tests
- [x] 04-02-PLAN.md -- Add /analyze POST endpoint integrating chord detection + segmentation; validate with curl against Don't Cave.mp3

---

### Phase 5: Upload Handler and Async Processing
**Goal**: Users can submit an MP3 file through the web interface and receive processing feedback while the pipeline runs — the server does not hang
**Depends on**: Phase 4
**Requirements**: INPUT-01, INPUT-03
**Success Criteria** (what must be TRUE):
  1. User can select and upload an MP3 file from the browser UI (multipart form POST)
  2. Files larger than 50MB are rejected with a clear error message before processing begins
  3. Non-MP3 MIME types are rejected at upload with a clear error message
  4. The UI shows a progress message (e.g., "Analyzing audio...") while the backend is processing — the page does not freeze or appear broken
  5. The pipeline runs in a FastAPI threadpool (run_in_executor) — confirmed by server remaining responsive to a second request during processing
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md -- Add file validation (size + MIME) and threadpool offloading to /analyze endpoint
- [x] 05-02-PLAN.md -- Replace frontend scaffold with upload form, loading state, and result display

---

### Phase 6: Lyrics Input, Chart Builder, and API Contract
**Goal**: Users can paste lyrics into the interface and receive a structured ChartData JSON response that correctly aligns detected chords to the corresponding lyric lines by section
**Depends on**: Phase 5
**Requirements**: INPUT-02, INTG-01
**Success Criteria** (what must be TRUE):
  1. User can type or paste lyrics into a text area in the browser and submit them alongside the MP3
  2. The backend returns a ChartData JSON response containing sections, each with lyric lines and chord annotations positioned on those lines
  3. Chords are distributed across lyric lines proportionally — no section is left with all chords on one line while other lines have none
  4. The unique chord list in the response contains only the distinct chord names detected across the entire song (no duplicates)
  5. The Pydantic response model validates the ChartData structure and rejects malformed pipeline output with a 422 before it reaches the frontend
**Plans**: TBD

Plans:
- [ ] 06-01: Define Pydantic models (ChartData, Section, LyricLine, ChordAnnotation) as the backend-frontend API contract
- [ ] 06-02: Implement chart_builder.build() with line-count heuristic alignment of chord timestamps to lyric lines by section
- [ ] 06-03: Add lyrics textarea to frontend form and wire full multipart POST (MP3 + lyrics) to /analyze endpoint

---

### Phase 7: Chord Chart Display
**Goal**: Users see their chord chart rendered in Ultimate Guitar format in the browser — chords positioned above the correct syllables, sections labeled, key shown in the header
**Depends on**: Phase 6
**Requirements**: DISP-01, DISP-02
**Success Criteria** (what must be TRUE):
  1. Each song section appears with its label ([Verse], [Chorus], [Bridge]) as a header above its lyrics
  2. Chord names appear on a line directly above the lyric line, horizontally positioned over the syllable where the chord change occurs
  3. The detected song key is displayed in the chart header (e.g., "Key: G major")
  4. The chart renders correctly in a standard desktop browser (Chrome or Firefox) without horizontal overflow or overlapping chord names
**Plans**: TBD

Plans:
- [ ] 07-01: Integrate ChordSheetJS 14.0.0 via npm/Vite and confirm chord-above-lyric layout with hardcoded ChordPro test data
- [ ] 07-02: Wire chart display to live /analyze API response: render sections, labels, and chord positions from ChartData JSON
- [ ] 07-03: Add chart header (key, tempo) and verify section labels render correctly for all returned section types

---

### Phase 8: Chord Fingering Diagrams
**Goal**: Users see a guitar fingering diagram for every unique chord used in the song, generated client-side from the unique_chords list
**Depends on**: Phase 7
**Requirements**: DISP-03
**Success Criteria** (what must be TRUE):
  1. A fingering diagram appears for each unique chord in the song — no chord in the chart is missing a diagram
  2. Diagrams render as clean SVG elements in the browser (no broken images, no canvas fallback)
  3. Barre chord diagrams display the barre indicator (horizontal line across strings) correctly
  4. For any chord name that svguitar cannot render, a graceful fallback (e.g., "diagram unavailable") is shown rather than a JavaScript error
**Plans**: TBD

Plans:
- [ ] 08-01: Integrate svguitar 2.5.1 via npm/Vite and render test diagrams for a known set of chords (C, G, Am, E7)
- [ ] 08-02: Wire diagram rendering to the unique_chords list from the API response; implement fallback for unrecognized chords
- [ ] 08-03: Layout and style the diagrams section below or alongside the chord chart; confirm no visual conflicts with chart display

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Scaffold | 2/2 | Complete | 2026-03-03 |
| 2. Audio Loading and Key Detection | 2/2 | Complete | 2026-03-04 |
| 3. Beat Tracking and Chord Detection | 3/3 | Complete | 2026-03-04 |
| 4. Structural Segmentation | 2/2 | Complete | 2026-03-04 |
| 5. Upload Handler and Async Processing | 2/2 | Complete | 2026-03-04 |
| 6. Lyrics Input, Chart Builder, and API Contract | 0/3 | Not started | - |
| 7. Chord Chart Display | 0/3 | Not started | - |
| 8. Chord Fingering Diagrams | 0/3 | Not started | - |
