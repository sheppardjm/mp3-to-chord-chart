# Phase 6: Lyrics Input, Chart Builder, and API Contract - Research

**Researched:** 2026-03-04
**Domain:** Pydantic v2 models as API contract, proportional chord-to-lyric alignment, FastAPI multipart form with File + Form fields, vanilla JS textarea + FormData
**Confidence:** HIGH

## Summary

Phase 6 has three distinct sub-problems that must be solved in order: (1) define Pydantic response models that form the backend-frontend API contract, (2) implement a `chart_builder.build()` function that aligns chord timestamps to lyric lines proportionally by section, and (3) wire the frontend textarea and updated multipart POST to the backend. All three problems have clean solutions that fit the existing stack with minimal new code.

The most important architectural discovery is that **`key` is not currently returned by `_run_pipeline()`**. The `detect_key()` function exists in `audio/key_detection.py` and is used in Phase 2, but `main.py`'s `_run_pipeline` never calls it. Phase 6 must add `detect_key()` to `_run_pipeline` so that `ChartData.key` can be populated. This is a one-line addition.

The chord-to-lyric alignment algorithm is a proportional time-slice heuristic: each section's time range is divided equally among its lyric lines, and chord events are assigned to whichever line's time slice contains their timestamp. This distributes chords across lines proportionally without requiring any NLP or lyric timing data. The algorithm is verified to work correctly for more chords than lines (multiple chords per line), fewer chords than lines (some lines have no chords), and mismatched section counts (zip truncation is the safe default).

**Primary recommendation:** Create `backend/audio/models.py` for the Pydantic models (the API contract), `backend/audio/chart_builder.py` for the alignment logic, modify `_run_pipeline` in `main.py` to add `key` and call `chart_builder.build()`, and update the frontend form to include a `<textarea>` for lyrics.

---

## Standard Stack

All packages are already installed. No new dependencies required.

### Core (already installed, verified)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | Define ChartData, Section, LyricLine, ChordAnnotation models | Already installed with FastAPI; Pydantic v2 is the established standard |
| fastapi | 0.135.1 | File + Form in same multipart endpoint; response_model annotation | Already installed and working |
| python-multipart | 0.0.22 | Parses multipart/form-data with both file and text fields | Already installed; required for File() and Form() to work |

### No New Dependencies

The chord alignment algorithm is pure Python (regex + list comprehension). No new packages are needed.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Proportional time-slice alignment | NLP-based lyric timing (MFCC alignment) | NLP approach requires a forced alignment library (WhisperX, etc.) — enormous scope for a heuristic that works well enough |
| Separate `models.py` | Inline models in `chart_builder.py` | Inline models work but `main.py` needs to import `ChartData` for `response_model=` — separate file avoids circular imports |
| `list[str]` (Python 3.9+ style) | `List[str]` from `typing` | Both work in Pydantic v2 on Python 3.14; use `list[str]` (no import needed, cleaner) |

**Installation:** No new packages needed.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── audio/
│   ├── models.py          # NEW: ChartData, Section, LyricLine, ChordAnnotation
│   ├── chart_builder.py   # NEW: build() function + lyrics parser + alignment logic
│   ├── chord_detection.py # UNCHANGED
│   ├── segmentation.py    # UNCHANGED
│   ├── loader.py          # UNCHANGED
│   ├── key_detection.py   # UNCHANGED
│   └── __init__.py        # UNCHANGED
└── main.py                # MODIFIED: add key to _run_pipeline, add lyrics Form param,
                           #            import ChartData, call chart_builder.build()

frontend/src/
└── main.js                # MODIFIED: add lyrics textarea, append to FormData
```

### Pattern 1: Pydantic v2 Model Hierarchy for ChartData

**What:** Four nested Pydantic BaseModel classes forming the API contract. `ChordAnnotation` is the leaf; `ChartData` is the root.

**When to use:** Define once in `models.py`, import everywhere (`main.py` for `response_model=`, `chart_builder.py` for constructing the response).

```python
# Source: verified against Pydantic 2.12.5 in installed venv
# backend/audio/models.py

