# Phase 7: Chord Chart Display - Research

**Researched:** 2026-03-04
**Domain:** ChordSheetJS 14.0.0, HTML/CSS chord-above-lyric rendering, ChartData-to-Song translation
**Confidence:** HIGH (ChordSheetJS API verified against GitHub source; data model verified against codebase)

## Summary

Phase 7 renders the `/analyze` API response (a `ChartData` JSON object) as a human-readable chord chart in the browser. The chart must show chord names positioned above the correct lyric syllables, section headers ([Verse], [Chorus], etc.), and a key/tempo header — matching Ultimate Guitar display conventions.

The roadmap mandates ChordSheetJS 14.0.0 as the rendering library. Research confirms this is the correct choice: the library provides `HtmlDivFormatter` which produces a flexbox-based `column > chord / lyrics` div layout that handles chord-above-lyric positioning without any custom CSS geometry. The library ships an ESM build (`lib/module.js`) and integrates cleanly with Vite 7.

The critical implementation challenge is **translating `ChartData` into a ChordSheetJS `Song` object**. The API's `ChordAnnotation.position` field (a 0.0–1.0 fraction of line duration) must be converted to character-offset splits of the lyric text so that `ChordLyricsPair` instances can be assembled correctly. This conversion is pure JavaScript and requires no additional library.

**Primary recommendation:** Install `chordsheetjs@14.0.0` via npm. Build a `Song` programmatically using `Song`, `Line`, `ChordLyricsPair`, and `Tag` classes. Render with `HtmlDivFormatter`. Inject the formatter's CSS string into a `<style>` tag.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| chordsheetjs | 14.0.0 | Song object model + HTML rendering | Roadmap-mandated; provides full chord-above-lyric layout engine |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jspdf | ^4.0.0 | Peer dep of chordsheetjs | Pulled in automatically; not used directly |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HtmlDivFormatter | Custom HTML renderer | Custom renderer avoids the Song-building translation layer but loses CSS generation, future transpose support, and PDF export |
| ChordProParser (parse text) | Programmatic Song construction | Parsing ChordPro text is simpler to write but requires serializing ChartData to a string format first — more brittle |

**Installation:**
```bash
cd frontend
npm install chordsheetjs@14.0.0
```

Expected additions to `node_modules`: jspdf and ~20 transitive deps (html2canvas, canvg, pako, etc.). Bundle size impact is significant; jspdf is large. Tree-shaking will not eliminate jspdf because it is an unconditional dependency of chordsheetjs. This is an accepted cost given the roadmap decision.

---

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── main.js              # existing: form submission, fetch /analyze
├── renderChart.js       # NEW: ChartData → Song → HtmlDivFormatter → DOM
└── style.css            # existing: global styles
```

A single `renderChart.js` module is sufficient. No component framework is used (vanilla JS). The module exports one function: `renderChart(chartData, containerEl)`.

### Pattern 1: Programmatic Song Construction

**What:** Build a ChordSheetJS `Song` object directly from `ChartData` JSON without going through a text parser.

**When to use:** Always — the ChartData is already structured data; using a text parser would require serializing to ChordPro or ChordsOverWords format first.

**How `ChordLyricsPair` works:** Each `ChordLyricsPair(chord, lyricFragment)` pairs one chord with the text that comes *after* that chord change. The complete lyric line is recovered by concatenating all `lyrics` fragments. A line with no chords needs a single `ChordLyricsPair('', fullLineText)`.

**Position-to-character-offset conversion:**

The API returns `ChordAnnotation.position` as a float 0.0–1.0 representing where in the line duration the chord change occurs. To position the chord over the correct syllable, map this to a character index in the lyric text:

```javascript
// charIndex is the split point: chord starts here, preceding text belongs to prior pair
function positionToCharIndex(position, text) {
  return Math.round(position * text.length);
}
```

Then split the lyric text at each chord's character index to produce the `lyrics` fragment for each `ChordLyricsPair`:

```javascript
// chords: ChordAnnotation[] sorted by position ascending
// text: string (full lyric line)
function buildPairs(chords, text) {
  const pairs = [];
  let cursor = 0;

  for (const ann of chords) {
    const charIdx = Math.round(ann.position * text.length);
    // lyrics fragment from cursor to charIdx belongs to the PREVIOUS chord
    // The current chord's lyric fragment starts here
    const prevLyrics = text.slice(cursor, charIdx);
    if (pairs.length > 0) {
      // Assign prevLyrics to last pair
      pairs[pairs.length - 1] = new ChordLyricsPair(
        pairs[pairs.length - 1].chords,
        prevLyrics,
      );
    }
    pairs.push(new ChordLyricsPair(ann.chord, ''));
    cursor = charIdx;
  }

  // Remaining text goes to the last chord
  const remaining = text.slice(cursor);
  if (pairs.length > 0) {
    pairs[pairs.length - 1] = new ChordLyricsPair(
      pairs[pairs.length - 1].chords,
      remaining,
    );
  } else {
    // No chords: one empty-chord pair with full text
    pairs.push(new ChordLyricsPair('', text));
  }

  return pairs;
}
```

**Example (verified pattern — Song, Line, ChordLyricsPair, Tag are all direct exports):**

```javascript
// Source: github.com/martijnversluis/ChordSheetJS src/index.ts (exports verified)
import {
  Song,
  Line,
  ChordLyricsPair,
  Tag,
  HtmlDivFormatter,
  VERSE,
  CHORUS,
} from 'chordsheetjs';

