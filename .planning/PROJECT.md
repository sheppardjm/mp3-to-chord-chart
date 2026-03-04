# dontCave

## What This Is

A personal tool that takes an MP3 file and user-provided lyrics, detects the chord progression from the audio, and generates an Ultimate Guitar-style chord chart in a web UI. Guitar players upload a song, paste the lyrics, and get a formatted chord page with chords positioned above the correct words.

## Core Value

Accurately detect chord changes from an MP3 and align them to the right positions in user-provided lyrics, producing a readable chord chart.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Upload an MP3 file and paste lyrics via a web interface
- [ ] Detect basic chords (major, minor, 7th) and their timing from the MP3 audio
- [ ] Align detected chord changes to the corresponding positions in the lyrics
- [ ] Auto-detect song sections (Verse, Chorus, Bridge) and label them in the chart
- [ ] Display the chord chart in Ultimate Guitar style — chords above lyrics, section labels
- [ ] Show chord fingering diagrams for each unique chord used in the song
- [ ] Python backend (Flask/FastAPI) handles audio analysis, web frontend displays results

### Out of Scope

- Lyrics transcription from audio — user provides lyrics manually
- Extended/jazz chords (sus, aug, dim, 9th, maj7) — basic chords only for v1
- Transpose / capo suggestions — not in v1
- Fret-level guitar tablature — chord names only, not note-by-note tab
- Mobile app — web-only
- Multi-user / accounts — personal tool, no auth needed
- Saving/sharing charts — one-shot generation for now

## Context

- Audio chord detection relies on chroma feature extraction (e.g., librosa) — matching pitch class energy over time to chord templates
- Chord detection accuracy varies: works well for acoustic/pop/folk with clear harmony, struggles with heavy distortion or dense mixes
- Song section detection can use structural segmentation algorithms (e.g., librosa's segment detection or repetition-based analysis)
- Aligning chord timing to lyrics requires syncing audio timestamps with text positioning — the trickiest part of the project
- Ultimate Guitar's format: chord names appear on a line directly above the lyric line, positioned over the syllable where the chord changes

## Constraints

- **Tech stack**: Python backend (Flask or FastAPI), HTML/CSS/JS frontend
- **Audio analysis**: librosa or similar Python audio analysis library
- **Personal use**: No need for production hardening, auth, or scalability

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| User provides lyrics (no auto-transcribe) | Simpler, more accurate than speech-to-text | — Pending |
| Basic chords only (major, minor, 7th) | Covers most pop/rock/folk; extended chords add complexity | — Pending |
| Python + web UI | Python has the best audio analysis ecosystem; web UI for formatting | — Pending |
| One-shot generation (no edit/adjust) | Personal tool, keep it simple for v1 | — Pending |

---
*Last updated: 2026-03-03 after initialization*
