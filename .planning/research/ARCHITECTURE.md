# Architecture Research

**Domain:** MP3-to-chord-chart web application (audio analysis pipeline)
**Researched:** 2026-03-03
**Confidence:** MEDIUM-HIGH (architecture derived from documented patterns in librosa, ChordMiniApp reference implementation, and MIR literature; specific chord detection accuracy numbers LOW confidence)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BROWSER (Frontend)                            │
├───────────────────────────┬─────────────────────────────────────────┤
│  Upload UI                │  Chart Display UI                        │
│  ┌────────────────┐       │  ┌──────────────────┐ ┌──────────────┐  │
│  │  File Picker   │       │  │  Chord Chart View│ │ Fingering    │  │
│  │  Lyrics Input  │       │  │  (lyrics + chords)│ │ Diagrams     │  │
│  └───────┬────────┘       │  └──────────────────┘ └──────────────┘  │
│          │ POST multipart │                                          │
└──────────┼────────────────┴─────────────────────────────────────────┘
           │ HTTP REST
┌──────────▼────────────────────────────────────────────────────────┐
│                    BACKEND (Python / FastAPI)                       │
├────────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐   ┌──────────────────┐   ┌───────────────────┐  │
│  │ Upload Handler│──▶│ Audio Pipeline   │──▶│ Chart Builder     │  │
│  │ (validation,  │   │ (librosa-based,  │   │ (chord→lyric      │  │
│  │  temp storage)│   │  see stages below)│   │  alignment,       │  │
│  └───────────────┘   └──────────────────┘   │  JSON response)   │  │
│                                              └───────────────────┘  │
├────────────────────────────────────────────────────────────────────┤
│                    Audio Analysis Pipeline (Core)                    │
│                                                                      │
│  [MP3 bytes]                                                         │
│       ↓ Stage 1: Load & Decode                                       │
│  [audio array, sr=22050Hz]                                           │
│       ↓ Stage 2: Key Detection                                       │
│  [estimated key]                                                      │
│       ↓ Stage 3: Beat Tracking                                       │
│  [beat timestamps]                                                    │
│       ↓ Stage 4: Chroma Feature Extraction                           │
│  [12-dim chroma vectors, beat-synchronized]                          │
│       ↓ Stage 5: Chord Classification                                │
│  [chord label per beat]                                              │
│       ↓ Stage 6: Structural Segmentation                             │
│  [section boundaries + labels]                                       │
│       ↓ Stage 7: Chord Simplification                                │
│  [deduplicated chord sequence per section]                           │
└────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Upload Handler | Receive multipart form (MP3 + lyrics text), validate MIME type and size, write to temp file, trigger pipeline | Audio Pipeline |
| Audio Pipeline | Orchestrate all librosa analysis stages in order, return structured result dict | Upload Handler (caller), Chart Builder |
| Key Detector | Estimate musical key (tonal center) using `librosa.estimate_tuning` + chroma profiles | Audio Pipeline |
| Beat Tracker | Detect tempo and beat frame positions via `librosa.beat.beat_track` | Audio Pipeline |
| Chroma Extractor | Compute 12-dim pitch class energy per beat via `librosa.feature.chroma_cqt` + `librosa.util.sync` | Audio Pipeline |
| Chord Classifier | Match each beat's chroma vector against major/minor/7th templates via cosine similarity | Audio Pipeline |
| Section Segmenter | Detect structural boundaries (verse/chorus etc.) via Laplacian segmentation (`librosa.segment.*`) | Audio Pipeline |
| Chord Simplifier | Collapse repeated adjacent chords, deduplicate within beats to produce section-level chord lists | Audio Pipeline |
| Chart Builder | Align chord sequence with user-provided lyric lines (word count or line heuristic), produce JSON chart structure | Upload Handler |
| Chart Display UI | Render chord names above lyric lines in UG-style layout, organized by section | Backend REST API |
| Fingering Diagram UI | Render SVG guitar chord diagrams using svguitar.js, keyed from unique chord set in chart | Chart Display UI |

## Recommended Project Structure