function buildSong(chartData) {
  const song = new Song({ key: chartData.key, tempo: String(chartData.bpm) });

  for (const section of chartData.sections) {
    // Section start tag: e.g. {start_of_verse: label="Verse"}
    const sectionType = sectionTypeFor(section.label); // VERSE, CHORUS, etc.
    const startTag = new Tag(`start_of_${sectionType}`, section.label);
    const startLine = new Line({ type: sectionType, items: [startTag] });
    song.addLine(startLine);

    for (const lyricLine of section.lines) {
      const pairs = buildPairs(lyricLine.chords, lyricLine.text);
      const line = new Line({ type: sectionType, items: pairs });
      song.addLine(line);
    }

    const endTag = new Tag(`end_of_${sectionType}`, '');
    const endLine = new Line({ type: sectionType, items: [endTag] });
    song.addLine(endLine);
  }

  return song;
}
```

**Note on sectionTypeFor():** Map the API's `section.label` (e.g., "Verse 1", "Chorus", "Bridge") to ChordSheetJS section type constants. The safe mapping is:

```javascript
function sectionTypeFor(label) {
  const lower = label.toLowerCase();
  if (lower.includes('chorus')) return 'chorus';
  if (lower.includes('bridge')) return 'bridge';
  return 'verse'; // default for Verse, Intro, Outro, etc.
}
```

The Tag constructor signature is `new Tag(name, value)` where `name` is the directive name (e.g., `'start_of_verse'`) and `value` is the label string.

### Pattern 2: HtmlDivFormatter Rendering

**What:** Convert a `Song` to HTML and inject into the DOM, with CSS.

**Example:**
```javascript
// Source: github.com/martijnversluis/ChordSheetJS src/formatter/html_formatter.ts (verified)
function renderChart(chartData, containerEl) {
  const song = buildSong(chartData);
  const formatter = new HtmlDivFormatter();

  // Inject scoped CSS once
  if (!document.getElementById('chordsheet-css')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'chordsheet-css';
    styleEl.textContent = formatter.cssString('#chord-chart');
    document.head.appendChild(styleEl);
  }

  containerEl.id = 'chord-chart';
  containerEl.innerHTML = formatter.format(song);
}
```

`cssString('#chord-chart')` scopes all generated CSS to `#chord-chart` to avoid polluting the rest of the page.

### Pattern 3: Chart Header (Key + Tempo)

The header is best rendered outside the ChordSheetJS output — as a simple `<div>` above the chart container — because ChordSheetJS title/subtitle metadata renders as `<h1>`/`<h2>` inside the chord sheet div and styling them is more complex than a standalone element.

```javascript
function renderHeader(chartData, headerEl) {
  headerEl.innerHTML = `
    <span class="chart-key">Key: ${chartData.key}</span>
    <span class="chart-tempo">Tempo: ${Math.round(chartData.bpm)} BPM</span>
  `;
}
```

### Anti-Patterns to Avoid