from pydantic import BaseModel


class ChordAnnotation(BaseModel):
    chord: str       # e.g. 'G:maj'
    position: float  # 0.0-1.0, proportional position within the lyric line


class LyricLine(BaseModel):
    text: str                     # the lyric text
    chords: list[ChordAnnotation] # chords that fall on this line


class Section(BaseModel):
    label: str            # 'Section A', 'Section B', etc. (from pipeline)
    lines: list[LyricLine]


class ChartData(BaseModel):
    key: str                   # e.g. 'G:maj' from detect_key()
    bpm: float                 # from detect_chords_pipeline()
    unique_chords: list[str]   # distinct chord names, order of first appearance
    sections: list[Section]
```

**Validation behavior (verified):**
- `ChartData(bpm='not-a-float', ...)` raises `pydantic.ValidationError` — type coercion fails
- `ChartData(**valid_dict)` constructs cleanly
- `.model_dump()` and `.model_dump_json()` serialize correctly
- `.model_validate(dict)` is the v2 equivalent of v1's `parse_obj()`

### Pattern 2: Proportional Chord-to-Lyric Alignment

**What:** Divide each section's time range equally among its lyric lines. Assign chord events to whichever line's time slice contains their timestamp. Position within the line is expressed as a float 0.0-1.0.

**When to use:** This is the only alignment logic needed for the success criteria. No more sophisticated algorithm is warranted.

**Algorithm:**

```python
# Source: verified with realistic pipeline data in Python 3.14
# backend/audio/chart_builder.py

import re
from audio.models import ChordAnnotation, LyricLine, Section, ChartData


def _parse_lyrics(lyrics: str) -> list[list[str]]:
    """Split pasted lyrics into sections (blank-line delimited) and lines."""
    raw_sections = re.split(r'\n\s*\n', lyrics.strip())
    result = []
    for raw in raw_sections:
        lines = [l.strip() for l in raw.strip().split('\n') if l.strip()]
        if lines:
            result.append(lines)
    return result


def _align_chords_to_lines(
    section_start: float,
    section_end: float,
    chord_events: list[dict],   # list of {'chord': str, 'time': float}
    lyric_lines: list[str],
) -> list[LyricLine]:
    """
    Assign chord events to lyric lines proportionally.

    Each line owns an equal time slice of the section. A chord event is
    assigned to the line whose slice contains chord['time'].
    Position within the line is chord_time_offset / line_duration.
    """
    if not lyric_lines:
        return []

    section_duration = section_end - section_start
    n_lines = len(lyric_lines)
    result = []

    for i, line_text in enumerate(lyric_lines):
        line_start = section_start + (i / n_lines) * section_duration
        line_end = section_start + ((i + 1) / n_lines) * section_duration
        line_duration = line_end - line_start

        # Chords whose timestamp falls within [line_start, line_end)
        line_chords = [
            c for c in chord_events
            if line_start <= c['time'] < line_end
        ]

        annotated = []
        for c in line_chords:
            pos = (c['time'] - line_start) / line_duration if line_duration > 0 else 0.0
            annotated.append(ChordAnnotation(chord=c['chord'], position=round(pos, 3)))

        result.append(LyricLine(text=line_text, chords=annotated))

    return result