```
dontCave/
├── backend/
│   ├── main.py                 # FastAPI app entry point, route definitions
│   ├── api/
│   │   └── routes.py           # POST /analyze endpoint
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── loader.py           # Stage 1: audio loading, MP3 decode
│   │   ├── key_detection.py    # Stage 2: key estimation
│   │   ├── beat_tracker.py     # Stage 3: beat positions
│   │   ├── chroma.py           # Stage 4: chroma feature extraction
│   │   ├── chord_classifier.py # Stage 5: template matching, chord labels
│   │   ├── segmenter.py        # Stage 6: structural section detection
│   │   └── simplifier.py       # Stage 7: deduplication, chord sequence
│   ├── chart/
│   │   ├── __init__.py
│   │   ├── builder.py          # Align chords + lyrics → chart dict
│   │   └── models.py           # Pydantic models: ChartSection, ChordEntry
│   ├── templates/
│   │   └── chord_templates.py  # Static major/minor/7th chroma templates
│   └── requirements.txt
├── frontend/
│   ├── index.html              # Upload form
│   ├── chart.html              # Chart display page
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── upload.js           # Form submit → POST → redirect with result
│       ├── chart.js            # Render chart sections, chord lines
│       └── diagrams.js         # svguitar.js calls, chord fingering lookup
└── .planning/
```

### Structure Rationale

- **pipeline/:** Each stage is a separate module. This makes unit testing per-stage straightforward and allows swapping individual stages (e.g., replacing template matching with a neural model) without touching the rest.
- **chart/:** Separated from pipeline because chart building is a pure data-transformation concern (no audio signal processing). Has its own Pydantic models for the JSON contract.
- **templates/:** Static Python file containing the 36-chord template matrix (12 major + 12 minor + 12 dominant 7th). No database needed for MVP.
- **frontend/js split:** upload.js and chart.js are separate; upload triggers processing, chart.html receives JSON via URL params or sessionStorage and renders independently.

## Architectural Patterns

### Pattern 1: Sequential Pipeline with Explicit Stage Contracts

**What:** Each pipeline stage receives the previous stage's output as a typed dict/dataclass and returns a typed dict/dataclass. The orchestrator (`pipeline/__init__.py`) calls stages in order and threads results through.

**When to use:** Always. This is the core structure. Audio analysis is inherently sequential — you cannot extract chroma without beats, cannot classify chords without chroma.

**Trade-offs:** Synchronous is simpler to implement and debug. For a personal one-shot tool, there is no need for async task queues (Celery/Redis). A 3-4 minute MP3 processes in approximately 5-15 seconds synchronously; acceptable for this use case.

**Example:**
```python
# pipeline/__init__.py
def run_pipeline(audio_path: str) -> dict:
    audio, sr = load_audio(audio_path)         # Stage 1
    key = detect_key(audio, sr)                 # Stage 2
    beats, tempo = track_beats(audio, sr)       # Stage 3
    chroma = extract_chroma(audio, sr, beats)   # Stage 4
    chords = classify_chords(chroma)            # Stage 5
    sections = segment_sections(audio, sr, beats, chords)  # Stage 6
    return simplify_chords(sections, chords)    # Stage 7
```

### Pattern 2: Template Matching Chord Classification

**What:** Pre-compute a 36x12 template matrix (36 chord types, 12 pitch classes). For each beat, compute cosine similarity between the beat's chroma vector and each template. The template with highest similarity is the chord label.

**When to use:** MVP. Adequate for basic major/minor/7th detection without ML dependencies. Well-documented, debuggable, deterministic.

**Trade-offs:** Lower accuracy than neural approaches (approximately 60-75% on polyphonic pop vs 85%+ for deep learning). Sufficient for the personal tool goal state. No GPU or model download required.

**Example:**
```python
# chord_classifier.py
import numpy as np

CHORD_TEMPLATES = {
    "C":  [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0],  # major triad
    "Cm": [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0],  # minor triad
    "C7": [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],  # dominant 7th
    # ... all 36 chords
}

def classify_chords(chroma_matrix: np.ndarray) -> list[str]:
    chord_labels = []
    for beat_chroma in chroma_matrix.T:
        best_chord = max(
            CHORD_TEMPLATES,
            key=lambda c: np.dot(beat_chroma, CHORD_TEMPLATES[c]) /
                         (np.linalg.norm(beat_chroma) + 1e-8)
        )
        chord_labels.append(best_chord)
    return chord_labels
```

### Pattern 3: Lyric Line to Section Alignment by Line Count

**What:** User pastes raw lyrics with blank lines separating sections. Backend splits lyrics into sections by blank line, then distributes the chord sequence across each section's lines proportionally.

**When to use:** MVP. No timestamp-level lyric alignment (that requires audio-lyrics forced alignment which adds significant complexity). Line-count heuristic gives workable results for a personal tool.

