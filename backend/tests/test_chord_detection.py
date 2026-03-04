"""Structural tests for chord detection pipeline.

These tests validate invariants of the pipeline functions using synthetic data.
They do NOT require audio files and can run in CI.
"""
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audio.chord_detection import (
    HOP, NOTES, build_chord_templates, detect_chords,
    collapse_chords, measure_accuracy,
)


def test_hop_constant():
    assert HOP == 1024

def test_notes_list():
    assert len(NOTES) == 12
    assert NOTES[0] == 'C'
    assert NOTES[7] == 'G'
    assert NOTES[6] == 'F#'
    assert NOTES[10] == 'Bb'

def test_build_chord_templates_count():
    names, matrix = build_chord_templates()
    assert len(names) == 36
    assert matrix.shape == (36, 12)

def test_build_chord_templates_normalized():
    _, matrix = build_chord_templates()
    norms = np.linalg.norm(matrix, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-6)

def test_build_chord_templates_names():
    names, _ = build_chord_templates()
    valid_suffixes = {':maj', ':min', ':7'}
    for name in names:
        assert ':' in name
        suffix = name[name.index(':'):]
        assert suffix in valid_suffixes

def test_build_chord_templates_all_roots():
    names, _ = build_chord_templates()
    roots = set(name.split(':')[0] for name in names)
    assert roots == set(NOTES)

def test_detect_chords_output_length():
    names, matrix = build_chord_templates()
    chroma = np.random.rand(12, 50) + 0.1
    chords = detect_chords(chroma, names, matrix)
    assert len(chords) == 50

def test_detect_chords_valid_names():
    names, matrix = build_chord_templates()
    chroma = np.random.rand(12, 30) + 0.1
    chords = detect_chords(chroma, names, matrix)
    name_set = set(names)
    for chord in chords:
        assert chord in name_set

def test_detect_chords_pure_c_major():
    names, matrix = build_chord_templates()
    chroma = np.zeros((12, 20))
    chroma[0, :] = 1.0; chroma[4, :] = 1.0; chroma[7, :] = 1.0
    chords = detect_chords(chroma, names, matrix)
    from collections import Counter
    most_common = Counter(chords).most_common(1)[0][0]
    assert most_common == 'C:maj'

def test_detect_chords_pure_g_major():
    names, matrix = build_chord_templates()
    chroma = np.zeros((12, 20))
    chroma[7, :] = 1.0; chroma[11, :] = 1.0; chroma[2, :] = 1.0
    chords = detect_chords(chroma, names, matrix)
    from collections import Counter
    most_common = Counter(chords).most_common(1)[0][0]
    assert most_common == 'G:maj'

def test_collapse_no_duplicates():
    chords = ['C:maj', 'C:maj', 'G:maj', 'G:maj', 'G:maj', 'C:maj']
    times = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5])
    segments = collapse_chords(chords, times)
    for i in range(1, len(segments)):
        assert segments[i]['chord'] != segments[i-1]['chord']

def test_collapse_preserves_first_timestamp():
    chords = ['C:maj', 'C:maj', 'G:maj', 'G:maj']
    times = np.array([0.0, 0.5, 1.0, 1.5])
    segments = collapse_chords(chords, times)
    assert len(segments) == 2
    assert segments[0] == {'chord': 'C:maj', 'time': 0.0}
    assert segments[1] == {'chord': 'G:maj', 'time': 1.0}

def test_collapse_single_chord():
    chords = ['G:maj'] * 100
    times = np.arange(100) * 0.5
    segments = collapse_chords(chords, times)
    assert len(segments) == 1
    assert segments[0]['chord'] == 'G:maj'

def test_collapse_all_different():
    chords = ['C:maj', 'D:min', 'E:min', 'F:maj']
    times = np.array([0.0, 1.0, 2.0, 3.0])
    segments = collapse_chords(chords, times)
    assert len(segments) == 4

def test_measure_accuracy_perfect():
    detected = ['C:maj', 'G:maj', 'D:min']
    reference = ['C:maj', 'G:maj', 'D:min']
    result = measure_accuracy(detected, reference)
    assert result['exact_accuracy'] == 1.0
    assert result['root_accuracy'] == 1.0
    assert result['n_compared'] == 3

def test_measure_accuracy_root_match():
    detected = ['C:maj', 'G:7', 'D:min']
    reference = ['C:min', 'G:maj', 'D:maj']
    result = measure_accuracy(detected, reference)
    assert result['exact_accuracy'] == 0.0
    assert result['root_accuracy'] == 1.0

def test_measure_accuracy_empty():
    result = measure_accuracy([], [])
    assert result['exact_accuracy'] == 0.0
    assert result['n_compared'] == 0

def test_measure_accuracy_length_mismatch():
    detected = ['C:maj', 'G:maj', 'D:min', 'A:min']
    reference = ['C:maj', 'G:maj']
    result = measure_accuracy(detected, reference)
    assert result['n_compared'] == 2
    assert result['exact_accuracy'] == 1.0

def run_all_tests():
    tests = [(name, func) for name, func in globals().items()
             if name.startswith('test_') and callable(func)]
    passed = 0
    failed = 0
    for name, func in sorted(tests):
        try:
            func()
            print(f"  PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    if failed > 0:
        raise SystemExit(1)
    return passed, failed

if __name__ == '__main__':
    run_all_tests()
