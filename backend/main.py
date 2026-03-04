"""dontCave backend API.

Endpoints:
    GET  /health   — health check
    POST /analyze  — upload MP3, returns chord analysis with sections
"""
import os
import tempfile

from fastapi import FastAPI, File, UploadFile, HTTPException

from audio.loader import load_audio
from audio.chord_detection import (
    detect_chords_pipeline,
    beat_track_grid,
    extract_beat_chroma,
)
from audio.segmentation import segment_song, build_sections

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Analyze an uploaded MP3 file: detect chords and segment into sections.

    Accepts a multipart file upload. Writes to a temp file, runs the full
    pipeline, and returns JSON with tempo, chord segments, and labeled sections.

    Returns:
        JSON with keys:
            - tempo_bpm: float
            - chord_segments: list[dict] — collapsed chord timeline
            - sections: list[dict] — labeled sections with chord sequences
            - n_beats: int
            - n_segments: int
    """
    # Write uploaded file to temp location
    suffix = os.path.splitext(file.filename or "upload.mp3")[1] or ".mp3"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Phase 2: Load audio
        audio = load_audio(tmp_path)

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
            'tempo_bpm': chord_result['tempo_bpm'],
            'chord_segments': chord_result['chord_segments'],
            'sections': sections,
            'n_beats': chord_result['n_beats'],
            'n_segments': chord_result['n_segments'],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
