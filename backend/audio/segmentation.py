"""Structural segmentation: detect song sections from beat-synced chroma.

Uses librosa.segment.agglomerative() on stack_memory-enhanced beat-synced
chroma to partition a song into labeled sections. All inputs come from
Phase 3's detect_chords_pipeline() -- no new audio loading or feature
extraction is required.

No numba dependencies: librosa.segment uses sklearn and scipy only.
"""
import librosa
import librosa.segment
import numpy as np


DEFAULT_LABELS = [
    'Section A', 'Section B', 'Section C', 'Section D',
    'Section E', 'Section F', 'Section G', 'Section H',
    'Section I', 'Section J', 'Section K', 'Section L',
]


def compute_k(duration_s: float, n_beats: int) -> int:
    """
    Compute number of sections from song duration.

    Heuristic: one section per ~30 seconds, floor at 4, cap at min(12, n_beats-1).
    The floor of 4 ensures even short songs get meaningful segmentation.
    The cap of 12 prevents over-segmentation on long songs.
    n_beats-1 guard prevents sklearn ValueError when k >= n_beats.

    Args:
        duration_s: Total song duration in seconds.
        n_beats: Number of beats in the song (chroma_sync.shape[1]).

    Returns:
        k: int -- number of segments for agglomerative clustering.
    """
    k = max(4, int(duration_s / 30))
    return min(k, 12, n_beats - 1)


def segment_song(chroma_sync: np.ndarray, duration_s: float) -> np.ndarray:
    """
    Detect section boundaries as beat indices using agglomerative clustering.

    Applies stack_memory (n_steps=3, delay=1) for temporal context, then
    runs agglomerative clustering with k sections. Boundaries are inherently
    beat-aligned because the input is beat-synced chroma.

    Args:
        chroma_sync: np.ndarray of shape (12, n_beats) -- beat-synced chroma
                     from extract_beat_chroma() in chord_detection.py.
        duration_s: Total song duration in seconds (from load_audio()['duration']).

    Returns:
        boundary_beats: np.ndarray of int beat indices where sections start.
                       Always starts with 0.
    """
    n_beats = chroma_sync.shape[1]
    k = compute_k(duration_s, n_beats)

    # stack_memory adds temporal context (3 steps back) for better boundary
    # detection. This produces (36, n_beats) from (12, n_beats).
    chroma_stacked = librosa.feature.stack_memory(chroma_sync, n_steps=3, delay=1)

    # agglomerative returns beat indices directly -- already beat-aligned.
    # Uses sklearn AgglomerativeClustering with Ward linkage internally.
    boundary_beats = librosa.segment.agglomerative(chroma_stacked, k)
    return boundary_beats


def build_sections(
    boundary_beats: np.ndarray,
    beat_times: list[float],
    chord_sequence: list[str],
) -> list[dict]:
    """
    Build sections array for API response from boundaries + chord sequence.

    Combines boundary beat indices, beat times, and per-beat chord labels
    from Phase 3 to produce the sections array. Each section contains a
    label, start time, and a collapsed chord sequence (consecutive identical
    chords merged).

    Args:
        boundary_beats: Beat indices from segment_song() (always starts at 0).
        beat_times: list[float] from detect_chords_pipeline() result.
                   Length is authoritative n_beats (use this, not chroma_sync.shape[1]).
        chord_sequence: list[str] from detect_chords_pipeline() result.

    Returns:
        sections: list of dicts, each with:
            - 'label': str -- 'Section A', 'Section B', etc.
            - 'start': float -- start time in seconds (rounded to 3 decimals)
            - 'chord_sequence': list[dict] -- collapsed chords with 'chord' and 'time' keys

    NOTE: boundary_beats are filtered to < len(beat_times) to handle the
    off-by-one from fix_frames in extract_beat_chroma() (Pitfall 3 in research).
    """
    n_beats = len(beat_times)
    # Filter out-of-bounds boundaries (safety against fix_frames off-by-one)
    valid_bounds = boundary_beats[boundary_beats < n_beats]

    sections = []
    for i, start_beat in enumerate(valid_bounds):
        sb = int(start_beat)
        eb = int(valid_bounds[i + 1]) if i + 1 < len(valid_bounds) else n_beats

        t_start = float(beat_times[sb])
        section_chord_seq = chord_sequence[sb:eb]
        beat_slice = beat_times[sb:eb]

        # Collapse consecutive identical chords within this section
        chords_collapsed = []
        for j, chord in enumerate(section_chord_seq):
            t = float(beat_slice[j]) if j < len(beat_slice) else t_start
            if not chords_collapsed or chords_collapsed[-1]['chord'] != chord:
                chords_collapsed.append({'chord': chord, 'time': round(t, 3)})

        # Guard against empty sections (two adjacent boundaries at same beat)
        if not chords_collapsed and sb < len(chord_sequence):
            chords_collapsed.append({'chord': chord_sequence[sb], 'time': round(t_start, 3)})

        sections.append({
            'label': DEFAULT_LABELS[i % len(DEFAULT_LABELS)],
            'start': round(t_start, 3),
            'chord_sequence': chords_collapsed,
        })

    return sections