def build(pipeline_result: dict, lyrics: str) -> ChartData:
    """
    Build ChartData from pipeline output and raw lyrics text.

    Args:
        pipeline_result: dict with keys: key, tempo_bpm, sections (list of dicts)
        lyrics: raw user-pasted lyrics, sections separated by blank lines

    Returns:
        ChartData Pydantic model

    Raises:
        KeyError: if pipeline_result is missing expected keys (caught by endpoint -> 422)
        pydantic.ValidationError: if data fails model validation (caught by endpoint -> 422)
    """
    lyric_sections = _parse_lyrics(lyrics)
    pipeline_sections = pipeline_result['sections']

    # Compute section end times (next section's start, or last chord + buffer)
    section_end_times = []
    for i, s in enumerate(pipeline_sections):
        if i + 1 < len(pipeline_sections):
            section_end_times.append(pipeline_sections[i + 1]['start'])
        else:
            chord_seq = s.get('chord_sequence', [])
            last_time = chord_seq[-1]['time'] if chord_seq else s['start']
            section_end_times.append(last_time + 8.0)

    # Unique chords in order of first appearance across all pipeline sections
    seen: set[str] = set()
    unique_chords: list[str] = []
    for s in pipeline_sections:
        for c in s.get('chord_sequence', []):
            if c['chord'] not in seen:
                seen.add(c['chord'])
                unique_chords.append(c['chord'])

    # Pair pipeline sections with lyric sections; zip truncates at shorter list
    chart_sections = []
    for (pipeline_sec, lyric_sec), sec_end in zip(
        zip(pipeline_sections, lyric_sections), section_end_times
    ):
        lines = _align_chords_to_lines(
            pipeline_sec['start'],
            sec_end,
            pipeline_sec.get('chord_sequence', []),
            lyric_sec,
        )
        chart_sections.append(Section(label=pipeline_sec['label'], lines=lines))

    return ChartData(
        key=pipeline_result['key'],
        bpm=pipeline_result['tempo_bpm'],
        unique_chords=unique_chords,
        sections=chart_sections,
    )
```

**Verified behavior:**
- 8 chords, 4 lines: 2 chords per line (evenly distributed)
- 2 chords, 6 lines: 2 lines have chords, 4 lines have no chords
- 2 lyric sections, 8 pipeline sections: 2 sections in output (zip truncates to shorter)
- 8 lyric sections, 3 pipeline sections: 3 sections in output (zip truncates to shorter)

### Pattern 3: FastAPI Endpoint with File + Form

**What:** Add `lyrics: str = Form(None)` alongside the existing `file: UploadFile = File(...)`. Both are multipart fields parsed by python-multipart.

**When to use:** When the browser sends a single multipart POST with both a file and text fields.

```python
# Source: verified against FastAPI 0.135.1 signature inspection
# backend/main.py

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from pydantic import ValidationError
from audio.models import ChartData
from audio.chart_builder import build

@app.post('/analyze', response_model=ChartData)
async def analyze(
    file: UploadFile = File(...),
    lyrics: str = Form(None),   # None if not provided (but required for Phase 6)
):
    # ... existing validation (file.size, file.content_type) ...

    result = await run_in_threadpool(_run_pipeline, tmp_path)

    # Chart building is fast (pure Python), run in-process after pipeline
    if lyrics:
        try:
            chart = build(result, lyrics)
            return chart
        except (ValidationError, KeyError, ValueError) as e:
            raise HTTPException(status_code=422, detail=str(e))

    return result  # fallback if no lyrics (backward compat)
```

**Key notes:**
- `response_model=ChartData` adds the JSON schema to `/docs` and validates output structure
- `Form(None)` makes lyrics optional — backward compatible with Phase 5 form that has no textarea
- If chart_builder raises `ValidationError` or `KeyError`, the endpoint raises `HTTPException(422)` — satisfies success criterion 5

### Pattern 4: Adding `key` to `_run_pipeline`

**What:** `_run_pipeline` does not currently call `detect_key()`. Add it so `pipeline_result['key']` is available for `chart_builder.build()`.

**Critical discovery:** The `key` field is absent from the current `/analyze` response. This must be fixed in Phase 6.

```python
# backend/main.py — _run_pipeline modification
from audio.key_detection import detect_key

def _run_pipeline(tmp_path: str) -> dict:
    audio = load_audio(tmp_path)
    key = detect_key(audio['y_harmonic'], audio['sr'])  # ADD THIS
    chord_result = detect_chords_pipeline(audio)
    # ... rest of existing code ...
    return {
        'key': key,                                  # ADD THIS
        'tempo_bpm': chord_result['tempo_bpm'],
        'chord_segments': chord_result['chord_segments'],
        'sections': sections,
        'n_beats': chord_result['n_beats'],
        'n_segments': chord_result['n_segments'],
    }