**Trade-offs:** Imprecise — chords will not always land on the right word. Good enough for a reference chart. The user knows the song; the chart is a guide, not a transcription.

## Data Flow

### Request Flow

```
User uploads MP3 + pastes lyrics text
    ↓
POST /analyze  (multipart/form-data: file=<mp3>, lyrics=<text>)
    ↓
Upload Handler
    - Validate: MIME type audio/mpeg, max 50MB
    - Write to /tmp/{uuid}.mp3
    - Parse lyrics text into raw string
    ↓
run_pipeline("/tmp/{uuid}.mp3")
    - Returns: {sections: [{label, beats, chords, timestamps}]}
    ↓
chart_builder.build(pipeline_result, lyrics_text)
    - Returns: ChartData JSON
        {
          key: "G",
          tempo: 120,
          unique_chords: ["G", "Em", "C", "D"],
          sections: [
            {
              label: "Verse 1",
              lines: [
                {lyric: "Here I am...", chords: [{chord: "G", word_position: 0}]},
                ...
              ]
            }
          ]
        }
    ↓
JSON response to browser
    ↓
chart.js renders sections as UG-style blocks
diagrams.js renders svguitar fingering diagram for each unique_chord
```

### Key Data Flows

1. **Audio → Chroma:** MP3 bytes decoded to float32 time-series at 22050 Hz. CQT computed. Chroma filter bank produces (12, T) matrix. Beat-synchronized to reduce (12, T) to (12, num_beats).

2. **Chroma → Chord labels:** (12, num_beats) matrix compared against 36 templates. Output is list of `num_beats` chord label strings (e.g., `["G", "G", "Em", "C", "D", "D", ...]`).

3. **Chord labels → Sections:** Structural boundaries from Laplacian segmentation divide the beat sequence into labeled segments. Within each segment, chord sequence is simplified (collapse repeats).

4. **Sections + Lyrics → Chart JSON:** Lyric text split by blank lines into user-defined sections. If user sections match structural sections in count, map 1:1. Otherwise, distribute chords across lyric lines by proportion. Output is the JSON structure the frontend renders.

5. **Chart JSON → Display:** `chart.js` iterates sections and lines, placing chord names as `<span>` elements above lyric text. `diagrams.js` renders SVG diagrams for the `unique_chords` list using svguitar.js.

## Scaling Considerations

This is a personal tool. Scaling is not a design goal. The relevant concerns are:

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user, personal tool | Synchronous processing in request handler. No queue. Temp files cleaned after response. |
| 10 users (shared among friends) | Add processing timeout (60s). Add temp file cleanup cron. FastAPI handles concurrent requests via async endpoints (pipeline called in threadpool). |
| 100+ users | Add Celery + Redis for background job queue, polling endpoint for status. Out of scope for this project. |

### First Bottleneck

Audio loading and CQT computation are the slowest steps. For a 4-minute MP3, expect 8-20 seconds total pipeline time on a modern laptop CPU. This is acceptable for a synchronous personal tool. Caching (file hash → result) can eliminate repeat processing if desired.

## Anti-Patterns

### Anti-Pattern 1: Doing Chord Classification Frame-by-Frame at Raw Sample Rate

**What people do:** Compute chroma at every audio frame (every ~23ms at 22050Hz with 512-sample hop), then classify a chord per frame.

**Why it's wrong:** Generates tens of thousands of chord labels for a 3-minute song. Most frames within a beat will agree, but noise at transitions creates flickering labels. Also slow — far more computation than needed.

**Do this instead:** Synchronize chroma to beat positions first (`librosa.util.sync`). This reduces from thousands of frames to ~100-200 beats per song, one chord per beat. Much cleaner signal.

### Anti-Pattern 2: Trying to Do Audio-Lyrics Forced Alignment in MVP

**What people do:** Attempt to align specific words in lyrics to audio timestamps using forced alignment tools (Montreal Forced Aligner, NeMo, etc.).

**Why it's wrong:** Forced alignment requires phoneme models, language-specific acoustic models, clean vocals, and substantial setup complexity. It is a separate research problem from chord detection. Adding it to MVP scope will stall the project.

**Do this instead:** Use the line-count heuristic (distribute chords proportionally across lyric lines). This is how most chord chart editors (e.g., ChordPro format) handle it — chords are annotated at the lyric-line level, not the word level.

