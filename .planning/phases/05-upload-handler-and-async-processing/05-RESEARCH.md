# Phase 5: Upload Handler and Async Processing - Research

**Researched:** 2026-03-04
**Domain:** FastAPI file upload validation, asyncio threadpool offloading, vanilla JS progress feedback
**Confidence:** HIGH

## Summary

Phase 5 wires the existing `/analyze` endpoint (built in Phase 4) to proper file validation and makes the server non-blocking during audio processing. Three distinct problems must be solved: (1) validate file size and MIME type before running the pipeline, (2) offload the CPU-bound pipeline to a threadpool so the event loop stays free, and (3) show a loading state in the browser so the page does not appear frozen during the 10-60 second processing window.

All three problems have well-established solutions that require no new dependencies. The backend uses `starlette.concurrency.run_in_threadpool` (already present in the installed stack) to offload blocking calls. File size validation uses `file.size` (populated by Starlette's multipart parser by the time the handler runs) checked against the 50MB limit, and MIME type validation uses `file.content_type`. The frontend uses vanilla JS `fetch` with `FormData`; a loading message is toggled before and after the `await fetch(...)` call.

**Primary recommendation:** Use `run_in_threadpool` from `starlette.concurrency` to wrap the synchronous pipeline call inside the `async def analyze` endpoint. Validate `file.size` and `file.content_type` immediately at the top of the handler, raising `HTTPException` with clear messages before any pipeline work starts.

---

## Standard Stack

All packages are already installed. No new dependencies are required for this phase.

### Core (already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.135.1 | HTTP framework, `UploadFile`, `HTTPException` | Already installed; confirmed working |
| starlette | (bundled with fastapi) | `run_in_threadpool`, `UploadFile` base | FastAPI builds on Starlette; `run_in_threadpool` is the idiomatic offload helper |
| python-multipart | 0.0.22 | Parses multipart/form-data uploads | Already installed; required for `UploadFile` to work |
| uvicorn | 0.41.0 | ASGI server running the event loop | Already installed; handles concurrency |

### Frontend (no new packages)

| Tool | Version | Purpose |
|------|---------|---------|
| Vite | 7.3.1 | Dev server with proxy to backend |
| vanilla JS Fetch API | browser built-in | POST FormData, await response, update DOM |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `run_in_threadpool` | `asyncio.get_running_loop().run_in_executor(None, fn)` | Both work; `run_in_threadpool` is shorter, Starlette-idiomatic, and already used internally by FastAPI for `def` endpoints. Prefer it. |
| `run_in_threadpool` | `asyncio.to_thread(fn, *args)` | Also valid (Python 3.9+); `run_in_threadpool` is already a dependency so prefer it for consistency |
| Checking `file.size` | Reading all bytes then checking `len(content)` | Reading all bytes first wastes memory on files that will be rejected; `file.size` is populated without extra reads |
| Checking `file.size` | Content-Length header validation | Header can be spoofed; `file.size` reflects actual bytes received after streaming is complete |

**Installation:** No new packages needed.

---

## Architecture Patterns

### Recommended Project Structure

No new files or folders are needed. Changes are confined to:

```
backend/
└── main.py          # Add validation + run_in_threadpool wrapping

frontend/src/
└── main.js          # Replace health-check scaffold with upload form + loading state
```

### Pattern 1: File Validation at the Top of the Handler

**What:** Check `file.size` and `file.content_type` before writing to disk or running the pipeline. Raise `HTTPException` immediately on violation.

**When to use:** Always, as the first two statements inside the endpoint body, before any I/O or processing.

**Key facts about `file.size`:**
- Starlette's `MultiPartParser` initializes `UploadFile.size = 0` and increments it via `write()` as chunks arrive.
- By the time the async path operation function receives control, all parts have been streamed and `file.size` reflects the full file size.
- Verified by reading `starlette/formparsers.py` and `starlette/datastructures.py` from the installed venv (starlette bundled with fastapi 0.135.1).

**Key facts about `file.content_type`:**
- It is a property that reads `self.headers.get("content-type", None)` — the content-type subheader from the multipart part, not the global request content-type.
- The browser sets this to `"audio/mpeg"` for MP3 files in a standard file input.
- It can be spoofed by a malicious client sending a crafted multipart body — acceptable for this use case (personal tool, not a security product).

```python
# Source: verified against FastAPI 0.135.1 official docs + starlette source
from fastapi import FastAPI, File, UploadFile, HTTPException

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_TYPES = {"audio/mpeg", "audio/mp3"}

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    # Validation before any processing
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is 50 MB."
        )
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Invalid file type '{file.content_type}'. Only MP3 files are accepted."
        )
    # ... pipeline follows
```

### Pattern 2: Offloading the Blocking Pipeline with run_in_threadpool

**What:** Wrap the synchronous pipeline call in `run_in_threadpool` so the async event loop is not blocked.

**When to use:** Any time you call blocking (non-async) code from an `async def` endpoint. The current pipeline functions (`load_audio`, `detect_chords_pipeline`, `segment_song`) are all synchronous CPU-bound calls.

**Why not just use `def` instead of `async def`?**
The endpoint currently uses `async def analyze` because it calls `await file.read()`. Changing to `def` would require switching all file I/O to synchronous calls. Using `run_in_threadpool` for the pipeline portion is cleaner and preserves the existing async file I/O.

```python
# Source: starlette.concurrency.run_in_threadpool (verified in installed venv)
# run_in_threadpool signature: async def run_in_threadpool(func, *args, **kwargs) -> T
# Internally calls anyio.to_thread.run_sync(functools.partial(func, *args, **kwargs))

from starlette.concurrency import run_in_threadpool
import asyncio

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    # ... validation ...

    # Write uploaded file to temp location (async)
    suffix = os.path.splitext(file.filename or "upload.mp3")[1] or ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Run the entire blocking pipeline in a thread
        result = await run_in_threadpool(_run_pipeline, tmp_path)
        return result
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _run_pipeline(tmp_path: str) -> dict:
    """Synchronous pipeline function - safe to call from a thread."""
    audio = load_audio(tmp_path)
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
        'tempo_bpm': chord_result['tempo_bpm'],
        'chord_segments': chord_result['chord_segments'],
        'sections': sections,
        'n_beats': chord_result['n_beats'],
        'n_segments': chord_result['n_segments'],
    }
```

### Pattern 3: Frontend Upload Form with Loading State

**What:** Replace the current health-check scaffold in `frontend/src/main.js` with a file input form. On submit, show "Analyzing audio..." immediately, POST the file via `fetch` + `FormData`, then update the UI with the result or an error.

**When to use:** The page must not appear frozen during the 10-60 second processing window. Toggle the loading message BEFORE `await fetch(...)` and clear it in the finally block.

**Critical note — do not set Content-Type manually:** When sending a `FormData` object, the browser must set the `Content-Type: multipart/form-data` header with the correct boundary. If you set `Content-Type` manually in the fetch options, it omits the boundary and the server cannot parse the form.

```javascript
// Source: MDN FormData, verified with FastAPI multipart expectations
// frontend/src/main.js

import './style.css'

document.querySelector('#app').innerHTML = `
  <h1>dontCave</h1>
  <form id="upload-form">
    <input type="file" id="file-input" accept=".mp3,audio/mpeg" required />
    <button type="submit" id="submit-btn">Analyze</button>
  </form>
  <p id="status"></p>
  <pre id="result"></pre>
`

const form = document.querySelector('#upload-form')
const statusEl = document.querySelector('#status')
const resultEl = document.querySelector('#result')
const submitBtn = document.querySelector('#submit-btn')

form.addEventListener('submit', async (e) => {
  e.preventDefault()

  const fileInput = document.querySelector('#file-input')
  if (!fileInput.files.length) return

  const formData = new FormData()
  formData.append('file', fileInput.files[0])

  // Show loading state BEFORE the awaited fetch
  statusEl.textContent = 'Analyzing audio...'
  submitBtn.disabled = true

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      body: formData,
      // Do NOT set Content-Type header — browser sets it with boundary
    })

    if (!response.ok) {
      const err = await response.json()
      statusEl.textContent = `Error: ${err.detail || response.statusText}`
      return
    }

    const data = await response.json()
    statusEl.textContent = 'Analysis complete.'
    resultEl.textContent = JSON.stringify(data, null, 2)
  } catch (err) {
    statusEl.textContent = `Network error: ${err.message}`
  } finally {
    submitBtn.disabled = false
  }
})
```

### Anti-Patterns to Avoid

- **Calling pipeline functions directly from `async def` without `run_in_threadpool`:** This blocks the event loop for the entire 10-60 seconds. The second request to `/health` will not get a response until the pipeline finishes. The success criteria explicitly require `/health` to remain responsive.
- **Setting `Content-Type: multipart/form-data` manually in fetch:** Omits the boundary string, causing the server to respond with 422 (Unprocessable Entity) because it cannot parse the multipart body.
- **Using `File(max_length=...)` to limit UploadFile size:** This does not work — `max_length` is for string validation only. Pydantic tries to call `len()` on the file object and fails. Verified via GitHub discussion #11750.
- **Checking `content-length` request header as the primary size guard:** The global `Content-Length` header in a multipart request reflects the entire request body (including form overhead), not just the file size. Use `file.size` instead after streaming completes.
- **Reading all bytes before validation:** `await file.read()` loads the entire file into memory before you can check its size. For a 50 MB file that will be rejected, this wastes memory. Check `file.size` first.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Threadpool offloading | Custom `asyncio.ThreadPoolExecutor` management | `starlette.concurrency.run_in_threadpool` | Already installed, handles `functools.partial` wrapping automatically, integrated with anyio |
| Multipart parsing | Manual byte parsing | `python-multipart` via FastAPI `UploadFile` | Already installed and wired; FastAPI uses it automatically |
| Loading indicator | Polling endpoint or WebSocket | DOM text toggle before/after `await fetch()` | The pipeline completes synchronously in a thread and returns; no streaming is needed. A simple text toggle satisfies the success criteria. |

**Key insight:** The existing stack handles everything. This phase is configuration and wiring, not new dependencies.

---

## Common Pitfalls

### Pitfall 1: Event Loop Blocked by Pipeline

**What goes wrong:** The `/health` endpoint returns no response while `/analyze` is running. The server appears hung to a second user.

**Why it happens:** `load_audio`, `detect_chords_pipeline`, and `segment_song` are synchronous functions. Calling them directly inside `async def analyze` blocks the single-threaded asyncio event loop for the duration.

**How to avoid:** Extract the pipeline into a plain `def _run_pipeline(tmp_path)` function and call it via `await run_in_threadpool(_run_pipeline, tmp_path)`.

**Warning signs:** During manual verification, issuing `curl http://localhost:8000/health` in a second terminal while an upload is processing returns immediately (good) or hangs (bad).

### Pitfall 2: file.size Is None

**What goes wrong:** `file.size` returns `None` even though a file was uploaded, causing the size check to be skipped silently.

**Why it happens:** Starlette initializes `size=0` and increments it via `write()`. If somehow the file is constructed differently (unlikely in normal FastAPI usage), `size` could be `None`.

**How to avoid:** Guard explicitly: `if file.size is not None and file.size > MAX_FILE_SIZE`. If `file.size` is `None`, fall through to normal processing (the file is small enough to not have triggered the spooled memory limit). This is a safe default for a personal tool.

**Warning signs:** Upload a file larger than 50 MB and verify the 413 response is returned before the pipeline starts.

### Pitfall 3: MIME Type Mismatch for MP3

**What goes wrong:** The browser sends `audio/mpeg` for MP3 files, but the validation set only contains `"audio/mp3"` (or vice versa). All valid MP3 uploads are rejected with 415.

**Why it happens:** The MIME type for MP3 is inconsistently registered across browsers and operating systems. Chrome sends `audio/mpeg`; some environments send `audio/mp3`.

**How to avoid:** Accept both: `ALLOWED_MIME_TYPES = {"audio/mpeg", "audio/mp3"}`. Test with the actual browser being used.

**Warning signs:** Upload a valid MP3 and receive a 415 error.

### Pitfall 4: Temp File Not Cleaned Up on Exception

**What goes wrong:** An exception in the pipeline leaves orphaned temp files in `/tmp`.

**Why it happens:** `tempfile.NamedTemporaryFile(delete=False)` requires explicit cleanup. If the exception happens before the `finally` block, the file remains.

**How to avoid:** The current `main.py` already has a `finally: os.unlink(tmp_path)` pattern. Preserve this when refactoring. The `_run_pipeline` helper should not clean up the temp file — cleanup stays in the endpoint's `finally` block which owns the temp file's lifecycle.

### Pitfall 5: FormData Content-Type Manual Override

**What goes wrong:** The backend receives a 422 error on all uploads despite a valid file being sent.

**Why it happens:** The developer sets `headers: {'Content-Type': 'multipart/form-data'}` in the fetch call. This sets the content-type without the boundary parameter, breaking multipart parsing.

**How to avoid:** Never set `Content-Type` in the fetch options when sending `FormData`. The browser sets it correctly with the boundary automatically.

**Warning signs:** 422 Unprocessable Entity on all file uploads, even a known-good MP3.

---

## Code Examples

Verified patterns from official sources and codebase inspection.

### Complete Validated Backend Endpoint

```python
# Source: FastAPI 0.135.1 official docs + starlette source (installed venv)
import os
import tempfile
import asyncio

from fastapi import FastAPI, File, UploadFile, HTTPException
from starlette.concurrency import run_in_threadpool

from audio.loader import load_audio
from audio.chord_detection import (
    detect_chords_pipeline,
    beat_track_grid,
    extract_beat_chroma,
)
from audio.segmentation import segment_song, build_sections

app = FastAPI()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB in bytes
ALLOWED_MIME_TYPES = {"audio/mpeg", "audio/mp3"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    # 1. Validate file size (file.size is populated by multipart parser)
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum allowed size is 50 MB."
        )

    # 2. Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Invalid file type '{file.content_type}'. "
                "Only MP3 files (audio/mpeg) are accepted."
            )
        )

    # 3. Write to temp file
    suffix = os.path.splitext(file.filename or "upload.mp3")[1] or ".mp3"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # 4. Run blocking pipeline in threadpool
        result = await run_in_threadpool(_run_pipeline, tmp_path)
        return result

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


def _run_pipeline(tmp_path: str) -> dict:
    """Blocking pipeline — safe to call from run_in_threadpool."""
    audio = load_audio(tmp_path)
    chord_result = detect_chords_pipeline(audio)
    _, beat_frames = beat_track_grid(audio['y_percussive'], audio['sr'])
    chroma_sync = extract_beat_chroma(
        audio['y_harmonic'], beat_frames, audio['sr']
    )
    boundary_beats = segment_song(chroma_sync, audio['duration'])
    sections = build_sections(
        boundary_beats,
        chord_result['beat_times'],
        chord_result['chord_sequence'],
    )
    return {
        'tempo_bpm': chord_result['tempo_bpm'],
        'chord_segments': chord_result['chord_segments'],
        'sections': sections,
        'n_beats': chord_result['n_beats'],
        'n_segments': chord_result['n_segments'],
    }
```

### Frontend Upload Form with Loading State

```javascript
// Source: MDN FormData spec, fetch spec
// frontend/src/main.js

import './style.css'

document.querySelector('#app').innerHTML = `
  <h1>dontCave</h1>
  <form id="upload-form">
    <label for="file-input">Select MP3 file:</label>
    <input type="file" id="file-input" accept=".mp3,audio/mpeg" required />
    <button type="submit" id="submit-btn">Analyze</button>
  </form>
  <p id="status"></p>
  <pre id="result"></pre>
`

const form = document.querySelector('#upload-form')
const statusEl = document.querySelector('#status')
const resultEl = document.querySelector('#result')
const submitBtn = document.querySelector('#submit-btn')

form.addEventListener('submit', async (e) => {
  e.preventDefault()
  resultEl.textContent = ''

  const fileInput = document.querySelector('#file-input')
  if (!fileInput.files.length) {
    statusEl.textContent = 'Please select an MP3 file.'
    return
  }

  const formData = new FormData()
  formData.append('file', fileInput.files[0])

  // Show loading state before the async network call
  statusEl.textContent = 'Analyzing audio...'
  submitBtn.disabled = true

  try {
    // Note: do NOT set Content-Type header — browser sets it with boundary
    const response = await fetch('/api/analyze', {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }))
      statusEl.textContent = `Error: ${err.detail || response.statusText}`
      return
    }

    const data = await response.json()
    statusEl.textContent = 'Analysis complete.'
    resultEl.textContent = JSON.stringify(data, null, 2)
  } catch (err) {
    statusEl.textContent = `Network error: ${err.message}`
  } finally {
    submitBtn.disabled = false
  }
})
```

### Verifying Server Remains Responsive (Manual Test)

```bash
# Terminal 1: submit a long-processing file
curl -X POST http://localhost:8000/analyze \
  -F "file=@/path/to/song.mp3" &

# Terminal 2: immediately check health
curl http://localhost:8000/health
# Should return {"status":"ok"} immediately — not hang
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `asyncio.get_event_loop().run_in_executor(None, fn)` | `starlette.concurrency.run_in_threadpool(fn, *args)` or `asyncio.to_thread(fn, *args)` | Python 3.9 / Starlette | Simpler API, same behavior |
| `XMLHttpRequest` with `onprogress` | `fetch` + FormData with DOM state toggle | ~2017 | Fetch is now universal; XHR only needed for byte-level progress bars |

**Deprecated/outdated:**
- `asyncio.get_event_loop()`: Deprecated in Python 3.10+. Use `asyncio.get_running_loop()` inside coroutines. Moot if using `run_in_threadpool` which handles this internally.
- `File(max_length=N)` for UploadFile size limiting: Does not work (Pydantic tries `len()` on file object). Use `file.size` instead.

---

## Open Questions

1. **`file.size` when file is exactly 0 bytes or size is None**
   - What we know: Starlette initializes `size=0` and increments via `write()`. `None` should not occur in normal multipart flow.
   - What's unclear: Edge case behavior if multipart body is malformed or browser omits the part body.
   - Recommendation: The guard `if file.size is not None and file.size > MAX_FILE_SIZE` is safe — `None` passes through to be caught by the pipeline's own error handling.

2. **MP3 MIME type on all target browsers/OS**
   - What we know: Chrome sends `audio/mpeg`. Some older/unusual environments send `audio/mp3`.
   - What's unclear: Whether Windows Chrome or Safari sends a different value.
   - Recommendation: Accept `{"audio/mpeg", "audio/mp3"}` as the allowed set. Test manually on the development machine.

3. **Frontend result display format**
   - What we know: Phase 5 success criteria do not specify what the result looks like — only that the loading state appears and disappears.
   - What's unclear: Phase 6 will add lyrics input and change the form structure significantly.
   - Recommendation: Display raw JSON in a `<pre>` element for Phase 5. Phase 6 will replace this with the chord chart display.

---

## Sources

### Primary (HIGH confidence)

- FastAPI 0.135.1 installed venv — `starlette/datastructures.py` (UploadFile source), `starlette/formparsers.py` (size population), `starlette/concurrency.py` (run_in_threadpool source) — verified by reading source directly
- https://fastapi.tiangolo.com/reference/uploadfile/ — UploadFile API reference with `size`, `content_type`, `filename`, `headers` attributes
- https://fastapi.tiangolo.com/tutorial/request-files/ — Official upload file tutorial
- https://fastapi.tiangolo.com/tutorial/handling-errors/ — HTTPException patterns
- https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.run_in_executor — run_in_executor API reference

### Secondary (MEDIUM confidence)

- https://sentry.io/answers/fastapi-difference-between-run-in-executor-and-run-in-threadpool/ — run_in_executor vs run_in_threadpool comparison (consistent with source code)
- https://www.slingacademy.com/article/fastapi-how-to-upload-and-validate-files/ — file.file.seek(0,2)/tell() validation pattern (confirmed seek/tell approach works, though file.size is simpler)
- https://davidmuraya.com/blog/fastapi-file-uploads/ — Content-Length header approach (useful as defense-in-depth but not primary)
- https://maximeblanc.fr/blog/file-upload-in-javascript-using-fetch — Fetch + FormData with loading state

### Tertiary (LOW confidence)

- https://github.com/fastapi/fastapi/discussions/8167 — Strategies for limiting upload size (community discussion, confirmed file.size is the right approach)
- https://github.com/fastapi/fastapi/discussions/11750 — File(max_length=N) doesn't work for UploadFile (single source, but consistent with source code reading)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified installed and functional in the venv
- Architecture (run_in_threadpool): HIGH — source code of `run_in_threadpool` read directly from installed venv; confirmed `anyio.to_thread.run_sync` underneath
- Architecture (file.size): HIGH — `starlette/formparsers.py` and `starlette/datastructures.py` read directly; size initialized to 0 and incremented during streaming
- Architecture (MIME validation): HIGH — `content_type` is a property reading headers; accepts both `audio/mpeg` and `audio/mp3`
- Frontend patterns: HIGH — Fetch API + FormData is a browser standard; loading state toggle is DOM manipulation
- Pitfalls: HIGH for event-loop blocking (confirmed by FastAPI docs), MEDIUM for MIME type variations (manual testing recommended)

**Research date:** 2026-03-04
**Valid until:** 2026-06-04 (stable APIs; FastAPI and Starlette evolve slowly for these primitives)
