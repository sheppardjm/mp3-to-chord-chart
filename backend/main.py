"""dontCave backend API.

Endpoints:
    GET  /health   — health check
    POST /analyze  — upload MP3 + lyrics, returns ChartData JSON

Validation:
    - Files larger than 50 MB are rejected with HTTP 413
    - Non-MP3 MIME types are rejected with HTTP 415
    - Missing or empty lyrics are rejected with HTTP 422

Async processing:
    - The synchronous audio pipeline runs in a threadpool via
      run_in_threadpool so the event loop is not blocked during analysis
    - Chart building (build_chart) is fast pure Python and runs in-process
"""
import os
import tempfile

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from audio.loader import load_audio
from audio.chord_detection import (
    detect_chords_pipeline,
    beat_track_grid,
    extract_beat_chroma,
)
from audio.key_detection import detect_key
from audio.models import ChartData
from audio.segmentation import segment_song, build_sections
from audio.chart_builder import build as build_chart

app = FastAPI()

# ---------------------------------------------------------------------------
# Upload validation constants
# ---------------------------------------------------------------------------
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_TYPES = {"audio/mpeg", "audio/mp3"}


# ---------------------------------------------------------------------------
# Synchronous pipeline (runs in threadpool to avoid blocking the event loop)
# ---------------------------------------------------------------------------

def _run_pipeline(tmp_path: str) -> dict:
    """Run the full audio analysis pipeline synchronously.

    This function is intentionally synchronous — it is offloaded to a
    threadpool by analyze() so the FastAPI event loop remains responsive
    during the 10-60 second processing time.

    Args:
        tmp_path: Absolute path to the temporary MP3 file on disk.

    Returns:
        dict with keys: key, tempo_bpm, chord_segments, sections, n_beats, n_segments
    """
    # Phase 2: Load audio
    audio = load_audio(tmp_path)

    # Phase 2: Key detection
    key = detect_key(audio['y_harmonic'], audio['sr'])

    # Phase 3: Chord detection
    chord_result = detect_chords_pipeline(audio)

    # Phase 4: Structural segmentation
    # Re-compute beat-synced chroma for segmentation input.
    # detect_chords_pipeline() doesn't expose chroma_sync, so we
    # recompute it from the same harmonic/percussive components.
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
        'key': key,
        'tempo_bpm': chord_result['tempo_bpm'],
        'chord_segments': chord_result['chord_segments'],
        'sections': sections,
        'n_beats': chord_result['n_beats'],
        'n_segments': chord_result['n_segments'],
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=ChartData)
async def analyze(file: UploadFile = File(...), lyrics: str = Form(None)):
    """Analyze an uploaded MP3 file with lyrics: validate, detect chords, build chart.

    Validates file size (<= 50 MB) and MIME type (audio/mpeg or audio/mp3)
    before any I/O. Writes to a temp file, runs the synchronous audio pipeline
    in a threadpool, then aligns detected chords to the provided lyrics and
    returns a structured ChartData response.

    Args:
        file:   Uploaded MP3 file (multipart/form-data).
        lyrics: Song lyrics as plain text (multipart/form-data). Sections
                separated by blank lines; lines within each section separated
                by newlines.

    Returns:
        ChartData JSON with keys: key, bpm, unique_chords, sections.

    Raises:
        413: File exceeds 50 MB limit
        415: File is not an MP3 (audio/mpeg)
        422: Lyrics missing/empty or pipeline output malformed
        500: Internal pipeline error
    """
    # ------------------------------------------------------------------
    # 1. Validate file size (cheap check, no I/O)
    # ------------------------------------------------------------------
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum allowed size is 50 MB.",
        )

    # ------------------------------------------------------------------
    # 2. Validate MIME type (no I/O)
    # ------------------------------------------------------------------
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Invalid file type '{file.content_type}'. "
                "Only MP3 files (audio/mpeg) are accepted."
            ),
        )

    # ------------------------------------------------------------------
    # 3. Write to temp file and run pipeline in threadpool
    # ------------------------------------------------------------------
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename or "upload.mp3")[1] or ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        result = await run_in_threadpool(_run_pipeline, tmp_path)

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