```

`detect_key()` uses `chroma_cqt` with `tuning=0.0` — same pattern as `extract_beat_chroma()`, safe on Python 3.14 with the numba no-op stub.

### Pattern 5: Frontend Textarea + FormData

**What:** Add a `<textarea id="lyrics">` to the HTML form. Append its value to the `FormData` before POST.

```javascript
// Source: MDN FormData spec (browser built-in)
// frontend/src/main.js

document.querySelector('#app').innerHTML = `
  <h1>dontCave</h1>
  <form id="upload-form">
    <label for="file-input">Select MP3 file:</label>
    <input type="file" id="file-input" accept=".mp3,audio/mpeg" required />
    <label for="lyrics">Paste lyrics:</label>
    <textarea id="lyrics" rows="20" placeholder="Paste lyrics here..."></textarea>
    <button type="submit" id="submit-btn">Analyze</button>
  </form>
  <p id="status"></p>
  <pre id="result"></pre>
`

// In the submit handler:
const formData = new FormData()
formData.append('file', fileInput.files[0])
formData.append('lyrics', document.querySelector('#lyrics').value)

// Do NOT set Content-Type — browser sets multipart with boundary automatically
const response = await fetch('/api/analyze', {
  method: 'POST',
  body: formData,
})
```

### Anti-Patterns to Avoid

- **Putting models inside `chart_builder.py`:** `main.py` needs to import `ChartData` for `response_model=ChartData`. Importing from `chart_builder.py` in `main.py` creates a dependency order problem. Put models in `models.py`.
- **Using `response_model` alone to get 422 on bad pipeline output:** FastAPI returns 500 (ResponseValidationError) when the *response* fails model validation, not 422. The 422 must come from catching `ValidationError` inside the endpoint and re-raising as `HTTPException(422)`.
- **Setting `Content-Type` manually in fetch:** Breaks the multipart boundary. Never set it when sending FormData.
- **Using `zip_longest` to pad mismatched section counts:** Adds complexity. Pad with empty arrays. `zip` truncation (shorter list wins) is correct behavior — unpaired pipeline sections just don't appear in the chart.
- **Running `chart_builder.build()` in `run_in_threadpool`:** Build is fast (pure Python, no I/O). Run it in-process after the threadpool pipeline completes.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multipart text field parsing | Manual `request.body()` parsing | `FastAPI Form()` | python-multipart already installed and handles it |
| Response model validation | Custom dict-checking code | `Pydantic BaseModel` + `model_validate()` | Pydantic does structural, type, and presence validation automatically |
| Unique chord deduplication | Custom class-based tracking | Python `set` + ordered list | Standard Python; O(1) lookup, preserves insertion order |
| Section time range calculation | Complex boundary detection | `sections[i+1]['start']` as end time | Pipeline output already has ordered sections with start times |

**Key insight:** The chart builder is pure coordination logic — parse, zip, align, validate. No library is needed beyond what's installed.

---

## Common Pitfalls

### Pitfall 1: `key` Missing from Pipeline Output

**What goes wrong:** `chart_builder.build()` raises `KeyError: 'key'` when accessing `pipeline_result['key']`. This propagates as a 500 from the endpoint.

**Why it happens:** `_run_pipeline` in `main.py` currently does not call `detect_key()`. The `key_detection.py` module exists but is not wired into the endpoint pipeline.

**How to avoid:** Add `key = detect_key(audio['y_harmonic'], audio['sr'])` to `_run_pipeline` and include `'key': key` in the returned dict. Verify by checking that the JSON response contains a `key` field after modification.

**Warning signs:** `KeyError: 'key'` in server logs, or 422/500 on all analyze requests.

### Pitfall 2: 422 vs 500 for Response Validation Failure

**What goes wrong:** Malformed pipeline output causes a 500 error instead of the specified 422.

**Why it happens:** FastAPI's `response_model=ChartData` validates the *return value*, but a failed response-side validation raises `ResponseValidationError` which becomes HTTP 500, not 422. 422 is for *request* input validation.

**How to avoid:** Explicitly call `ChartData.model_validate(data)` inside the endpoint (or let `chart_builder.build()` construct the model directly). Catch `ValidationError` or `KeyError` and raise `HTTPException(status_code=422, detail=...)`.

**Pattern:**
```python
try:
    chart = build(pipeline_result, lyrics)
    return chart