- **Do not use `ChordsOverWordsParser` or `ChordProParser` to build the Song**: These parsers accept text strings. Serializing ChartData to ChordsOverWords text and re-parsing it adds a fragile serialization layer with no benefit over direct construction.
- **Do not use `MeasuredHtmlFormatter`**: This is a beta feature that requires `DomMeasurer` or `CanvasMeasurer` for precise pixel positioning. The standard `HtmlDivFormatter` flexbox layout is sufficient and more reliable for this use case.
- **Do not use `HtmlTableFormatter`**: Table-based layout is not responsive and does not adapt to different lyric line lengths.
- **Do not render `position` as a raw percentage CSS offset**: The flexbox column layout handles chord alignment automatically — do not manually compute `left` pixel offsets.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chord-above-lyric column layout | Custom CSS flexbox chord rows | `HtmlDivFormatter` | Zero-width-space handling, responsive column breaks, label rows all solved |
| CSS for chord sheet | Custom `.chord`, `.lyrics` styles from scratch | `formatter.cssString()` | Correct padding, column alignment, paragraph spacing included |
| Chord name parsing/transposition | String manipulation on chord names | `Chord.parse()` from chordsheetjs | Handles enharmonics, slash chords, sus/add extensions |

**Key insight:** ChordSheetJS's flexbox column layout is the correct display model — each chord gets its own column `<div>`, with the chord name above and the following lyric text below. The layout automatically aligns chords with their lyrics without any custom geometry.

---

## Common Pitfalls

### Pitfall 1: Off-by-one in Position-to-Character Mapping

**What goes wrong:** `position = 0.0` should map to the very start of the line (char index 0), resulting in a chord above the first character. `position = 1.0` should never appear (it would be the start of the next line), but defensive clamping is needed.

**Why it happens:** `Math.round(0.0 * text.length)` = 0 (correct). `Math.round(1.0 * text.length)` = `text.length` (past the end — would produce an empty lyrics fragment for the last chord).

**How to avoid:** Clamp character index: `Math.min(Math.round(position * text.length), text.length - 1)` for positions > 0. Handle the edge case where `chords` is empty (produce a single `ChordLyricsPair('', text)`).

**Warning signs:** A chord appears at the far right of a line with no lyrics under it, or lyrics text is duplicated.

### Pitfall 2: Song.addLine() with Mismatched Line Types

**What goes wrong:** Section start/end tags must be on their own `Line` objects with the correct `type` property. Mixing tag items and `ChordLyricsPair` items on the same line causes `HtmlDivFormatter` to silently skip the label.

**Why it happens:** The formatter uses `line.type` and `line.items` type-checks to determine rendering path. A line that has both a section start tag and chord pairs hits the wrong rendering branch.

**How to avoid:** Always create three types of lines: (1) a line with only the start tag, (2) content lines with only `ChordLyricsPair` items, (3) a line with only the end tag.

### Pitfall 3: HtmlDivFormatter CSS Not Injected

**What goes wrong:** The formatter's `format()` output produces HTML with class names like `chord`, `lyrics`, `row`, `column`, `paragraph` — but without the CSS, chords render on the same baseline as lyrics instead of above them.

**Why it happens:** The formatter does NOT inject a `<style>` tag into the HTML output. CSS must be added separately.

**How to avoid:** Call `formatter.cssString('#chord-chart')` and inject into `document.head` before inserting the formatter output into the DOM. Do this once (guard with `document.getElementById('chordsheet-css')`).

### Pitfall 4: Large Bundle Size from jspdf

**What goes wrong:** `chordsheetjs@14.0.0` depends on `jspdf@^4.0.0`, which brings in html2canvas, canvg, pako, and others. The final bundle will be significantly larger than expected.

**Why it happens:** jspdf is an unconditional dependency; it cannot be tree-shaken because chordsheetjs imports from it at the module level.

**How to avoid:** Accept the size for this project scope. If bundle size becomes a problem, use dynamic `import('chordsheetjs')` to lazy-load the library only after the user triggers analysis.

**Warning signs:** Vite build output shows `chordsheetjs` chunk > 500KB.

### Pitfall 5: Chord Label Mapping Fails on Unexpected Labels

**What goes wrong:** The backend `section.label` field contains strings like `"Verse 1"`, `"Chorus"`, `"Bridge"`, `"Intro"`, `"Outro"`. If the mapping function only checks exact matches, novel labels (e.g., `"Pre-Chorus"`) silently fall through to `'verse'` and lose their intended section type styling.

**Why it happens:** The label is a free-form string from the segmentation model.

**How to avoid:** Use substring matching (`label.toLowerCase().includes('chorus')`) rather than exact matching. Default to `'verse'` type for unknown labels — this is safe and prevents crashes.

---

## Code Examples

### Complete renderChart.js Module Pattern

