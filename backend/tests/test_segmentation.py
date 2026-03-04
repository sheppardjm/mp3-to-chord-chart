"""Structural tests for segmentation module.

These tests validate invariants of the segmentation functions using synthetic
data. They do NOT require audio files and can run in CI.
"""
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audio.segmentation import compute_k, segment_song, build_sections, DEFAULT_LABELS


# --- compute_k tests ---

def test_compute_k_floor():
    """k should never be less than 4 (floor)."""
    assert compute_k(30.0, 50) == 4   # int(30/30)=1, but floor is 4
    assert compute_k(60.0, 100) == 4  # int(60/30)=2, but floor is 4
    assert compute_k(90.0, 160) == 4  # int(90/30)=3, but floor is 4

def test_compute_k_cap_12():
    """k should never exceed 12."""
    assert compute_k(600.0, 1000) == 12  # int(600/30)=20, capped at 12
    assert compute_k(900.0, 1500) == 12  # int(900/30)=30, capped at 12

def test_compute_k_cap_n_beats():
    """k should never exceed n_beats - 1."""
    assert compute_k(300.0, 5) == 4  # int(300/30)=10, but n_beats-1=4
    assert compute_k(300.0, 3) == 2  # min(12, 10, 2) = 2

def test_compute_k_normal():
    """Normal case: k = int(duration_s / 30)."""
    assert compute_k(150.0, 300) == 5  # int(150/30) = 5
    assert compute_k(240.0, 400) == 8  # int(240/30) = 8
    assert compute_k(360.0, 600) == 12 # int(360/30) = 12, capped at 12


# --- segment_song tests ---

def test_segment_song_returns_ndarray():
    """segment_song must return a numpy array."""
    chroma = np.random.rand(12, 200)
    bounds = segment_song(chroma, 120.0)
    assert isinstance(bounds, np.ndarray)

def test_segment_song_starts_at_zero():
    """First boundary must always be beat 0."""
    chroma = np.random.rand(12, 200)
    bounds = segment_song(chroma, 120.0)
    assert bounds[0] == 0

def test_segment_song_boundaries_within_range():
    """All boundary indices must be < n_beats."""
    n_beats = 200
    chroma = np.random.rand(12, n_beats)
    bounds = segment_song(chroma, 120.0)
    assert all(b < n_beats for b in bounds)

def test_segment_song_boundaries_sorted():
    """Boundary indices must be in ascending order."""
    chroma = np.random.rand(12, 200)
    bounds = segment_song(chroma, 120.0)
    for i in range(1, len(bounds)):
        assert bounds[i] > bounds[i - 1], f"Not sorted at index {i}: {bounds[i-1]} >= {bounds[i]}"

def test_segment_song_min_sections_90s():
    """A song > 90 seconds must produce >= 2 sections (Success Criterion 1)."""
    # ~160 beats at ~107 BPM for ~90s
    chroma = np.random.rand(12, 160)
    bounds = segment_song(chroma, 91.0)
    assert len(bounds) >= 2, f"Only {len(bounds)} sections for 91s song"

def test_segment_song_min_sections_240s():
    """A 240s song should produce multiple sections."""
    chroma = np.random.rand(12, 430)
    bounds = segment_song(chroma, 240.0)
    assert len(bounds) >= 4, f"Only {len(bounds)} sections for 240s song"

def test_segment_song_boundaries_are_beat_aligned():
    """All boundaries are beat indices (integers), proving beat alignment (SC2)."""
    chroma = np.random.rand(12, 200)
    bounds = segment_song(chroma, 120.0)
    for b in bounds:
        assert isinstance(int(b), int)  # numpy int converts to Python int
        assert b == int(b), f"Boundary {b} is not an integer"


# --- DEFAULT_LABELS tests ---

def test_default_labels_count():
    """Must have at least 12 labels for cycling."""
    assert len(DEFAULT_LABELS) >= 12

def test_default_labels_format():
    """Labels must follow 'Section X' format (SC3)."""
    for label in DEFAULT_LABELS:
        assert label.startswith('Section '), f"Label '{label}' does not start with 'Section '"


# --- build_sections tests ---

def test_build_sections_count():
    """Number of sections must equal number of boundaries."""
    bounds = np.array([0, 50, 100, 150])
    beat_times = list(np.arange(200) * 0.5)
    chord_seq = ['G:maj'] * 200
    sections = build_sections(bounds, beat_times, chord_seq)
    assert len(sections) == 4

def test_build_sections_required_keys():
    """Each section must have 'label', 'start', 'chord_sequence' (SC4)."""
    bounds = np.array([0, 50, 100])
    beat_times = list(np.arange(150) * 0.5)
    chord_seq = ['G:maj'] * 75 + ['C:maj'] * 75
    sections = build_sections(bounds, beat_times, chord_seq)
    for s in sections:
        assert 'label' in s, f"Missing 'label' in section"
        assert 'start' in s, f"Missing 'start' in section"
        assert 'chord_sequence' in s, f"Missing 'chord_sequence' in section"

