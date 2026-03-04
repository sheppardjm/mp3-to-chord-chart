"""Key detection via Krumhansl-Schmuckler algorithm with enharmonic naming."""
import librosa
import numpy as np
import scipy.linalg
from scipy.stats import zscore


# Krumhansl-Schmuckler key profiles (psychoacoustic experiment data)
KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

# Chromatic root names (C=0 through B=11).
# Uses flats for semitones on the flat side of the circle of fifths,
# F# for the tritone (semitone 6). Matches standard music theory conventions.
ROOTS = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']


def detect_key(y_harmonic: np.ndarray, sr: int = 22050) -> str:
    """
    Detect the musical key of an audio signal using Krumhansl-Schmuckler
    correlation over chroma_cqt features.

    Args:
        y_harmonic: Harmonic component of the audio signal (from HPSS).
                    Must NOT be raw audio — use y_harmonic from load_audio().
        sr: Sample rate (default 22050, matching load_audio output).

    Returns:
        Key string in "ROOT:mode" format, e.g. "G:maj" or "Bb:min".
        This format is compatible with librosa.key_to_notes().
    """
    # Extract chromagram from harmonic signal (CQT for pitch-aligned bins)
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr)

    # Sum across time -> 12-element pitch-class energy vector
    chroma_mean = chroma.mean(axis=1)

    # Normalize all profiles to zero mean, unit variance
    chroma_z = zscore(chroma_mean)
    major_z = zscore(KS_MAJOR)
    minor_z = zscore(KS_MINOR)

    # Circulant matrices: all 12 rotations of each profile (vectorized)
    major_circulant = scipy.linalg.circulant(major_z)
    minor_circulant = scipy.linalg.circulant(minor_z)

    # Correlation scores for all 24 keys (12 major + 12 minor)
    major_scores = major_circulant.T.dot(chroma_z)
    minor_scores = minor_circulant.T.dot(chroma_z)

    # Find best key
    best_major_idx = int(np.argmax(major_scores))
    best_minor_idx = int(np.argmax(minor_scores))

    if major_scores[best_major_idx] >= minor_scores[best_minor_idx]:
        return f"{ROOTS[best_major_idx]}:maj"
    else:
        return f"{ROOTS[best_minor_idx]}:min"


def get_note_names(key: str, unicode: bool = False) -> list[str]:
    """
    Get the 12 note names spelled correctly for the given key.

    Uses librosa.key_to_notes() which applies circle-of-fifths rules:
    flat-key tonics produce flat spellings (Bb, Eb, Ab),
    sharp-key tonics produce sharp spellings (F#, C#, G#).

    Args:
        key: Key string in "ROOT:mode" format (e.g. "Bb:maj", "G:min").
        unicode: If True, use unicode accidentals. False (default) uses
                 ASCII b/# for downstream string processing.

    Returns:
        List of 12 note name strings starting from C.
    """
    return librosa.key_to_notes(key, unicode=unicode)