```javascript
// Source: API verified against ChordSheetJS src/index.ts, src/chord_sheet/*.ts
import {
  Song,
  Line,
  ChordLyricsPair,
  Tag,
  HtmlDivFormatter,
} from 'chordsheetjs';

const CHORD_CHART_CSS_ID = 'chordsheet-css';
const CHORD_CHART_CONTAINER_ID = 'chord-chart';

/** Map a section label string to a ChordSheetJS section type name */
function sectionTypeFor(label) {
  const l = label.toLowerCase();
  if (l.includes('chorus')) return 'chorus';
  if (l.includes('bridge')) return 'bridge';
  return 'verse';
}

/**
 * Convert ChartData LyricLine chords (position 0.0-1.0) + text
 * into an array of ChordLyricsPair for one Line.
 */
function buildChordLyricsPairs(chords, text) {
  if (!chords || chords.length === 0) {
    return [new ChordLyricsPair('', text)];
  }

  // Sort by position ascending (should already be sorted, but be safe)
  const sorted = [...chords].sort((a, b) => a.position - b.position);

  const pairs = [];
  let prevCharIdx = 0;

  for (let i = 0; i < sorted.length; i++) {
    const charIdx = Math.min(
      Math.round(sorted[i].position * text.length),
      text.length,
    );
    // Text from prevCharIdx to charIdx is the lyrics fragment for the
    // PREVIOUS chord (or pre-chord text if i === 0 with no leading chord)
    const fragment = text.slice(prevCharIdx, charIdx);

    if (i === 0 && charIdx > 0) {
      // Leading lyrics before the first chord: empty-chord pair
      pairs.push(new ChordLyricsPair('', fragment));
    } else if (i > 0) {
      // Assign fragment to the previous chord's lyrics
      const prev = pairs[pairs.length - 1];
      pairs[pairs.length - 1] = new ChordLyricsPair(prev.chords, fragment);
    }

    pairs.push(new ChordLyricsPair(sorted[i].chord, ''));
    prevCharIdx = charIdx;
  }

  // Remaining text after the last chord
  const tail = text.slice(prevCharIdx);
  if (pairs.length > 0) {
    const last = pairs[pairs.length - 1];
    pairs[pairs.length - 1] = new ChordLyricsPair(last.chords, tail);
  }

  return pairs;
}

/** Build a ChordSheetJS Song from a ChartData API response */
function buildSong(chartData) {
  const song = new Song({
    key: chartData.key,
    tempo: String(Math.round(chartData.bpm)),
  });

  for (const section of chartData.sections) {
    const type = sectionTypeFor(section.label);

    // Section start tag line
    song.addLine(new Line({
      type,
      items: [new Tag(`start_of_${type}`, section.label)],
    }));

    // Content lines
    for (const lyricLine of section.lines) {
      const pairs = buildChordLyricsPairs(lyricLine.chords, lyricLine.text);
      song.addLine(new Line({ type, items: pairs }));
    }

    // Section end tag line
    song.addLine(new Line({
      type,
      items: [new Tag(`end_of_${type}`, '')],
    }));
  }

  return song;
}

/** Render a ChartData object into the given container element */
export function renderChart(chartData, containerEl) {
  const formatter = new HtmlDivFormatter();

  // Inject scoped CSS once
  if (!document.getElementById(CHORD_CHART_CSS_ID)) {
    const styleEl = document.createElement('style');
    styleEl.id = CHORD_CHART_CSS_ID;
    styleEl.textContent = formatter.cssString(`#${CHORD_CHART_CONTAINER_ID}`);
    document.head.appendChild(styleEl);
  }

  containerEl.id = CHORD_CHART_CONTAINER_ID;
  containerEl.innerHTML = formatter.format(buildSong(chartData));
}
```

### Hardcoded ChordPro Test (for Plan 07-01 integration smoke test)

```javascript
// Source: ChordSheetJS README (verified)
import { ChordProParser, HtmlDivFormatter } from 'chordsheetjs';

const TEST_CHORDPRO = `
{title: Test Song}
{key: G}
{start_of_verse: Verse 1}
[G]Let it [D]be, let it [Em]be
{end_of_verse}
{start_of_chorus: Chorus}
[C]Whis-per [G]words of wis-dom
{end_of_chorus}
`;

