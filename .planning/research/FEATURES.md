# Feature Research

**Domain:** Audio chord detection + chord chart / tab generation tools
**Researched:** 2026-03-03
**Confidence:** MEDIUM (WebSearch-verified against multiple competitor sources; no Context7 applicable for product features)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Chord names displayed above lyrics | Industry standard UX established by Ultimate Guitar and every chord chart tool; users trained on this format | LOW | Two-line format: chord name row above lyric row. Inline bracket (ChordPro) format is a secondary convention used by OnSong/SongSheet. For a web display tool, the UG two-line layout is more readable at a glance. |
| Song section labels (Verse, Chorus, Bridge) | All major tools (Chordify, UG, Chord AI) show structural markers; musicians use sections to navigate | MEDIUM | Auto-detection from audio is hard (60-70% accuracy per MIREX benchmarks). Given lyrics are user-supplied, a reasonable fallback is auto-detecting from audio then letting user confirm/edit labels. |
| Chord fingering diagrams | UG, Chordify, Chord AI, Yamaha Chord Tracker all show chord shapes; users expect to see "how to play this chord" | MEDIUM | For major, minor, 7th only (project scope), this is a finite set of diagrams. Can be static SVG/image assets keyed to chord name. Standard fretboard orientation (top = nut, dots = finger placement, X = muted, O = open). |
| Chord names are correct music notation | Users know G, Am, C, E7, Dm etc.; garbled chord names break trust immediately | LOW | Naming convention must follow standard: root + quality (e.g., "Am", "G", "E7", "Dm"). No invented shorthand. |
| Detection acknowledges basic chord vocabulary | Users uploading pop/rock/folk MP3s expect major, minor, dominant 7th chords to be recognized | MEDIUM | Project scope already limits to major/minor/7th — this aligns with what the underlying libraries (librosa, chord recognition models) handle best. Complex chords (dim7, m7b5, sus2) are a stretch goal and commonly inaccurate. |
| Some indication of tempo or song playback position | Chordify, Chord AI, Yamaha Chord Tracker all show time-synced chords; users want to know "which chord am I on now" | HIGH | Full playback sync (audio + scrolling chord highlighting) is table stakes for apps like Chordify but is a significant engineering lift. For a one-shot generator (upload → get chart), a static chart without playback sync is defensible as MVP. See MVP Definition. |
| Clear display of chord changes within lyrics | Users need to know exactly where in the lyric line a chord changes (beat/syllable alignment) | MEDIUM | ChordPro bracket format preserves alignment through font/key changes. Standard UG two-line tab format requires monospaced font to stay aligned. Either works; choose one and be consistent. |
| Readable, printable output | Every chord chart tool offers print or PDF export; musicians take charts to rehearsals | LOW | Browser print CSS is sufficient. Clean layout with adequate font size. No complex export library needed for MVP. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| One-shot upload flow (MP3 + lyrics → chart) | Most tools (Chordify, Chord AI) detect chords from audio but require you to separately source and paste lyrics, then manually merge. This tool generates a unified chord chart from both inputs simultaneously. | MEDIUM | The core product concept IS the differentiator. No competitor does this as a clean one-shot flow targeted at chart generation vs. real-time play-along. |
| Lyrics-anchored chord placement | Chordify shows a timeline-style chord grid, not lyrics-embedded chords. UG charts are hand-authored. This tool auto-aligns detected chords to lyric text using beat/timing data. | HIGH | Requires mapping audio chord timestamps → lyric words/syllables. Needs lyric timing inference (could use rough beat-to-line matching if full word-level alignment is too complex). This is the hardest part and is what makes the output feel like a real chord chart vs. a chord timeline. |
| Chord simplification for beginners | Moises and Yamaha Chord Tracker both offer chord simplification (e.g., drop 7ths, suggest capo positions). Users learning guitar often can't play complex voicings. | LOW | Since project scope is already basic (major/minor/7th), the output is already simplified. Could label this explicitly ("Simplified chords") as a value prop. |
| Auto-detected song key displayed | Chord AI, Moises both surface the detected key (e.g., "Key of G Major"). Useful context for musicians who want to transpose or solo. | LOW | librosa or similar can return detected key. One additional label in the UI header. Low effort, meaningful signal. |
| Section confidence indicator | Auto-detected sections (Verse/Chorus) are often wrong. Showing "detected with low confidence" or allowing one-click relabeling sets appropriate expectations and makes the tool feel honest. | MEDIUM | Prevents user distrust when section labels are wrong. None of the surveyed tools do this. |
| Export as plain-text ChordPro | ChordPro is the interoperable format used by SongSheet Pro, OnSong, and dozens of gigging apps. Exporting in this format lets users take their generated chart into their preferred performance app. | LOW | Simple text format. Chords inline as `[Am]` within lyric text. Very low implementation cost; high interoperability value. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time playback sync (audio + scrolling highlights) | Chordify's signature feature; impressive demo | Requires serving audio back from the server, managing playback state, websocket or polling for sync, CORS/browser audio API complexity. Doubles infrastructure scope for MVP. | Static chord chart with timestamps noted (e.g., "0:32 - Chorus"). Can add playback sync in v2 if users request it. |
| Song library / saved charts | Users naturally want to save their work | Requires user accounts, authentication, persistent storage (database), file storage for MP3s. Turns a stateless processing tool into a full app. | In-browser session storage for the current session. Download/export as text or PDF as the "save" mechanism. |
| User accounts and authentication | Feels professional | Major scope increase; security surface; session management; password reset flows. Not needed for a personal tool. | Skip entirely for MVP. If multi-user ever needed, add in a dedicated phase. |
| Full transposition (change key) | Every chord chart app offers this | Requires chord-name-aware transposition logic and re-rendering. Non-trivial for a web app. Moises/UG handle this server-side with full music theory logic. | Capo suggestion table ("to play in Am instead of Em, use capo 7") is simpler and covers the most common use case. |
| MIDI export | Chord AI and Klangio offer this; sounds powerful | Requires a MIDI generation library. MIDI of chord progressions is useful only for DAW users, not guitarists looking at a chord chart. Scope creep for target user. | ChordPro text export serves the interoperability need for the target audience. |
| Beat-accurate chord timing grid (Chordify style) | Visually impressive; shows chords on a scrolling timeline | Fundamentally different UX paradigm than a chord chart. Optimized for play-along, not chart reading. Would require audio streaming back to browser. | Chord chart format (chords above lyrics) IS the alternative. Solve a different problem better. |
| Complex chord vocabulary (dim7, m7b5, 9ths) | Completionists want full jazz vocabulary | Audio detection accuracy drops significantly beyond major/minor/7th, per published MIREX benchmarks (~65-70% overall, much lower for complex voicings). Showing wrong complex chords is worse than showing "close but simplified" chords. | Explicit scope limit: major, minor, dominant 7th only. Document this as a design choice, not a limitation. |
| YouTube/SoundCloud URL input | Chord AI and Chordify support this | Requires yt-dlp or similar scraping; TOS issues; network egress costs; brittleness when APIs change. Not worth it for a personal tool taking MP3 inputs. | MP3 file upload only. User downloads from wherever they want. Clean boundary. |
| Social sharing / community chord charts | UG's core moat | Enormous product scope. Community features, moderation, versioning, ratings. | N/A for a personal tool. |

