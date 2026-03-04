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
