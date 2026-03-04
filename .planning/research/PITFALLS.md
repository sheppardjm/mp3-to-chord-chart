# Pitfalls Research

**Domain:** Audio chord detection and chord chart generation (web app)
**Researched:** 2026-03-03
**Confidence:** MEDIUM (WebSearch + official librosa docs + MIR research papers; no Context7 available for audio MIR libraries)

---

## Critical Pitfalls

### Pitfall 1: Treating Raw Chroma Features as Chord Labels

**What goes wrong:**
Developers use `librosa.feature.chroma_cqt` or `librosa.feature.chroma_stft` and naively map the highest-energy pitch class to a chord name. This produces wildly inaccurate results — often detecting the wrong chord family entirely — because chroma features are a pitch-class energy distribution, not a chord identifier.

**Why it happens:**
The librosa documentation for chroma features is approachable and produces visually interesting output. Developers see 12 pitch classes, see that a C major chord has energy in C/E/G, and assume template-matching on raw chroma will "just work." Research confirms: "a simple template-based chord estimator using chroma features is not accurate enough to use in practice."

**How to avoid:**
Use a pre-trained chord recognition model rather than raw chroma. Options in order of recommendation:
- `chord-recognition` via `madmom` library (HMM-based, solid baseline)
- `CREMA` (Convolutional and Recurrent Estimators for Music Analysis) — pre-trained, widely cited
- `basic-pitch` (Spotify) for note detection as an intermediate step
- At minimum: apply log compression to chroma, temporal smoothing, and Viterbi decoding (`librosa.sequence.viterbi_discriminative`) before labeling — not just argmax

**Warning signs:**
- Your detected chords change frame-by-frame (every 0.02 seconds) with no smoothing
- Chords detected don't match the key of the song
- Detection shows mostly single-note chords or random root movement

**Phase to address:** Audio Processing phase (before any UI work). Validate chord detection accuracy against 5-10 known songs before building the chart generation layer.

---

### Pitfall 2: MP3 Decompression Memory Explosion

**What goes wrong:**
A 20MB MP3 uploaded by the user decodes to raw PCM audio — often 200–600MB in RAM — before librosa can analyze it. A 5-minute song at 44.1kHz stereo float32 = ~100MB of RAM per file. The Flask/FastAPI process runs out of memory or slows to a crawl, especially if two users upload simultaneously.

**Why it happens:**
Librosa's `load()` function loads the entire file into memory as a numpy ndarray. Developers test with short clips, miss the problem, and only discover it with real songs. The librosa issue tracker has confirmed reports of memory growth over multiple files processed in the same process.

**How to avoid:**
- Call `librosa.load(path, duration=300)` to hard-cap at 5 minutes max
- Downsample on load: `librosa.load(path, sr=22050)` (default) — do not use 44100
- Delete the array explicitly after processing: `del y; import gc; gc.collect()`
- For a personal tool, set a file size limit of 50MB max in Flask (`app.config['MAX_CONTENT_LENGTH']`)
- Stream loading via `soundfile` if processing very long files

**Warning signs:**
- Server slows after processing 3–4 files in a session
- `htop` shows RAM climbing and not releasing between requests
- Processing a 10-minute song takes 2x as long as a 5-minute song

**Phase to address:** Backend setup phase. Establish memory guard rails before wiring up the full pipeline.

---

### Pitfall 3: Blocking the Web Server During Audio Analysis

**What goes wrong:**
Librosa's chroma extraction, beat tracking, and chord classification on a 4-minute MP3 takes 10–60 seconds of CPU. If this runs synchronously in a Flask route handler, the entire server blocks — no other requests can be served, the browser shows a spinning wheel with no feedback, and users may assume the app crashed and re-upload.

**Why it happens:**
Flask's development server is single-threaded by default. Developers test locally with short files, don't notice the freeze, and ship. The blocking becomes visible only with longer songs or concurrent users.

**How to avoid:**
- Run analysis in a background thread or process: use `concurrent.futures.ProcessPoolExecutor` (CPU-bound, needs process not thread)
- Return a job ID immediately, poll for results: `GET /status/<job_id>`
- Show a progress indicator in the UI (even a fake one with known steps: "Analyzing audio...", "Detecting beats...", "Mapping chords...")
- For a personal tool, even a simple spinner with a 30-second timeout is better than silence