---

## Feature Dependencies

```
[MP3 Upload]
    └──required by──> [Audio Chord Detection]
                          └──required by──> [Chord Timeline / Timestamps]
                                                └──required by──> [Lyrics-Chord Alignment]
                                                                      └──required by──> [Chord Chart Display]

[User-Provided Lyrics]
    └──required by──> [Lyrics-Chord Alignment]
                          └──required by──> [Section Labels]
                                                └──enhances──> [Chord Chart Display]

[Chord Chart Display]
    └──enhances──> [Chord Fingering Diagrams]
    └──enables──> [PDF/Print Export]
    └──enables──> [ChordPro Text Export]

[Audio Chord Detection]
    └──produces──> [Key Detection] (low-cost byproduct)

[Section Labels (auto-detected)]
    └──conflicts with──> [High Confidence Claims] (auto-detection is ~60-70% accurate)
```

### Dependency Notes

- **Audio Chord Detection requires MP3 Upload:** The core analysis pipeline depends on having audio input. No audio = no chart. This is the critical path.
- **Lyrics-Chord Alignment requires both Chord Timestamps AND User Lyrics:** Both inputs must be present before alignment can occur. This is the novel value of the tool and the hardest feature to implement well.
- **Section Labels depend on Lyrics structure:** Without lyrics, section detection is purely audio-based (harder). With lyrics, heuristics like "repeated lyric blocks" are a viable shortcut for MVP.
- **Chord Fingering Diagrams enhance but do not require Chord Chart Display:** Diagrams can be a post-render enhancement. They can be static SVG assets looked up by chord name.
- **Key Detection is a free byproduct of Audio Chord Detection:** librosa-based chord analysis typically returns a detected key. Surface it; costs nothing extra.
- **ChordPro Export requires Chord Chart Display to exist first:** Can't export what hasn't been generated. Natural sequencing.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [ ] MP3 file upload — without this, nothing works
- [ ] Audio chord detection (major/minor/7th, chord + timestamp output) — the core intelligence
- [ ] Chord-to-lyric alignment (map detected chord timestamps to lyric lines) — what makes this a chart, not just a chord list
- [ ] Song section labels (Verse/Chorus/Bridge) auto-detected from audio + lyric structure — makes chart navigable; acceptable accuracy ~60-70%
- [ ] Chord chart display (chords above lyrics, section headers, monospaced font alignment) — the primary output
- [ ] Chord fingering diagrams (static SVGs for the ~20 chords in scope: major/minor/7th) — visual aid; finite implementation cost
- [ ] Detected key displayed in chart header — low cost, high signal
- [ ] PDF/print export via browser print CSS — "save my chart" without needing accounts

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] ChordPro text export — add when users ask how to use charts in OnSong/SongSheet
- [ ] Section label editing (click to rename Verse → Chorus) — add when auto-detection is wrong often enough to matter
- [ ] Capo suggestion table — add if users frequently transpose manually
- [ ] Confidence display on section labels — add if user complaints about wrong sections are common

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] Playback sync (audio + scrolling chord highlight) — big lift; validate demand first
- [ ] Full key transposition — complex music theory logic; defer
- [ ] Session persistence (in-browser) — add if users report "I closed the tab and lost my chart"
- [ ] Alternative chord voicings (show 3 fingering options per chord) — add when basic diagram feedback is positive

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| MP3 upload + chord detection | HIGH | MEDIUM | P1 |
| Lyrics-chord alignment | HIGH | HIGH | P1 |
| Chord chart display (chords above lyrics) | HIGH | LOW | P1 |
| Song section labels | HIGH | MEDIUM | P1 |
| Chord fingering diagrams (static) | HIGH | LOW | P1 |
| Key detection display | MEDIUM | LOW | P1 |
| PDF/print export | MEDIUM | LOW | P1 |
| ChordPro text export | MEDIUM | LOW | P2 |
| Section label editing | MEDIUM | LOW | P2 |
| Capo suggestion | LOW | LOW | P2 |
| Section confidence display | MEDIUM | LOW | P2 |
| Playback sync (audio + chord highlight) | HIGH | HIGH | P3 |
| Full key transposition | MEDIUM | HIGH | P3 |
| Alternative chord voicings | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Chordify | Ultimate Guitar | Chord AI | Yamaha Chord Tracker | Our Approach |
|---------|----------|-----------------|----------|---------------------|--------------|
| Audio input | Upload + YouTube + mic | Hand-authored tabs (no audio input) | Upload + YouTube + mic + streaming | Local music library | MP3 upload only |
| Chord detection | Yes, auto from audio | No (user-submitted) | Yes, AI-based | Yes, from device library | Yes, AI-based (Python backend) |
| Chord display format | Timeline grid (scrolling) | Chords above lyrics | Timeline + chord list | Chord symbol timeline | Chords above lyrics (UG format) |
| Lyrics integration | Recent addition (sync playback) | Yes (hand-authored) | Lyrics transcription (AI) | No | User-provided lyrics, aligned to chords |
| Song sections | No | Yes (hand-authored [Verse], [Chorus]) | No | No | Auto-detected + user labels |
| Chord diagrams | Yes (guitar/piano/ukulele) | Yes (large library) | Yes (guitar/piano/ukulele) | Yes (guitar + piano) | Yes (guitar, static SVGs, basic chords only) |
| Transposition | Yes (Premium) | Yes (Pro) | Yes | Yes | No (v1; capo table as workaround) |
| Export | PDF (Premium) | Print, PDF (Pro) | MIDI, stems | None | PDF via print CSS; ChordPro text (v1.x) |
| Playback sync | Core feature | No | No | Core feature | No (v1); consider v2 |
| User accounts | Required | Required | Required | Not needed | Not needed |
| One-shot chart from audio + lyrics | No | No | Partial (separate tools) | No | Yes — this is the core differentiator |