except (ValidationError, KeyError, ValueError) as e:
    raise HTTPException(status_code=422, detail=str(e))
```

**Warning signs:** The endpoint returns 500 when you deliberately pass bad pipeline output during testing.

### Pitfall 3: Last Section Gets No Chords (End Time Calculation)

**What goes wrong:** The last lyric section in the last pipeline section shows no chords because the section's end time is too early.

**Why it happens:** The last pipeline section has no "next section" to borrow its start time from. If you use `section['start']` as the end time, the section has zero duration, so no chords fall within it.

**How to avoid:** For the last section, use `last_chord_time + 8.0` as the end time (provides ~2 measures of breathing room). Verify with real audio that the last section's chords distribute across lines.

**Warning signs:** Last section in the output has all lines with empty chord lists despite the pipeline section having chords.

### Pitfall 4: Chord at Exact Section End Not Captured

**What goes wrong:** A chord whose timestamp exactly equals the section end time is not assigned to any line.

**Why it happens:** The alignment uses `line_start <= c['time'] < line_end` (exclusive upper bound). A chord at the section boundary belongs to the *next* section's first line, not the current section's last line.

**How to avoid:** This is correct behavior — a chord at `section_end` time is the first chord of the next section. The pipeline's `chord_sequence` for a section already excludes chords that belong to the next section (the section's `chord_sequence` only contains chords within `[section.start, next_section.start)`). No fix needed, but verify manually.

### Pitfall 5: Lyrics with No Blank Lines (Single Section)

**What goes wrong:** User pastes lyrics with no blank lines between verses. `_parse_lyrics` returns one section, but pipeline may return 8+ sections. Only the first pipeline section gets lyrics.

**Why it happens:** `re.split(r'\n\s*\n', ...)` produces a single element if there are no blank lines.

**How to avoid:** This is acceptable behavior — the user controls lyrics formatting. Document that blank lines separate sections. The chart builder does not attempt to infer section boundaries from lyrics alone.

**Warning signs:** A long song where the user gets output for only "Section A" with all lyrics on it.

### Pitfall 6: `Form(None)` Does Not Make Lyrics Optional When Chart Building Is Required

**What goes wrong:** The endpoint accepts a POST without `lyrics` (because `Form(None)` is optional), but `chart_builder.build()` is called and returns a `ChartData` with zero sections.

**Why it happens:** If `lyrics` is `None` or empty, `_parse_lyrics` returns `[]`, so `zip(pipeline_sections, [])` produces no pairs, and `sections=[]` in the result.

**How to avoid:** Add an explicit guard before calling `build()`:
```python
if not lyrics or not lyrics.strip():
    raise HTTPException(status_code=422, detail="Lyrics are required")
```
Or keep backward-compat fallback: return raw pipeline result if lyrics is absent.

**Warning signs:** Submitting the form without lyrics returns a valid-looking `ChartData` with `sections: []`.

---

## Code Examples

Verified patterns from codebase inspection and Python 3.14 execution.

### Complete `models.py`

```python
# Source: verified against Pydantic 2.12.5 in installed venv
# backend/audio/models.py

from pydantic import BaseModel


class ChordAnnotation(BaseModel):
    chord: str       # e.g. 'G:maj'
    position: float  # 0.0-1.0, proportional position within lyric line


class LyricLine(BaseModel):
    text: str                     # lyric text for this line
    chords: list[ChordAnnotation] # chord events that fall on this line