**Warning signs:**
- Upload endpoint returns only after analysis completes (no intermediate response)
- Browser shows no activity indicator during processing
- Testing with a 6-minute song causes the dev server to be unresponsive for 45+ seconds

**Phase to address:** Backend architecture phase, before UI integration. The polling pattern must be decided before the frontend is built.

---

### Pitfall 4: Ignoring Beat Alignment for Chord Placement

**What goes wrong:**
Chord detection produces frame-level predictions (e.g., one label per 0.02 seconds). Without beat alignment, the resulting chord chart has chords changing at arbitrary timestamps that don't correspond to musical beats or measures. The chart looks musically wrong — chords listed mid-word, mid-beat, or changing 8 times per second.

**Why it happens:**
Developers focus on getting chord labels right and treat the timing problem as "just formatting." Beat alignment is a separate MIR step that must be explicitly added. Research confirms that temporal alignment can be "very inaccurate" without this step.

**How to avoid:**
- Use `librosa.beat.beat_track()` to get beat timestamps
- Snap frame-level chord predictions to beat-synchronous windows: take the mode or median chord label within each beat interval
- For chord charts: quantize to measure level (group 4 beats), not frame level
- Assumption: chords change on beat boundaries — valid for most pop/rock songs, breaks on jazz or irregular time signatures

**Warning signs:**
- Chord chart shows 50+ different chord timestamps for a 3-minute song
- Chords appear to change mid-syllable in the lyrics alignment
- Detected chords don't line up with any audibly obvious chord change

**Phase to address:** Audio processing phase, immediately after implementing chord detection. Beat sync is not optional.

---

### Pitfall 5: Key Estimation Errors Causing Wrong Chord Names

**What goes wrong:**
The algorithm detects correct pitch content but names chords incorrectly because key context is wrong. For example, in a song in A major, a dominant 7th chord built on E gets labeled as E7 (correct) but may be labeled as Bb7 (enharmonic) or — worse — the key estimation is off entirely, causing the system to label a G chord as F## or a Bb as A#. Users with any musical knowledge immediately distrust the entire output.

