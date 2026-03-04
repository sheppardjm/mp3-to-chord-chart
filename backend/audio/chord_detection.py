"""Beat tracking and chord detection pipeline.

Beat tracking uses onset_strength + tempo + grid placement instead of
librosa.beat.beat_track(), which is incompatible with the numba no-op stub
(uses @guvectorize internally — fails with TypeError on Python 3.14/x86_64).
"""
import warnings

import librosa
import numpy as np

# MUST match Phase 2 HPSS hop_length (loader.py uses 1024).
# All frame-based operations (onset_strength, chroma_cqt, frames_to_time)
# must share this constant to avoid frame-index misalignment.
HOP = 1024


def beat_track_grid(y_percussive: np.ndarray, sr: int = 22050) -> tuple[float, np.ndarray]:
    """
    Estimate tempo and place beats on a phase-optimized regular grid.

    Uses onset_strength on the percussive component (cleaner rhythm signal
    than full audio) for tempo estimation, then places beats on a regular
    grid with phase offset optimized to maximize onset energy at beat positions.

    Args:
        y_percussive: Percussive component from HPSS (load_audio result).
                      Must NOT be y or y_harmonic — percussive gives cleaner
                      onset detection for rhythm.
        sr: Sample rate (default 22050, matching load_audio output).

    Returns:
        (tempo_bpm, beat_frames) where:
            - tempo_bpm: float — estimated tempo in beats per minute
            - beat_frames: np.ndarray of int — frame indices at hop_length=1024

    NOTE: librosa.beat.beat_track() is broken with the numba no-op stub.
    It uses @numba.guvectorize on __beat_local_score/__beat_track_dp, whose
    body code requires numba JIT compilation. This grid approach produces
    equivalent beat counts empirically (430/430 on Don't Cave.mp3).
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # suppress tempo() FutureWarning
        onset_env = librosa.onset.onset_strength(y=y_percussive, sr=sr, hop_length=HOP)
        tempo_arr = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)

    tempo_bpm = float(tempo_arr[0])
    frame_rate = sr / HOP
    beat_period = frame_rate * 60.0 / tempo_bpm
    n_frames = onset_env.shape[-1]

    # Phase optimization: find grid offset that maximizes onset energy at beats.
    # Step size of 2 frames gives sufficient resolution without excessive iteration.
    best_phase, best_score = 0.0, -np.inf
    for ph in np.arange(0, beat_period, 2):
        bf = np.round(np.arange(ph, n_frames, beat_period)).astype(int)
        bf = bf[bf < n_frames]
        score = onset_env[bf].sum()
        if score > best_score:
            best_score = score
            best_phase = ph

    beat_frames = np.round(np.arange(best_phase, n_frames, beat_period)).astype(int)
    beat_frames = beat_frames[beat_frames < n_frames]

    return tempo_bpm, beat_frames


def extract_beat_chroma(y_harmonic: np.ndarray, beat_frames: np.ndarray,
                        sr: int = 22050) -> np.ndarray:
    """
    Extract chroma features at hop_length=1024 and sync to beat positions.

    Uses chroma_cqt (CQT-based pitch class bins) on the harmonic component
    for cleaner pitch information. Synced to beat frames via librosa.util.sync
    with median aggregation for robustness against outlier frames within a beat.

    IMPORTANT: hop_length MUST match beat_track_grid() — both use HOP=1024.
    tuning=0.0 bypasses estimate_tuning() which triggers numba @stencil
    (Phase 2 D001 / 02-02 D001).

    Args:
        y_harmonic: Harmonic component from HPSS (load_audio result).
        beat_frames: Beat frame indices from beat_track_grid().
        sr: Sample rate (default 22050).

    Returns:
        chroma_sync: np.ndarray of shape (12, n_beats) — beat-synchronized
                     chroma matrix. Each column is the median chroma vector
                     for one beat.
    """
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr, hop_length=HOP, tuning=0.0)
    beat_frames_fixed = librosa.util.fix_frames(beat_frames, x_min=0, x_max=chroma.shape[-1])
    return librosa.util.sync(chroma, beat_frames_fixed, aggregate=np.median)


# Chromatic note names for chord labeling.
# Flat-side convention matching key_detection.py ROOTS.
NOTES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']


def build_chord_templates() -> tuple[list[str], np.ndarray]:
    """
    Build 36 chord templates: 12 major, 12 minor, 12 dominant 7th.

    Each template is a 12-element binary vector over chroma bins, L2-normalized
    so that cosine similarity (dot product) can be computed directly.

    Template intervals per quality:
        :maj  — root + major 3rd (4 semitones) + perfect 5th (7)
        :min  — root + minor 3rd (3) + perfect 5th (7)
        :7    — root + major 3rd (4) + perfect 5th (7) + minor 7th (10)

    Returns:
        chord_names: list[str] of length 36 — e.g. ['C:maj', 'C:min', 'C:7', 'Db:maj', ...]
        template_matrix: np.ndarray of shape (36, 12) — each row is a
                         normalized chord template vector.
    """
    chord_names = []
    rows = []

    for root in range(12):
        for suffix, intervals in [(':maj', [0, 4, 7]),
                                   (':min', [0, 3, 7]),
                                   (':7', [0, 4, 7, 10])]:
            t = np.zeros(12)
            for i in intervals:
                t[(root + i) % 12] = 1.0
            t /= np.linalg.norm(t)
            chord_names.append(f"{NOTES[root]}{suffix}")
            rows.append(t)

    return chord_names, np.array(rows)


def detect_chords(chroma_sync: np.ndarray, chord_names: list[str],
                  template_matrix: np.ndarray) -> list[str]:
    """
    Assign one chord label per beat using cosine similarity + Viterbi smoothing.

    Process:
        1. L2-normalize each beat's chroma column (cosine similarity prep).
        2. Compute dot product of template_matrix @ chroma_norm to get
           cosine similarity scores for all 36 chords at each beat.
        3. Clip to non-negative (negative cosine = no match).
        4. Normalize to produce a probability-like observation matrix.
        5. Apply Viterbi with a self-transition loop matrix (p_loop=0.5) to
           smooth the sequence while allowing reasonable chord changes.

    Args:
        chroma_sync: np.ndarray of shape (12, n_beats) — beat-synced chroma.
        chord_names: list[str] of length 36 — from build_chord_templates().
        template_matrix: np.ndarray of shape (36, 12) — normalized templates.

    Returns:
        list[str] of length n_beats — one chord label per beat, e.g. 'G:maj'.

    NOTE: p_loop=0.5 allows transitions at every beat without over-smoothing.
    Values above 0.7 collapse multi-minute songs to 1-2 unique chords.
    """
    chroma_norm = chroma_sync / (np.linalg.norm(chroma_sync, axis=0, keepdims=True) + 1e-8)
    probs = template_matrix @ chroma_norm
    probs = np.clip(probs, 0, None)
    probs = probs / (probs.sum(axis=0, keepdims=True) + 1e-8)
    transition = librosa.sequence.transition_loop(len(chord_names), 0.5)
    states = librosa.sequence.viterbi(probs, transition)
    return [chord_names[s] for s in states]


def collapse_chords(chord_seq: list[str], beat_times: np.ndarray) -> list[dict]:
    """
    Merge consecutive identical chord labels into timestamped segments.

    Each segment records the chord and the time (in seconds) at which it begins.
    The end of each segment is implicitly the start of the next segment (or end
    of the song for the last segment).

    Args:
        chord_seq: list[str] of length n_beats — one chord label per beat.
        beat_times: np.ndarray of shape (n_beats,) — beat onset times in seconds.

    Returns:
        list[dict] where each dict has:
            'chord': str  — chord label, e.g. 'G:maj'
            'time':  float — onset time in seconds

    Example:
        ['G:maj', 'G:maj', 'D:maj', 'D:maj', 'Em:min'] -> [
            {'chord': 'G:maj', 'time': 0.0},
            {'chord': 'D:maj', 'time': 2.3},
            {'chord': 'E:min', 'time': 4.6},
        ]
    """
    result = []
    for chord, time in zip(chord_seq, beat_times):
        if not result or result[-1]['chord'] != chord:
            result.append({'chord': chord, 'time': float(time)})
    return result


def measure_accuracy(detected: list[str], reference: list[str]) -> dict:
    """
    Measure chord detection accuracy at beat level.

    Compares detected chord labels against reference labels, both as exact
    match and root-only match (ignoring quality — :maj/:min/:7).

    Both lists must be the same length (aligned by beat index). If lengths
    differ, comparison is truncated to the shorter list.

    Args:
        detected: List of detected chord strings (e.g. ["G:maj", "C:maj", ...])
        reference: List of reference chord strings (same format)

    Returns:
        dict with:
            - exact_accuracy: float — fraction of beats where chord matches exactly
            - root_accuracy: float — fraction of beats where root note matches
            - n_compared: int — number of beats compared
            - exact_matches: int — count of exact matches
            - root_matches: int — count of root-only matches
    """
    n = min(len(detected), len(reference))
    if n == 0:
        return {'exact_accuracy': 0.0, 'root_accuracy': 0.0,
                'n_compared': 0, 'exact_matches': 0, 'root_matches': 0}

    exact_matches = 0
    root_matches = 0
    for d, r in zip(detected[:n], reference[:n]):
        if d == r:
            exact_matches += 1
        d_root = d.split(':')[0]
        r_root = r.split(':')[0]
        if d_root == r_root:
            root_matches += 1

    return {
        'exact_accuracy': exact_matches / n,
        'root_accuracy': root_matches / n,
        'n_compared': n,
        'exact_matches': exact_matches,
        'root_matches': root_matches,
    }


def detect_chords_pipeline(audio: dict) -> dict:
    """
    Full chord detection pipeline from load_audio() output to collapsed segments.

    Orchestrates:
        1. beat_track_grid()     — tempo estimation and beat frame placement
        2. extract_beat_chroma() — beat-synced CQT chroma (12, n_beats)
        3. build_chord_templates() — 36 L2-normalized chord templates
        4. detect_chords()       — cosine similarity + Viterbi smoothing
        5. collapse_chords()     — merge consecutive identical chord labels

    Args:
        audio: dict from load_audio() containing:
            - y_percussive: np.ndarray — percussive component (for beat tracking)
            - y_harmonic:   np.ndarray — harmonic component (for chroma extraction)
            - sr:           int        — sample rate (expected 22050)

    Returns:
        dict with keys:
            - tempo_bpm:      float      — estimated tempo in beats per minute
            - beat_times:     list[float] — beat onset times in seconds
            - chord_sequence: list[str]  — one chord label per beat
            - chord_segments: list[dict] — collapsed segments with 'chord' and 'time'
            - n_beats:        int        — total number of beats
            - n_segments:     int        — number of chord segments after collapse
    """
    tempo_bpm, beat_frames = beat_track_grid(audio['y_percussive'], audio['sr'])
    chroma_sync = extract_beat_chroma(audio['y_harmonic'], beat_frames, audio['sr'])
    chord_names, template_matrix = build_chord_templates()
    chord_seq = detect_chords(chroma_sync, chord_names, template_matrix)
    beat_frames_fixed = librosa.util.fix_frames(beat_frames, x_min=0)
    beat_times = librosa.frames_to_time(
        beat_frames_fixed[:len(chord_seq)], sr=audio['sr'], hop_length=HOP
    )
    segments = collapse_chords(chord_seq, beat_times)
    return {
        'tempo_bpm': tempo_bpm,
        'beat_times': beat_times.tolist(),
        'chord_sequence': chord_seq,
        'chord_segments': segments,
        'n_beats': len(chord_seq),
        'n_segments': len(segments),
    }