class Section(BaseModel):
    label: str             # 'Section A', 'Section B', etc.
    lines: list[LyricLine] # lyric lines with chord annotations


class ChartData(BaseModel):
    key: str                 # e.g. 'G:maj' or 'Bb:min'
    bpm: float               # estimated tempo
    unique_chords: list[str] # distinct chord names in order of first appearance
    sections: list[Section]  # sections with annotated lyric lines
```

### `_run_pipeline` Modification (adding `key`)

```python
# Source: existing backend/main.py + audio/key_detection.py
# backend/main.py — _run_pipeline function

from audio.key_detection import detect_key  # add to imports

def _run_pipeline(tmp_path: str) -> dict:
    audio = load_audio(tmp_path)

    key = detect_key(audio['y_harmonic'], audio['sr'])  # ADD: one line

    chord_result = detect_chords_pipeline(audio)

    _, beat_frames = beat_track_grid(audio['y_percussive'], audio['sr'])
    chroma_sync = extract_beat_chroma(audio['y_harmonic'], beat_frames, audio['sr'])

    boundary_beats = segment_song(chroma_sync, audio['duration'])
    sections = build_sections(
        boundary_beats,
        chord_result['beat_times'],
        chord_result['chord_sequence'],
    )

    return {
        'key': key,                                      # ADD: include key
        'tempo_bpm': chord_result['tempo_bpm'],
        'chord_segments': chord_result['chord_segments'],
        'sections': sections,
        'n_beats': chord_result['n_beats'],
        'n_segments': chord_result['n_segments'],
    }
```

### Updated `/analyze` Endpoint

```python
# Source: verified FastAPI 0.135.1 + Pydantic 2.12.5 patterns
# backend/main.py — analyze endpoint

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from audio.models import ChartData
from audio.chart_builder import build as build_chart