### Anti-Pattern 3: Returning Raw Beat-Level Chords Without Simplification

**What people do:** Display every chord label for every beat in the chart output.

**Why it's wrong:** A chord that spans 4 beats shows up as "G G G G" which is noisy and redundant. UG-style charts show a chord label once per change, not once per beat.

**Do this instead:** Collapse adjacent duplicate chords within each section. Display only chord changes.

### Anti-Pattern 4: Storing Processed Audio in the Database

**What people do:** Store the decoded audio array or feature matrices in a database between pipeline stages.

**Why it's wrong:** Numpy arrays for a 4-minute song at 22050Hz are ~20MB. Storing these in a DB is wasteful, slow, and unnecessary for a one-shot flow.

**Do this instead:** Keep all intermediate arrays in-memory within the pipeline function. Only persist the temp MP3 file to disk (for librosa to read), then delete it after the pipeline completes. Return only the lightweight JSON chart structure.

## Integration Points

### External Libraries

| Library | Integration Pattern | Notes |
|---------|---------------------|-------|
| librosa 0.11.x | Import in pipeline modules; call directly in-process | No subprocess, no API call. Pure Python. |
| svguitar | npm package loaded via `<script>` in chart.html | Frontend-only. No backend dependency. Renders SVG in browser. |
| FastAPI | ASGI app serving REST endpoint + static files | Use `StaticFiles` mount for frontend assets. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Upload Handler ↔ Audio Pipeline | Direct Python function call; pipeline receives file path string | Pipeline is synchronous; FastAPI runs it in a threadpool via `run_in_executor` to avoid blocking the event loop |
| Audio Pipeline ↔ Chart Builder | Pipeline returns Python dict; Chart Builder receives dict, returns Pydantic model serialized to JSON | Pydantic model defines the API contract between backend and frontend |
| Backend ↔ Frontend | JSON over HTTP REST (single POST /analyze, returns 200 with chart JSON or 4xx/5xx error) | No WebSocket needed for one-shot flow |
| Chart JS ↔ Diagram JS | Chart JS calls diagram JS with list of unique chord names; diagram JS renders SVG panels | Simple function call interface; svguitar handles all SVG generation |

## Build Order (Dependencies)

Build components in this order to have testable pieces at each step:

1. **Stage 1-4 (Audio Loading → Chroma):** These are pure librosa calls. Build and test in a Jupyter notebook first. Verify chroma matrix shape and values before proceeding.

2. **Stage 5 (Chord Classifier):** Write template dict and cosine similarity function. Unit-testable with a known chroma vector (e.g., pure G major should score highest on G template).

3. **Stage 6 (Section Segmenter):** Most complex stage. Laplacian segmentation requires tuning `k` (number of sections). Build separately, test on known songs with clear structure (verse/chorus pop).

4. **Stage 7 (Simplifier) + Chart Builder:** Pure data transformation. Easiest to test. Build after pipeline produces chord+section data.

5. **FastAPI endpoint:** Wire the pipeline into the HTTP handler. Test with curl before building UI.

6. **Chart Display UI (HTML/CSS/JS):** Render hardcoded JSON first to confirm layout before wiring to live endpoint.

7. **Fingering Diagrams (svguitar):** Add last. Self-contained frontend enhancement; does not block core functionality.

## Sources

- librosa 0.11.0 documentation — Tutorial: https://librosa.org/doc/0.11.0/tutorial.html
- librosa Chroma and Tonal Features (DeepWiki): https://deepwiki.com/librosa/librosa/4.2-chroma-and-tonal-features
- librosa Laplacian Segmentation example: https://librosa.org/doc/main/auto_examples/plot_segmentation.html
- ChordMiniApp reference architecture (Next.js + Flask): https://github.com/ptnghia-j/ChordMiniApp
- Template-based chord recognition (MIR research): https://www.audiolabs-erlangen.de/resources/MIR/FMP/C5/C5S2_ChordRec_Templates.html
- Chord recognition by chroma template matching: https://www.researchgate.net/publication/325070280_Chord_Recognition_based_on_Template_Recognition
- svguitar library for SVG chord diagrams: https://github.com/omnibrain/svguitar
- FastAPI file upload handling: https://fastapi.tiangolo.com/tutorial/request-files/
- ChordPro format (lyric+chord alignment standard): https://www.chordpro.org/

---
*Architecture research for: MP3-to-chord-chart personal web tool*
*Researched: 2026-03-03*