def test_build_sections_labels_assigned():
    """Sections must have default labels in order (SC3)."""
    bounds = np.array([0, 50, 100])
    beat_times = list(np.arange(150) * 0.5)
    chord_seq = ['G:maj'] * 150
    sections = build_sections(bounds, beat_times, chord_seq)
    assert sections[0]['label'] == 'Section A'
    assert sections[1]['label'] == 'Section B'
    assert sections[2]['label'] == 'Section C'

def test_build_sections_start_times():
    """Section start times must match the beat time at the boundary."""
    bounds = np.array([0, 50, 100])
    beat_times = list(np.arange(150) * 0.5)
    chord_seq = ['G:maj'] * 150
    sections = build_sections(bounds, beat_times, chord_seq)
    assert sections[0]['start'] == 0.0
    assert sections[1]['start'] == 25.0
    assert sections[2]['start'] == 50.0

def test_build_sections_chord_sequence_collapsed():
    """Chord sequences within sections must be collapsed (no adjacent duplicates)."""
    bounds = np.array([0, 50, 100])
    beat_times = list(np.arange(150) * 0.5)
    chord_seq = ['G:maj'] * 50 + ['C:maj'] * 25 + ['D:maj'] * 25 + ['G:maj'] * 50
    sections = build_sections(bounds, beat_times, chord_seq)
    for s in sections:
        cs = s['chord_sequence']
        for j in range(1, len(cs)):
            assert cs[j]['chord'] != cs[j-1]['chord'], \
                f"Adjacent duplicate chord in section {s['label']}: {cs[j]['chord']}"

def test_build_sections_chord_sequence_nonempty():
    """Every section must have at least one chord entry."""
    bounds = np.array([0, 50, 100, 150])
    beat_times = list(np.arange(200) * 0.5)
    chord_seq = ['G:maj'] * 200
    sections = build_sections(bounds, beat_times, chord_seq)
    for s in sections:
        assert len(s['chord_sequence']) >= 1, \
            f"Empty chord_sequence in section {s['label']}"

def test_build_sections_chord_entry_keys():
    """Each chord entry must have 'chord' and 'time' keys."""
    bounds = np.array([0, 50])
    beat_times = list(np.arange(100) * 0.5)
    chord_seq = ['G:maj'] * 50 + ['C:maj'] * 50
    sections = build_sections(bounds, beat_times, chord_seq)
    for s in sections:
        for entry in s['chord_sequence']:
            assert 'chord' in entry, f"Missing 'chord' key in chord entry"
            assert 'time' in entry, f"Missing 'time' key in chord entry"

def test_build_sections_out_of_bounds_filter():
    """Boundaries beyond len(beat_times) should be filtered out."""
    bounds = np.array([0, 50, 100, 999])  # 999 is out of bounds
    beat_times = list(np.arange(120) * 0.5)
    chord_seq = ['G:maj'] * 120
    sections = build_sections(bounds, beat_times, chord_seq)
    # 999 is filtered, so only 3 sections (at 0, 50, 100)
    assert len(sections) == 3

def test_build_sections_label_cycling():
    """Labels should cycle through DEFAULT_LABELS if more sections than labels."""
    # Create enough boundaries to exceed 12 labels
    bounds = np.array(list(range(0, 140, 10)))  # 14 boundaries
    beat_times = list(np.arange(150) * 0.5)
    chord_seq = ['G:maj'] * 150
    sections = build_sections(bounds, beat_times, chord_seq)
    assert len(sections) == 14
    assert sections[12]['label'] == 'Section A'  # wraps around
    assert sections[13]['label'] == 'Section B'

def test_build_sections_multi_chord_section():
    """A section with multiple different chords should have them all in collapsed sequence."""
    bounds = np.array([0, 80])
    beat_times = list(np.arange(100) * 0.5)
    # First section: G, G, C, C, D, D, Em, Em (repeated) -- 4 unique chords in 80 beats
    pattern = ['G:maj'] * 20 + ['C:maj'] * 20 + ['D:maj'] * 20 + ['E:min'] * 20
    chord_seq = pattern + ['G:maj'] * 20  # second section is all G
    sections = build_sections(bounds, beat_times, chord_seq)
    assert len(sections[0]['chord_sequence']) == 4  # G, C, D, Em collapsed
    assert sections[0]['chord_sequence'][0]['chord'] == 'G:maj'
    assert sections[0]['chord_sequence'][1]['chord'] == 'C:maj'
    assert sections[0]['chord_sequence'][2]['chord'] == 'D:maj'
    assert sections[0]['chord_sequence'][3]['chord'] == 'E:min'


def run_all_tests():
    """Run all tests and report results."""
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