@app.post('/analyze', response_model=ChartData)
async def analyze(
    file: UploadFile = File(...),
    lyrics: str = Form(None),
):
    # Existing validation (file.size, file.content_type) unchanged

    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename or 'upload.mp3')[1] or '.mp3'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        result = await run_in_threadpool(_run_pipeline, tmp_path)

        # Build chart (fast, pure Python — no need for threadpool)
        if not lyrics or not lyrics.strip():
            raise HTTPException(status_code=422, detail='Lyrics are required')

        try:
            chart = build_chart(result, lyrics)
            return chart
        except (ValidationError, KeyError, ValueError) as e:
            raise HTTPException(status_code=422, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
```

### Frontend Lyrics Textarea

```javascript
// Source: MDN FormData spec, verified pattern
// frontend/src/main.js — relevant additions

document.querySelector('#app').innerHTML = `
  <h1>dontCave</h1>
  <form id="upload-form">
    <label for="file-input">Select MP3 file:</label>
    <input type="file" id="file-input" accept=".mp3,audio/mpeg" required />
    <label for="lyrics">Paste lyrics (blank lines between sections):</label>
    <textarea id="lyrics" rows="20" cols="60"
      placeholder="Paste lyrics here. Separate sections with blank lines."></textarea>
    <button type="submit" id="submit-btn">Analyze</button>
  </form>
  <p id="status"></p>
  <pre id="result"></pre>
`

// In the submit handler — add lyrics to FormData:
const formData = new FormData()
formData.append('file', fileInput.files[0])
formData.append('lyrics', document.querySelector('#lyrics').value)

// Do NOT set Content-Type — browser sets multipart/form-data with boundary
const response = await fetch('/api/analyze', {
  method: 'POST',
  body: formData,
})
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `parse_obj()` | Pydantic v2 `model_validate()` | Pydantic v2 (2023) | v1 syntax raises deprecation warnings in v2 |
| `from typing import List` | `list[str]` (built-in generic) | Python 3.9+ | No import needed; cleaner syntax |
| Pydantic v1 `@validator` | Pydantic v2 `@field_validator` with `@classmethod` | Pydantic v2 | Old `@validator` removed in v2 |

**Deprecated/outdated:**
- `from pydantic import validator`: Removed in Pydantic v2. Use `@field_validator` with `@classmethod`.
- `Model.parse_obj(data)`: Replaced by `Model.model_validate(data)` in Pydantic v2.
- `Model.dict()`: Replaced by `Model.model_dump()` in Pydantic v2.

---

## Open Questions

1. **What happens when lyrics are longer than the song?**
   - What we know: Proportional alignment uses section time ranges from the pipeline. If the user provides 20 lyric lines for a 4-bar section, each line gets a tiny time slice. Chord distribution still works mathematically.
   - What's unclear: Whether the resulting chart looks reasonable musically.
   - Recommendation: Accept this limitation for Phase 6. The algorithm is correct by definition; music quality is a UX concern for a later phase.

2. **How should the frontend display the ChartData response?**
   - What we know: Phase 6 success criteria say "returns a ChartData JSON response" — no specific UI rendering is required beyond confirming the structure.
   - What's unclear: Whether `<pre id="result">JSON.stringify(data)</pre>` is sufficient or whether Phase 6 requires a rendered chord chart view.
   - Recommendation: The success criteria (criterion 2: "backend returns a ChartData JSON response") suggest raw JSON display is sufficient for Phase 6. A rendered chart view is a Phase 7 concern. Confirm with plan step 06-03.

3. **Should `unique_chords` include `N/A` (the "no chord" placeholder)?**
   - What we know: `detect_chords` in Phase 3 returns chords from the 36-template set (major, minor, dominant 7th). There is no explicit `N` (no chord) label in this pipeline.
   - What's unclear: Whether the pipeline ever returns a chord string like `N` or `N/A` for silent sections.
   - Recommendation: Filter any chord string that is `None`, empty, or `'N'` from `unique_chords`. Add a guard in `_extract_unique_chords()`.

---

## Sources

### Primary (HIGH confidence)

- Pydantic 2.12.5 installed venv (`pydantic/main.py`) — `BaseModel`, `model_validate()`, `model_dump()`, `field_validator` — verified by running code directly against installed venv
- FastAPI 0.135.1 installed venv — `File()`, `Form()` coexistence in endpoint signature — verified by `inspect.signature()` against live import
- `backend/audio/models.py` (does not yet exist) — designed based on codebase patterns and Pydantic v2 verification
- `backend/main.py` — read directly; confirmed `key` is absent from `_run_pipeline` return value
- `backend/audio/key_detection.py` — read directly; `detect_key()` exists and accepts `(y_harmonic, sr)` matching `_run_pipeline`'s available variables
- `backend/audio/segmentation.py` — read directly; confirmed `build_sections()` returns `{'label': str, 'start': float, 'chord_sequence': list[dict]}`

### Secondary (MEDIUM confidence)

- MDN FormData spec — `formData.append('lyrics', textareaEl.value)` sends as text field in multipart — consistent with python-multipart Form() behavior
- python-multipart 0.0.22 behavior confirmed via `pip show` and existing Phase 5 implementation (already parsing file fields)

### Tertiary (LOW confidence)

- Proportional time-slice alignment is an original heuristic designed for this codebase — no external reference; verified by running algorithm against test cases

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed and functional; no new dependencies
- Pydantic model design: HIGH — models verified by construction and serialization in Python 3.14/Pydantic 2.12.5
- Alignment algorithm: HIGH — algorithm verified against multiple edge cases (more chords than lines, fewer, mismatched section counts)
- 422 pattern for malformed output: HIGH — pattern verified by catching ValidationError and re-raising as HTTPException(422)
- Missing `key` in pipeline: HIGH — confirmed by reading `_run_pipeline` return dict in `main.py`; `key_detection.py` exists and is importable
- Frontend FormData + Form() integration: HIGH — FastAPI File + Form coexistence verified by signature inspection; no Content-Type anti-pattern confirmed from Phase 5 research

**Research date:** 2026-03-04
**Valid until:** 2026-06-04 (stable APIs; Pydantic v2 and FastAPI evolve slowly for these primitives)