**Why it happens:**
Template-based key estimation is fooled by certain chord progressions. Research documents a specific failure: "the presence of E7 chords determined an incorrect key of E-major instead of the actual key of A-major." Enharmonic equivalents (F# vs Gb, Bb vs A#) are musically identical but look wrong depending on key context. Librosa returns pitch classes as integers (0–11) — the developer must decide how to render them as note names.

**How to avoid:**
- Run key estimation (`librosa.feature.tonnetz` or `librosa.key.key` equivalent) first and use it to constrain chord naming
- Pick one enharmonic convention per detected key (sharp keys use sharps, flat keys use flats)
- For the basic-chords-only scope of this project: predefine a mapping of key → chord name conventions
- The MIREX 2024 evaluation framework assumes enharmonic equivalence — accept that F# and Gb are the same chord for display purposes and pick the more common name

**Warning signs:**
- Output shows chords with double sharps or flats (F##, Bbb)
- The detected key changes multiple times within a single song
- Chords labeled with sharps in a song that's clearly in a flat key (Bb, F, C, Gm)

**Phase to address:** Audio processing phase. Key estimation must be done before chord naming, not after.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip beat alignment, use raw frame timestamps | Faster first implementation | Chord chart looks musically illiterate; timestamps meaningless | Never — this is 10 lines of code |
| Use argmax on chroma for chord label | Zero ML dependencies | ~30% accuracy; completely misleads users; requires rewrite | Never for user-facing output |
| Synchronous processing in Flask route | Simpler code | Server blocks; UX is broken for >20s songs | Personal dev testing only |
| Hard-code one chord voicing per diagram | Avoids voicing complexity | Beginners get wrong fingering if song is in non-open position | Acceptable for MVP |
| Skip key estimation, always use sharps | Simpler chord naming | Incorrect notation for flat-key songs (Bb songs show A#) | Never — 5 lines of code to fix |
| Load entire audio file at original sample rate | Zero resampling artifacts | Memory explosion on long files | Never; always set `sr=22050` |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| librosa + MP3 | Assuming librosa handles MP3 natively in all versions | librosa 0.10+ deprecated `audioread` for MP3; requires `ffmpeg` on the system PATH; verify `ffmpeg` is installed in deployment environment |
| librosa `load()` | Not specifying `mono=True` | Stereo files return shape `(2, N)` instead of `(N,)` — breaks all downstream processing that assumes 1D array |
| librosa + numpy | Using old numpy API with new librosa | librosa 0.10+ requires numpy >=1.17; pin dependency versions in `requirements.txt` |
| Flask file uploads | No file type validation | Accept only `.mp3`, `.wav`, `.m4a`; validate MIME type server-side, not just filename extension |
| Flask + large uploads | Default Flask 1MB limit | Must set `app.config['MAX_CONTENT_LENGTH']` explicitly — default silently rejects files over 1MB with a 413 error the client may not handle gracefully |
| Chord diagram SVG/canvas | Hardcoding pixel positions | Diagrams break on mobile; use relative units or an established chord diagram library |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Processing full audio at 44100 Hz | Analysis takes 2–3x longer than needed | Always load at `sr=22050`; chord detection doesn't benefit from higher sample rates | Immediately on songs >3 minutes |
| Re-running beat track inside chord detection | Doubled computation time | Compute beats once, pass results to all downstream steps | Immediately if pipeline is modular |
| Sending raw audio array to chroma, STFT, and tonnetz separately | 3x FFT computation | Compute STFT once, derive all features from it | Medium songs (>5 min) |
| Keeping audio ndarray in memory after analysis | Memory not released between requests | Delete `y` explicitly after feature extraction | After 5+ uploads in a session |
| Generating chord diagrams server-side as images | Slow rendering, large payloads | Generate diagrams client-side with JS (VexChords, chord-fingering library) | At any non-trivial scale |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| No file size limit on upload | Server OOM attack via giant file | Set `MAX_CONTENT_LENGTH` to 100MB max in Flask/FastAPI |
| Executing `ffmpeg` with unsanitized filename | Shell injection if filename contains shell metacharacters | Use `subprocess` with a list (not string) for commands; never pass filename directly to shell; rename uploaded files to UUIDs server-side |
| Serving uploaded files from the same directory as app code | Path traversal risk | Store uploads in a temp directory outside webroot; delete after processing |
| No MIME type validation | Malicious file disguised as MP3 | Validate magic bytes, not just extension; use `python-magic` library |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing raw detection confidence scores to users | Users don't know what 0.73 confidence means; creates anxiety without actionability | Hide scores; instead show "Results may vary for songs with complex arrangements" as static disclaimer |
| Displaying chords that change every beat with no grouping | Chart looks like noise; unplayable | Group to measure level (4 beats); show one chord per measure unless there's a clear mid-measure change |
| No indication of processing time | User assumes app crashed after 10 seconds; re-uploads | Show progress steps with estimates: "1/3: Loading audio (5s)... 2/3: Detecting chords (20s)..." |
| Showing detected section labels without letting user override | "Verse 1" might be misdetected; user can't correct it | Make section labels editable in-place after display |
| Chord chart with no scroll anchoring to playback position | User loses place in chart while listening to verify | Even a static "current measure" highlight on playback would help; or just display section-by-section |
| Presenting chord diagrams for chords the detected song doesn't use | Cognitive overload | Only show fingering diagrams for chords actually detected in the song |
| Using music theory terminology in error messages | Confusion for non-musicians | "We couldn't detect clear chords in this section" not "Insufficient harmonic content in spectral frame" |

---

## "Looks Done But Isn't" Checklist

- [ ] **Chord detection working:** Verify against 5 known songs spanning pop, rock, folk — not just the one test song you used during development. Check: does A minor sound like A minor?
- [ ] **Beat alignment:** Visually verify that chord changes in the chart align with actual measure boundaries. Listen to the song while reading the chart.
- [ ] **MP3 loading:** Test with a 128kbps MP3, a 320kbps MP3, an M4A, and a WAV. Verify `ffmpeg` is installed in production environment.
- [ ] **Key naming convention:** Verify flat-key songs use flat notation (Bb, Eb) not sharp (A#, D#). Test with a song in F major or Bb major.
- [ ] **Long file handling:** Upload a 6-minute song. Verify server responds, doesn't timeout or crash, and memory is released after.
- [ ] **Error handling on bad audio:** Upload a corrupted MP3, a text file renamed as .mp3, and a silent file. Verify the app returns a user-readable error, not a 500.
- [ ] **Section detection labeled correctly:** Auto-detected sections (Verse/Chorus) should make musical sense. A 3-minute song should not have 15 sections.
- [ ] **Chord diagrams display:** All detected chord names must map to a valid fingering diagram. Unusual chords (e.g., "Ebm7") must either display correctly or gracefully fall back to a simpler voicing.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Built on raw chroma argmax — accuracy is terrible | HIGH | Rewrite audio processing pipeline; add `madmom` or `CREMA`; beat sync; this is a full backend rewrite |
| No beat alignment implemented | MEDIUM | Add beat tracking pass; re-timestamp all chord data; update chart rendering to consume new format |
| Synchronous processing blocking server | MEDIUM | Add job queue (even a simple threading pool); update frontend to poll; 1-2 days of refactoring |
| Memory not released between uploads | LOW | Add explicit `del y; gc.collect()` after processing; restart server to flush |
| Wrong enharmonic names in output | LOW | Add key-aware chord naming function; unit-testable; 2–4 hours of work |
| Section labels wrong | LOW-MEDIUM | Make sections editable in UI; no backend change required |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Raw chroma → chord labels | Audio Processing (Phase 1) | Test against 10 known songs; check accuracy >60% on basic chords |
| MP3 memory explosion | Backend Setup (Phase 1) | Load a 10-minute MP3; verify RAM stays under 500MB |
| Synchronous server blocking | Backend Architecture (Phase 1) | Upload a 5-minute file; verify UI receives immediate response with job ID |
| No beat alignment | Audio Processing (Phase 1) | Count chord timestamps in output; should be ≤16 per minute for pop songs |
| Key estimation / enharmonic naming | Audio Processing (Phase 1) | Test with songs in Bb, F, D major; verify flat vs sharp conventions |
| ffmpeg not in production | Deployment (final phase) | Test MP3 upload in clean deployment environment before launch |
| No file validation / security | Backend Setup (Phase 1) | Try uploading a .txt file renamed to .mp3; expect clean error |
| UX: no processing feedback | Frontend Integration (Phase 2) | Time a 4-minute song upload; verify spinner/progress shows for the full duration |
| Chord diagrams for unknown chords | Frontend Integration (Phase 2) | Feed an unusual chord (Abm, F#7) through the diagram renderer; verify no blank/broken diagram |
| Section labels uneditable | Frontend Integration (Phase 2) | Manually verify that at least one section can be renamed in the UI |

---

## Sources

- librosa official documentation — Advanced I/O: https://librosa.org/doc/main/ioformats.html
- librosa GitHub issue #681 — Memory leak / slowdown over iterations: https://github.com/librosa/librosa/issues/681
- librosa GitHub issue #406 — 128MB memory constraint: https://github.com/librosa/librosa/issues/406
- librosa blog — Streaming for large files: https://librosa.org/blog/2019/07/29/stream-processing/
- AudioLabs Erlangen — Template-Based Chord Recognition (template accuracy limitations): https://www.audiolabs-erlangen.de/resources/MIR/FMP/C5/C5S2_ChordRec_Templates.html
- AudioLabs Erlangen — Chroma Feature Types for Chord Recognition: https://www.audiolabs-erlangen.de/content/05_fau/professor/00_mueller/03_publications/2011_JiangGroscheKonzMueller_ChordRecognitionEvaluation_AES42-Ilmenau.pdf
- MIREX 2024 Audio Chord Estimation — Evaluation framework and vocabulary gaps: https://music-ir.org/mirex/wiki/2024:Audio_Chord_Estimation
- arxiv — Enhancing Automatic Chord Recognition through LLM Chain-of-Thought Reasoning (multi-track source separation approach): https://arxiv.org/html/2509.18700v1
- MDPI — Key Detection via Key-Profiles (E7 leading to wrong key of E-major example): https://www.mdpi.com/2076-3417/12/21/11261
- Music IR Blog — Essentia ACE algorithm accuracy issues and tuning detection: https://musicinformationretrieval.wordpress.com/2017/06/21/improving-essentia-ace-algorithms/
- ResearchGate — Automatic Chord Detection Incorporating Beat and Key Detection: https://www.researchgate.net/publication/224363462_Automatic_Chord_Detection_Incorporating_Beat_and_Key_Detection
- FastAPI background tasks guide — Long-running audio processing patterns: https://leapcell.io/blog/managing-background-tasks-and-long-running-operations-in-fastapi
- DEV Community — Memory leak fix in Python audio app: https://dev.to/highcenburg/how-i-fixed-a-critical-memory-leak-in-my-python-audio-app-42g9

---
*Pitfalls research for: Audio chord detection and chord chart generation web app*
*Researched: 2026-03-03*