const parser = new ChordProParser();
const song = parser.parse(TEST_CHORDPRO);
const formatter = new HtmlDivFormatter();
document.querySelector('#chord-chart').innerHTML = formatter.format(song);
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Chord-above-lyric via `<pre>` + whitespace padding | FlexBox column layout via HtmlDivFormatter | ChordSheetJS v5+ | Responsive layout; no monospace font required |
| `HtmlTableFormatter` | `HtmlDivFormatter` | ChordSheetJS v8+ | Div layout preferred; table layout is non-responsive |
| modifier terminology (chord.modifier) | accidental terminology (chord.accidental) | v13.0.0 | Breaking change if manipulating chord objects directly |

**Deprecated/outdated:**
- `ChordSheetParser`: Replaced by `ChordsOverWordsParser` (documented as deprecated in source)
- `MeasuredHtmlFormatter`: Beta status, requires DOM/Canvas measurer setup — not needed for this phase

---

## Open Questions

1. **Tag constructor signature (name vs. name+value)**
   - What we know: `Tag` class is documented as `new Tag(name, value)` from source inspection. The `start_of_verse` tag accepts a label as its value (e.g., `{start_of_verse: label="Verse 1"}`).
   - What's unclear: Whether `Tag('start_of_verse', 'Verse 1')` produces the correct label rendering in `HtmlDivFormatter` vs. needing `Tag('start_of_verse', 'label="Verse 1"')`.
   - Recommendation: Verify by running the hardcoded ChordPro smoke test (plan 07-01) and inspecting the rendered `<h3 class="label">` text.

2. **Position-to-character accuracy**
   - What we know: `ChordAnnotation.position` is a 0.0–1.0 fraction of *time* within the lyric line. This maps proportionally to character position under the assumption that syllables are uniformly distributed in time.
   - What's unclear: For lines with irregular syllable timing (e.g., long pauses, melisma), the character offset may be noticeably wrong.
   - Recommendation: Accept the approximation for this phase — the requirement is DISP-01 (chords above correct syllable), not pixel-perfect alignment. A word-boundary snap (round to nearest word start) could improve quality but is not required.

3. **Section label strings from the pipeline**
   - What we know: `pipeline_result['sections']` contains a `label` field. The segmentation code produces labels, but their exact strings were not checked during this research.
   - What's unclear: Whether labels are always one of `["Verse", "Chorus", "Bridge"]` or can be `"Verse 1"`, `"Pre-Chorus"`, etc.
   - Recommendation: Read `backend/audio/segmentation.py` during plan 07-02 to confirm label values. The `sectionTypeFor()` function uses substring matching to handle variants safely.

---

## Sources

### Primary (HIGH confidence)
- GitHub: `martijnversluis/ChordSheetJS` — `src/chord_sheet/song.ts`, `src/chord_sheet/line.ts`, `src/chord_sheet/chord_lyrics_pair.ts`, `src/chord_sheet/tag.ts`, `src/song_builder.ts`, `src/index.ts`, `src/formatter/html_formatter.ts`, `src/formatter/html_div_formatter.ts`, `src/formatter/templates/html_div_formatter.ts`, `src/parser/ultimate_guitar_parser.ts`
- API docs: `martijnversluis.github.io/ChordSheetJS/classes/Song.html`, `HtmlDivFormatter.html`, `ChordsOverWordsParser.html`
- npm registry: `chordsheetjs@14.0.0` package.json (main, module, deps fields)
- Project codebase: `backend/audio/models.py` (ChartData, Section, LyricLine, ChordAnnotation), `backend/audio/chart_builder.py` (position semantics), `frontend/package.json` (Vite 7.3.1), `frontend/vite.config.js` (proxy setup), `frontend/src/main.js` (existing fetch + DOM pattern)

### Secondary (MEDIUM confidence)
- GitHub releases page: ChordSheetJS v14.0.0 and v13.0.0 release notes (section type support added to UltimateGuitarParser in v14; "modifier" → "accidental" rename in v13)

### Tertiary (LOW confidence)
- WebSearch results for HtmlDivFormatter CSS examples — not independently verified against source

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — ChordSheetJS 14.0.0 on npm confirmed; Vite 7 confirmed in package.json
- Architecture (Song construction pattern): HIGH — Line, ChordLyricsPair, Tag, Song APIs verified against GitHub source
- Position-to-character mapping: MEDIUM — logic is sound but edge cases (empty lines, position=0.0 first chord) need testing
- Pitfalls: HIGH — CSS injection, line type mixing, bundle size all confirmed from source

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (ChordSheetJS API is stable; jspdf dep brings volatility risk)