---

## Sources

- Ultimate Guitar feature set: [Ultimate Guitar App on Google Play](https://play.google.com/store/apps/details?id=com.ultimateguitar.tabs) — MEDIUM confidence (WebSearch)
- Chordify features: [Chordify/MusicRadar coverage](https://www.musicradar.com/news/chordify-lyrics-live-chord-detection) — MEDIUM confidence (WebSearch)
- [Chordify Alternatives analysis](https://www.hooktheory.com/blog/chordify-alternatives/) — MEDIUM confidence (WebFetch verified)
- Yamaha Chord Tracker: [Yamaha USA Chord Tracker Features page](https://usa.yamaha.com/products/musical_instruments/pianos/apps/chord_tracker/features.html) — MEDIUM confidence (WebSearch; fetch failed with 403)
- Chord AI: [Chord AI official site](https://chordai.net/) — HIGH confidence (WebFetch verified)
- Melody Scanner: [Melody Scanner](https://melodyscanner.com/) — HIGH confidence (WebFetch verified)
- Audio chord detection accuracy: [MIREX Chord Detection benchmarks via ResearchGate](https://www.researchgate.net/publication/264569067_Automatic_Chord_Estimation_from_Audio_A_Review_of_the_State_of_the_Art) — HIGH confidence (academic)
- Song section detection complexity: [All-In-One Music Structure Analyzer (GitHub)](https://github.com/mir-aidj/all-in-one) — HIGH confidence (official repo)
- Chord/lyric format UX: [OnSong Writing Chord Charts](https://onsongapp.zendesk.com/hc/en-us/articles/360053210514-Writing-your-own-text-based-chord-charts) — HIGH confidence (official docs)
- Autoscroll / hands-free features: [OnSong Autoscroll Manual](https://onsongapp.com/docs/features/autoscroll/) — HIGH confidence (official docs)
- ChordPro format: [SongSheet Pro ChordPro docs](http://songsheetapp.com/manual/chordpro.html) — HIGH confidence (official docs)
- Moises chord detection: [Moises Advanced Chord Detection](https://moises.ai/blog/moises-news/advanced-chord-detection/) — MEDIUM confidence (official blog)
- UG chord/lyric format: [Ultimate Guitar forum thread on chord/lyric format](https://www.ultimate-guitar.com/forum/showthread.php?t=1677475) — MEDIUM confidence (community)

---
*Feature research for: audio chord detection + chord chart generation tool*
*Researched: 2026-03-03*
