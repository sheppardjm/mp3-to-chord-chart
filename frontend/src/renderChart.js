import {
  Song,
  Line,
  ChordLyricsPair,
  Tag,
  HtmlDivFormatter,
} from 'chordsheetjs'

const CHORD_CHART_CSS_ID = 'chordsheet-css'
const CHORD_CHART_CONTAINER_ID = 'chord-chart'

/** Map a section label string to a ChordSheetJS section type name */
function sectionTypeFor(label) {
  const lower = label.toLowerCase()
  if (lower.includes('chorus')) return 'chorus'
  if (lower.includes('bridge')) return 'bridge'
  return 'verse'
}

/**
 * Convert ChartData LyricLine chords (position 0.0-1.0) + text
 * into an array of ChordLyricsPair for one Line.
 */
function buildChordLyricsPairs(chords, text) {
  if (!chords || chords.length === 0) {
    return [new ChordLyricsPair('', text)]
  }

  // Sort by position ascending (defensive — should already be sorted)
  const sorted = [...chords].sort((a, b) => a.position - b.position)

  const pairs = []
  let prevCharIdx = 0

  for (let i = 0; i < sorted.length; i++) {
    const charIdx = Math.min(
      Math.round(sorted[i].position * text.length),
      text.length
    )

    // Text from prevCharIdx to charIdx is the lyrics fragment for the
    // PREVIOUS chord (or pre-chord leading text if i === 0)
    const fragment = text.slice(prevCharIdx, charIdx)

    if (i === 0 && charIdx > 0) {
      // Leading lyrics before the first chord: empty-chord pair
      pairs.push(new ChordLyricsPair('', fragment))
    } else if (i > 0) {
      // Assign fragment to the previous chord's lyrics
      const prev = pairs[pairs.length - 1]
      pairs[pairs.length - 1] = new ChordLyricsPair(prev.chords, fragment)
    }

    pairs.push(new ChordLyricsPair(sorted[i].chord, ''))
    prevCharIdx = charIdx
  }

  // Remaining text after the last chord
  const tail = text.slice(prevCharIdx)
  if (pairs.length > 0) {
    const last = pairs[pairs.length - 1]
    pairs[pairs.length - 1] = new ChordLyricsPair(last.chords, tail)
  }

  return pairs
}

/** Build a ChordSheetJS Song from a ChartData API response */
function buildSong(chartData) {
  const song = new Song()

  for (const section of chartData.sections) {
    const type = sectionTypeFor(section.label)

    // Section start tag line
    song.addLine(new Line({
      type,
      items: [new Tag('start_of_' + type, section.label)],
    }))

    // Content lines
    for (const lyricLine of section.lines) {
      const pairs = buildChordLyricsPairs(lyricLine.chords, lyricLine.text)
      song.addLine(new Line({ type, items: pairs }))
    }

    // Section end tag line
    song.addLine(new Line({
      type,
      items: [new Tag('end_of_' + type, '')],
    }))
  }

  return song
}

/** Render a ChartData object into the given container element */
export function renderChart(chartData, containerEl) {
  const formatter = new HtmlDivFormatter()

  // Inject scoped CSS once
  if (!document.getElementById(CHORD_CHART_CSS_ID)) {
    const styleEl = document.createElement('style')
    styleEl.id = CHORD_CHART_CSS_ID
    styleEl.textContent = formatter.cssString('#' + CHORD_CHART_CONTAINER_ID)
    document.head.appendChild(styleEl)
  }

  containerEl.id = CHORD_CHART_CONTAINER_ID
  containerEl.innerHTML = formatter.format(buildSong(chartData))
}
