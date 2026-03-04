# Requirements: dontCave

**Defined:** 2026-03-03
**Core Value:** Accurately detect chord changes from an MP3 and align them to the right positions in user-provided lyrics, producing a readable chord chart.

## v1 Requirements

### Audio Analysis

- [ ] **AUDIO-01**: System detects major, minor, and 7th chords from an uploaded MP3 using chroma feature extraction
- [ ] **AUDIO-02**: Chord changes are snapped to musical beat positions (beat-synchronized)
- [ ] **AUDIO-03**: Song sections (Verse, Chorus, Bridge) are auto-detected via structural segmentation
- [x] **AUDIO-04**: Song key is detected for correct enharmonic chord naming (F# vs Gb)

### Input

- [ ] **INPUT-01**: User can upload an MP3 file via the web interface
- [ ] **INPUT-02**: User can paste song lyrics into a text area
- [ ] **INPUT-03**: UI shows processing progress/feedback while audio is analyzed (10-60s)

### Display

- [ ] **DISP-01**: Chord names are positioned above the correct syllable in the lyrics (Ultimate Guitar format)
- [ ] **DISP-02**: Song sections are labeled with headers ([Verse], [Chorus], [Bridge])
- [ ] **DISP-03**: Chord fingering diagrams (SVG) are shown for each unique chord used in the song

### Integration

- [ ] **INTG-01**: Detected chord timestamps are aligned to user-provided lyric lines
- [x] **INTG-02**: Python backend (FastAPI) serves the API; frontend displays results via HTML/CSS/JS

## v2 Requirements

### Output

- **OUT-01**: User can print/export chord chart as PDF via print stylesheet
- **OUT-02**: User can transpose all chords up/down by semitones
- **OUT-03**: Capo position suggestions for easier fingerings

### Editing

- **EDIT-01**: User can manually edit/correct detected chords
- **EDIT-02**: User can manually adjust section labels
- **EDIT-03**: User can save/bookmark generated charts

### Input Expansion

- **INP-01**: Support WAV and FLAC file uploads in addition to MP3
- **INP-02**: Auto-transcribe lyrics from audio (Whisper integration)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time playback sync | Doubles infrastructure scope; not needed for static chart |
| User accounts / authentication | Personal tool, no multi-user needs |
| YouTube URL input | TOS issues, brittle scraping, adds complexity |
| Extended chord vocabulary (sus, aug, dim, 9th, maj7) | Detection accuracy craters beyond major/minor/7th |
| MIDI export | Wrong audience for a chord chart tool |
| Mobile app | Web-only, personal use |
| Fret-level guitar tablature | Chord names only, not note-by-note transcription |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUDIO-01 | Phase 3 | Pending |
| AUDIO-02 | Phase 3 | Pending |
| AUDIO-03 | Phase 4 | Pending |
| AUDIO-04 | Phase 2 | Complete |
| INPUT-01 | Phase 5 | Pending |
| INPUT-02 | Phase 6 | Pending |
| INPUT-03 | Phase 5 | Pending |
| DISP-01 | Phase 7 | Pending |
| DISP-02 | Phase 7 | Pending |
| DISP-03 | Phase 8 | Pending |
| INTG-01 | Phase 6 | Pending |
| INTG-02 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 after roadmap creation*
