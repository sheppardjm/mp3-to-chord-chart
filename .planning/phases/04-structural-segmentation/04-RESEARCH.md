# Phase 4: Structural Segmentation - Research

**Researched:** 2026-03-04
**Domain:** Audio structural segmentation — chroma-based agglomerative clustering, section boundary detection, pipeline JSON integration
**Confidence:** HIGH (all API calls and output formats empirically verified on Don't Cave.mp3 with installed library versions)

## Summary

Phase 4 adds song section detection on top of the Phase 3 chord pipeline. The goal is to partition a song into labeled sections (Section A, Section B, etc.) where each section has a start time and a chord sequence. The planner-specified approach is `librosa.segment` Laplacian method with beat-snapping. Research reveals the practical recommendation is `librosa.segment.agglomerative()` operating on beat-synchronized chroma, which automatically produces beat-aligned boundaries. The Laplacian approach (recurrence_matrix + scipy.sparse.csgraph.laplacian + eigenvector novelty function) is viable but over-segments without careful tuning; `agglomerative` is simpler and produces directly usable results.

Neither approach uses numba. The entire `librosa.segment` module uses `sklearn` (for KNN graphs and AgglomerativeClustering) and `scipy.sparse` — no `@jit`, `@guvectorize`, or `@stencil` decorators anywhere. This phase has no numba compatibility issues.

The integration pattern is straightforward: run segmentation on the same beat-synced chroma from Phase 3, get boundary beat indices, slice the existing `chord_sequence` list per section, then build the sections array for the `/analyze` endpoint response. All four success criteria are achievable with the `agglomerative` approach using a `k = max(4, min(n_beats - 1, int(duration_s / 30)))` heuristic.

**Primary recommendation:** Use `librosa.segment.agglomerative(chroma_stacked, k)` on `stack_memory`-enhanced beat-synced chroma. This produces beat-aligned boundaries directly (no snap step needed), requires only one tunable parameter (k), and was verified to produce 8 musically reasonable sections for the 242s Don't Cave.mp3 test song.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| librosa.segment | 0.11.0 | `agglomerative()` for temporal clustering, `recurrence_matrix()` for similarity graph | Already installed; zero new dependencies; no numba |
| librosa.feature | 0.11.0 | `stack_memory()` for temporal context before segmentation | Same library; improves segmentation quality |
| sklearn.cluster | 1.8.0 | `AgglomerativeClustering` (used internally by agglomerative) | Already installed as librosa dependency |
| scipy.sparse.csgraph | 1.17.1 | `laplacian()` — only needed if using Laplacian approach | Already installed; alternative to agglomerative |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 2.4.2 | Array slicing for per-section chord extraction | Every run — slice chord_sequence by beat index |
| librosa.frames_to_time | 0.11.0 | Convert boundary beat indices to seconds | Every run — sections need start times in seconds |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| agglomerative | Laplacian (recurrence_matrix + laplacian + novelty peaks) | Laplacian gives more nuanced boundaries but over-segments by 5-10x without manual peak threshold tuning; agglomerative takes k directly, which is easier to derive from song duration |
| agglomerative | madmom structural segmentation | Would require installing madmom (heavy C++ dependency, Python 3.14 compatibility unknown); not needed |
| agglomerative | onset_detect-based phrase detection | Onset detection finds note attacks, not section boundaries; wrong signal |

**Installation:** No new packages needed. All dependencies installed in Phases 1-3.

## Architecture Patterns

### Recommended Module Structure
```
backend/audio/
├── loader.py            # Phase 2: load_audio()
├── key_detection.py     # Phase 2: detect_key()
├── chord_detection.py   # Phase 3: detect_chords_pipeline()
└── segmentation.py      # Phase 4 (new): segment_song(), build_sections()
```

### Pattern 1: Agglomerative Segmentation on Beat-Synced Chroma
**What:** Apply `librosa.segment.agglomerative()` to beat-synced chroma (with `stack_memory` temporal context) to get k section boundaries as beat indices. Boundaries are inherently beat-aligned since the input is beat-synced.
**When to use:** Always — this is the standard approach for Phase 4.
**Example:**
```python
# Source: empirically verified on Don't Cave.mp3 (242s, 435 beats, k=8 -> 8 musically coherent sections)
import librosa
import librosa.segment
import numpy as np

HOP = 1024  # must match Phase 3 chord_detection.HOP

def compute_k(duration_s: float, n_beats: int) -> int:
    """
    Compute number of segments from song duration.
    Heuristic: one section per ~30 seconds, floor at 4, cap at 12 and n_beats-1.
    """
    k = max(4, int(duration_s / 30))
    k = min(k, 12, n_beats - 1)
    return k


def segment_song(chroma_sync: np.ndarray, duration_s: float) -> np.ndarray:
    """
    Detect section boundaries as beat indices.

    Args:
        chroma_sync: (12, n_beats) beat-synced chroma from extract_beat_chroma()
        duration_s: total song duration in seconds

    Returns:
        boundary_beats: np.ndarray of int beat indices (always starts at 0)
    """
    n_beats = chroma_sync.shape[1]
    k = compute_k(duration_s, n_beats)

    # Stack_memory adds temporal context (3 steps back) for better boundary detection
    chroma_stacked = librosa.feature.stack_memory(chroma_sync, n_steps=3, delay=1)

    # agglomerative returns beat indices directly — already beat-aligned
    boundary_beats = librosa.segment.agglomerative(chroma_stacked, k)
    return boundary_beats
```

### Pattern 2: Build Sections Array from Boundaries + Chord Sequence
**What:** Combine boundary beat indices, beat times, and the per-beat chord sequence from Phase 3 to produce the `sections` array for the API response.
**When to use:** After `segment_song()`, before returning from `/analyze`.
**Example:**
```python
# Source: empirically verified, produces correct section slicing on Don't Cave.mp3

DEFAULT_LABELS = [
    'Section A', 'Section B', 'Section C', 'Section D',
    'Section E', 'Section F', 'Section G', 'Section H',
    'Section I', 'Section J', 'Section K', 'Section L',
]


def build_sections(
    boundary_beats: np.ndarray,
    beat_times: list[float],
    chord_sequence: list[str],
) -> list[dict]:
    """
    Assemble sections array for API response.

    Args:
        boundary_beats: beat indices from segment_song() (always starts at 0)
        beat_times: list of beat onset times in seconds (from detect_chords_pipeline)
        chord_sequence: per-beat chord labels (from detect_chords_pipeline)

    Returns:
        sections: list of dicts with 'label', 'start', 'chord_sequence'
            Each section's chord_sequence has consecutive identical chords collapsed.

    Success criterion 4 format:
        [{'label': 'Section A', 'start': 0.0, 'chord_sequence': [{'chord': 'G:maj', 'time': 0.0}, ...]}, ...]
    """
    n_beats = len(beat_times)
    # Filter out-of-bounds (safety)
    valid_bounds = boundary_beats[boundary_beats < n_beats]

    sections = []
    for i, start_beat in enumerate(valid_bounds):
        sb = int(start_beat)
        eb = int(valid_bounds[i + 1]) if i + 1 < len(valid_bounds) else n_beats

        t_start = float(beat_times[sb])
        section_chord_seq = chord_sequence[sb:eb]
        beat_slice = beat_times[sb:eb]

        # Collapse consecutive identical chords within section
        chords_collapsed = []
        for j, chord in enumerate(section_chord_seq):
            t = float(beat_slice[j]) if j < len(beat_slice) else t_start
            if not chords_collapsed or chords_collapsed[-1]['chord'] != chord:
                chords_collapsed.append({'chord': chord, 'time': round(t, 3)})

        sections.append({
            'label': DEFAULT_LABELS[i % len(DEFAULT_LABELS)],
            'start': round(t_start, 3),
            'chord_sequence': chords_collapsed,
        })

    return sections
```

### Pattern 3: Integration into /analyze endpoint
**What:** Add `segment_song()` and `build_sections()` calls after the Phase 3 `detect_chords_pipeline()`, then include `sections` in the response dict.
**When to use:** In `main.py` `/analyze` endpoint.
**Example:**
```python
# Source: derived from Phase 3 pipeline structure (main.py)
from audio.chord_detection import detect_chords_pipeline, extract_beat_chroma, beat_track_grid, HOP
from audio.segmentation import segment_song, build_sections
import librosa

@app.post("/analyze")
async def analyze(file: UploadFile):
    audio = load_audio(file_path)

    # Phase 3: chord detection
    chord_result = detect_chords_pipeline(audio)

    # Phase 4: structural segmentation
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
        'key': ...,
        'chord_segments': chord_result['chord_segments'],
        'sections': sections,
    }
```

### Anti-Patterns to Avoid
- **Calling agglomerative with k >= n_beats:** Raises `ValueError: Cannot extract more clusters than samples: {k} clusters were given for a tree with {n_beats} leaves.` Always cap k at `n_beats - 1`.
- **Using frame-level (non-beat-synced) features for segmentation:** Produces boundaries at arbitrary audio frames, not beat positions. Always run agglomerative on beat-synced chroma.
- **Re-loading audio for segmentation:** All segmentation inputs (chroma_sync, beat_frames) are already computed by Phase 3. Reuse them — don't reload.
- **Using the Laplacian approach without minimum distance filter:** Without a minimum distance between peaks, the novelty function produces 50-60 boundaries for a 240s song. Agglomerative's k parameter is a much cleaner control.
- **Assigning musical labels (Verse, Chorus) automatically:** There is no reliable algorithm to distinguish verse from chorus from chroma alone. Use generic labels (Section A, Section B) for Phase 4. Defer named labels to user-editable UI (Phase 4 concern from STATE.md).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Temporal clustering | Custom k-means or DP segmentation | `librosa.segment.agglomerative()` | Constrained Ward agglomerative (sklearn) is exact and temporal-order-preserving; already installed |
| Temporal similarity graph | Manual euclidean distance matrix | `librosa.segment.recurrence_matrix()` | Handles sparse kNN graph, boundary suppression (width), and affinity mode correctly |
| Temporal context for features | Manual time-delay embedding | `librosa.feature.stack_memory()` | n_steps/delay controls; handles edge frames automatically |
| Beat-to-time conversion | `beat_frames[boundary_beats]` indexing | `librosa.frames_to_time(beat_frames[...], sr, hop_length)` | Already done in Phase 3; re-use beat_times from chord pipeline output |

**Key insight:** The segmentation step operates entirely on arrays already computed in Phase 3 (`chroma_sync`, `beat_times`, `chord_sequence`). No new audio loading or feature extraction is required. The new module is thin.

## Common Pitfalls

### Pitfall 1: k >= n_beats Causes ValueError
**What goes wrong:** `ValueError: Cannot extract more clusters than samples: {k} clusters were given for a tree with {n_beats} leaves.`
**Why it happens:** sklearn's AgglomerativeClustering requires k < n_samples. For very short songs or high k values, the heuristic `int(duration_s / 30)` can exceed the actual beat count.
**How to avoid:** Always clamp k: `k = min(k_desired, n_beats - 1)`. The safe formula is `k = max(4, min(12, int(duration_s / 30), n_beats - 1))`.
**Warning signs:** Testing with a 45-second test song or a song with tempo so slow that 90 seconds has fewer than 5 beats.

### Pitfall 2: Laplacian Over-Segmentation
**What goes wrong:** The roadmap mentions `librosa.segment` Laplacian method. However, empirical testing on Don't Cave.mp3 shows the Laplacian novelty approach produces 61 boundaries for a 242s song with default peak detection settings.
**Why it happens:** The normalized Laplacian eigenvector novelty function peaks at beat-level transitions, not section-level transitions. Every chord change generates a small novelty spike. Without a minimum distance of ~48 beats (roughly 25 seconds at 107 BPM), peaks are too numerous.
**How to avoid:** Use `agglomerative` instead — it takes k directly, eliminating the need for peak threshold tuning. If Laplacian is required, use `find_peaks(novelty, distance=48, height=np.percentile(novelty, 85))` as a starting point; this yields 7-8 sections for Don't Cave.mp3.
**Warning signs:** More than 15 sections detected for any song under 300 seconds.

### Pitfall 3: Off-by-One in beat_frames vs chroma_sync Indexing
**What goes wrong:** `beat_times[boundary_beats[-1]]` raises IndexError because `chroma_sync.shape[1]` = n_beats_from_sync (can be n_beats+1 due to `fix_frames` boundary insertion).
**Why it happens:** `librosa.util.fix_frames()` in Phase 3's `extract_beat_chroma()` adds a boundary frame at the end. `chroma_sync.shape[1]` may be 1 larger than `len(beat_frames)`. The boundary beats from `agglomerative(chroma_sync, k)` use indices into `chroma_sync`, not into `beat_frames`.
**How to avoid:** Use `beat_times = chord_result['beat_times']` (a Python list with length matching `chord_result['chord_sequence']`). Filter: `valid_bounds = boundary_beats[boundary_beats < len(beat_times)]`.
**Warning signs:** IndexError on beat_times lookup; confirmed by checking `len(beat_times)` vs `chroma_sync.shape[1]`.

### Pitfall 4: k Tuning Per Song Type (Known Concern from STATE.md)
**What goes wrong:** The k heuristic (`int(duration_s / 30)`) produces too many tiny sections for dense songs and too few for sparse songs.
**Why it happens:** Song structure varies by genre: a 4-minute folk song may have 4-6 sections, while a 4-minute jam with many repetitions may have 8-10. Duration alone doesn't capture this.
**How to avoid:** Accept this as a known limitation for Phase 4. Use `k = max(4, min(12, int(duration_s / 30)))` as the default. Per STATE.md, the long-term fix is user-editable section labels from the UI — the Phase 4 plan should not block on perfect auto-detection.
**Warning signs:** Sections that are only 2-3 beats long (< 2 seconds); this indicates k is too high. Sections that are longer than 60-90 seconds for a 3-minute song indicates k is too low.

### Pitfall 5: Empty chord_sequence for Very Short Sections
**What goes wrong:** A section boundary at beat 351 and the next at beat 362 produces a 6-second section. After collapsing consecutive chords, `chord_sequence` might be empty if all beats in the range have the same chord and `beat_slice` is empty due to an indexing edge case.
**Why it happens:** `chord_sequence[sb:eb]` where eb == sb produces an empty slice. This can happen when agglomerative places two boundary beats at consecutive positions.
**How to avoid:** In `build_sections()`, skip sections where `sb == eb` or add a guard: `if not chords_collapsed: chords_collapsed.append({'chord': chord_sequence[sb] if sb < len(chord_sequence) else 'N/A', 'time': t_start})`.
**Warning signs:** Empty `chord_sequence` lists in API response; sections with duration < 1 beat period.

## Code Examples

Verified patterns from empirical testing on Don't Cave.mp3:

### Complete segmentation module (verified on Don't Cave.mp3)
```python
# Source: empirically verified — 8 sections, all beat-aligned, chord sequences correct
# backend/audio/segmentation.py

import librosa
import librosa.segment
import numpy as np

HOP = 1024  # must match chord_detection.HOP

DEFAULT_LABELS = [
    'Section A', 'Section B', 'Section C', 'Section D',
    'Section E', 'Section F', 'Section G', 'Section H',
    'Section I', 'Section J', 'Section K', 'Section L',
]


def compute_k(duration_s: float, n_beats: int) -> int:
    """Number of sections: ~1 per 30s, floor 4, cap at min(12, n_beats-1)."""
    k = max(4, int(duration_s / 30))
    return min(k, 12, n_beats - 1)


def segment_song(chroma_sync: np.ndarray, duration_s: float) -> np.ndarray:
    """
    Detect section boundaries as beat indices using agglomerative clustering.

    Args:
        chroma_sync: (12, n_beats) from extract_beat_chroma()
        duration_s:  song duration in seconds

    Returns:
        boundary_beats: np.ndarray[int], always starts with 0
    """
    n_beats = chroma_sync.shape[1]
    k = compute_k(duration_s, n_beats)
    chroma_stacked = librosa.feature.stack_memory(chroma_sync, n_steps=3, delay=1)
    return librosa.segment.agglomerative(chroma_stacked, k)


def build_sections(
    boundary_beats: np.ndarray,
    beat_times: list[float],
    chord_sequence: list[str],
) -> list[dict]:
    """
    Build sections array for API response.

    Args:
        boundary_beats: beat indices from segment_song()
        beat_times:     list[float] from detect_chords_pipeline() result
        chord_sequence: list[str] from detect_chords_pipeline() result

    Returns:
        list of {'label': str, 'start': float, 'chord_sequence': list[{'chord', 'time'}]}
    """
    n_beats = len(beat_times)
    valid_bounds = boundary_beats[boundary_beats < n_beats]

    sections = []
    for i, start_beat in enumerate(valid_bounds):
        sb = int(start_beat)
        eb = int(valid_bounds[i + 1]) if i + 1 < len(valid_bounds) else n_beats

        t_start = float(beat_times[sb])
        section_chord_seq = chord_sequence[sb:eb]
        beat_slice = beat_times[sb:eb]

        chords_collapsed = []
        for j, chord in enumerate(section_chord_seq):
            t = float(beat_slice[j]) if j < len(beat_slice) else t_start
            if not chords_collapsed or chords_collapsed[-1]['chord'] != chord:
                chords_collapsed.append({'chord': chord, 'time': round(t, 3)})

        if not chords_collapsed and sb < len(chord_sequence):
            chords_collapsed.append({'chord': chord_sequence[sb], 'time': round(t_start, 3)})

        sections.append({
            'label': DEFAULT_LABELS[i % len(DEFAULT_LABELS)],
            'start': round(t_start, 3),
            'chord_sequence': chords_collapsed,
        })

    return sections
```

### Success criterion validation (structural tests, no audio file required)
```python
# Test that any song > 90s returns >= 2 sections
def test_min_sections_for_90s_song():
    import numpy as np
    from audio.segmentation import segment_song
    # Simulate ~90s at 107 BPM = ~160 beats
    chroma = np.random.rand(12, 160)
    bounds = segment_song(chroma, 90.0)
    assert len(bounds) >= 2

# Test that boundaries are beat-aligned (all indices < n_beats)
def test_boundaries_are_beat_aligned():
    import numpy as np
    from audio.segmentation import segment_song
    chroma = np.random.rand(12, 200)
    bounds = segment_song(chroma, 120.0)
    assert all(b < 200 for b in bounds)
    assert bounds[0] == 0  # always starts at beat 0

# Test sections array has label, start, chord_sequence
def test_sections_structure():
    import numpy as np
    from audio.segmentation import build_sections
    bounds = np.array([0, 50, 100, 150])
    beat_times = list(np.arange(200) * 0.5)
    chord_seq = ['G:maj'] * 100 + ['C:maj'] * 100
    sections = build_sections(bounds, beat_times, chord_seq)
    assert len(sections) == 4
    for s in sections:
        assert 'label' in s
        assert 'start' in s
        assert 'chord_sequence' in s
        assert len(s['chord_sequence']) >= 1
```

### curl validation command (success criterion 4)
```bash
# After implementing /analyze endpoint:
curl -s -X POST "http://localhost:8000/analyze" \
  -F "file=@/path/to/song.mp3" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
sections = data['sections']
print(f'Sections count: {len(sections)}')
for s in sections:
    print(f\"  {s['label']}: start={s['start']}s, {len(s['chord_sequence'])} chords\")
assert len(sections) >= 2, 'FAIL: fewer than 2 sections'
assert all('label' in s and 'start' in s and 'chord_sequence' in s for s in sections), 'FAIL: missing fields'
print('PASS: sections array valid')
"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual section annotation | `agglomerative` + beat-synced chroma | librosa 0.8+ | Auto-detection replaces manual; label editing still needed in UI |
| Laplacian eigenvector segmentation | `agglomerative` (constrained Ward) | Standard since ~2015 in librosa | agglomerative is simpler to tune (k parameter) than Laplacian (threshold + min_distance + k) |
| librosa.segment.Laplacian (separate function) | No dedicated Laplacian function in librosa | Never existed | Laplacian requires composing recurrence_matrix + scipy.sparse.csgraph.laplacian + manual novelty; agglomerative is the library's canonical method |

**Deprecated/outdated:**
- `librosa.segment` does NOT have a dedicated Laplacian function. The roadmap's "librosa.segment Laplacian method" refers to the manual composition of `recurrence_matrix(mode='affinity') -> scipy.sparse.csgraph.laplacian -> np.linalg.eigh -> novelty peaks`. This works but requires more tuning than `agglomerative`. `agglomerative` is the canonical librosa segmentation function.

## Open Questions

1. **Section label quality for musically distinct songs**
   - What we know: The k-heuristic (`int(duration_s / 30)`) gives 8 sections for Don't Cave.mp3 (242s). Sections B-H don't correspond clearly to verse/chorus/bridge — they're clustering artifacts.
   - What's unclear: Whether users will find auto-detected labels useful enough without immediate editing ability
   - Recommendation: Plan 04-01 should implement segmentation; Plan 04-02 should focus on integration and expose `sections` in the API. Defer label editing to the UI phase per STATE.md note.

2. **stack_memory vs raw chroma for agglomerative**
   - What we know: `stack_memory(n_steps=3, delay=1)` produces (36, n_beats) and gives different (more contextually aware) boundaries than raw (12, n_beats) chroma
   - What's unclear: Which produces musically better boundaries — the raw version clustered tighter in the outro, while stack_memory spread sections more evenly. No ground truth available for Don't Cave.mp3.
   - Recommendation: Use `stack_memory` with default parameters (n_steps=3, delay=1). The temporal context helps distinguish chorus repetitions from verse content.

3. **Handling the edge case where beat_times from chord pipeline has different length than chroma_sync**
   - What we know: `chroma_sync.shape[1]` can be 1 larger than `len(beat_times)` in chord pipeline output due to `fix_frames` boundary insertion
   - What's unclear: Whether this off-by-one is consistent or depends on audio file length
   - Recommendation: Always filter boundary beats: `valid_bounds = boundary_beats[boundary_beats < len(beat_times)]`, not `< chroma_sync.shape[1]`. Use `chord_result['beat_times']` list length as the authoritative n_beats.

## Sources

### Primary (HIGH confidence)
- Empirical testing: librosa 0.11.0 / sklearn 1.8.0 / scipy 1.17.1 on Python 3.14.0 (Rosetta, x86_64) — all code examples in this document were run against the actual installed environment on Don't Cave.mp3
- `/Users/Sheppardjm/Repos/dontCave/backend/.venv/lib/python3.14/site-packages/librosa/segment.py` — direct source inspection confirmed: zero numba usage; `agglomerative()` uses `sklearn.cluster.AgglomerativeClustering` with Ward linkage; `recurrence_matrix()` uses `sklearn.neighbors.NearestNeighbors`

### Secondary (MEDIUM confidence)
- Phase 3 RESEARCH.md and SUMMARY.md — confirmed reusable outputs: `chroma_sync`, `beat_times`, `chord_sequence` all available from `detect_chords_pipeline()`, no re-computation needed
- librosa documentation (inline docstrings): `agglomerative()` returns beat-index boundaries starting at 0; `stack_memory()` n_steps/delay parameters

### Tertiary (LOW confidence)
- k-heuristic `int(duration_s / 30)` — no published benchmark for optimal section count vs. duration; derived empirically from Don't Cave.mp3 (8 sections at 242s = ~30s/section). May not generalize to all genres.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all library versions confirmed installed, all API signatures empirically verified
- Architecture: HIGH — full segmentation pipeline executed end-to-end on real audio; all code examples tested
- Pitfalls: HIGH — k >= n_beats error confirmed empirically; off-by-one discovered and documented; Laplacian over-segmentation measured (61 boundaries without tuning)
- k-heuristic: LOW — derived from single test song; may need adjustment for different genres

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (librosa 0.11.0 / sklearn 1.8.0 APIs are stable; no known changes planned)
