"""Chart builder: aligns detected chords to user-provided lyrics by section."""

import re

from audio.models import ChordAnnotation, LyricLine, Section, ChartData


def _parse_lyrics(lyrics: str) -> list[list[str]]:
    """Split raw lyrics text into sections of lyric lines.

    Sections are delimited by blank lines (one or more empty/whitespace-only
    lines). Within each section, lines are split by newline, stripped, and
    filtered to remove empty strings.

    Args:
        lyrics: Raw lyrics string from the user.

    Returns:
        List of sections. Each section is a list of non-empty line strings.
    """
    raw_sections = re.split(r'\n\s*\n', lyrics.strip())
    sections = []
    for raw in raw_sections:
        lines = [line.strip() for line in raw.splitlines()]
        lines = [line for line in lines if line]
        if lines:
            sections.append(lines)
    return sections


def _align_chords_to_lines(
    section_start: float,
    section_end: float,
    chord_events: list[dict],
    lyric_lines: list[str],
) -> list[LyricLine]:
    """Distribute chord events across lyric lines using equal time slices.

    Divides [section_start, section_end) into N equal slices, one per lyric
    line. Each chord event is assigned to the line whose time slice contains
    the chord's timestamp. Chord position within a line is expressed as a
    0.0-1.0 fraction of the line's duration.

    Args:
        section_start: Section start time in seconds.
        section_end:   Section end time in seconds.
        chord_events:  List of {'chord': str, 'time': float} dicts.
        lyric_lines:   Lyric text lines for this section.

    Returns:
        List of LyricLine models with chords placed proportionally.
    """
    if not lyric_lines:
        return []

    n = len(lyric_lines)
    duration = section_end - section_start

    result: list[LyricLine] = []
    for i, text in enumerate(lyric_lines):
        line_start = section_start + (i / n) * duration
        line_end = section_start + ((i + 1) / n) * duration
        line_duration = line_end - line_start

        chords: list[ChordAnnotation] = []
        for event in chord_events:
            t = event['time']
            if line_start <= t < line_end:
                if line_duration == 0:
                    position = 0.0
                else:
                    position = round((t - line_start) / line_duration, 3)
                chords.append(ChordAnnotation(chord=event['chord'], position=position))

        result.append(LyricLine(text=text, chords=chords))

    return result


def build(pipeline_result: dict, lyrics: str) -> ChartData:
    """Build a ChartData model by aligning pipeline chords to lyric lines.

    Pairs each pipeline section with a lyric section (via zip — truncates at
    the shorter list so mismatched counts never raise an error). Chords are
    proportionally distributed across the lyric lines of each section.

    Args:
        pipeline_result: Dict with keys 'key', 'tempo_bpm', 'sections'.
                         Each section has 'label', 'start', 'chord_sequence'.
        lyrics:          Raw lyrics string from the user.

    Returns:
        ChartData Pydantic model ready for JSON serialisation.
    """
    lyric_sections = _parse_lyrics(lyrics)
    pipeline_sections = pipeline_result['sections']

    # ------------------------------------------------------------------
    # Compute section end times.
    # All but the last: end = start of the following section.
    # Last section: end = last chord time + 8.0 s (or start + 8.0 if no chords).
    # ------------------------------------------------------------------
    section_ends: list[float] = []
    for i, sec in enumerate(pipeline_sections):
        if i < len(pipeline_sections) - 1:
            section_ends.append(pipeline_sections[i + 1]['start'])
        else:
            chords = sec.get('chord_sequence', [])
            if chords:
                section_ends.append(chords[-1]['time'] + 8.0)
            else:
                section_ends.append(sec['start'] + 8.0)

    # ------------------------------------------------------------------
    # Build unique_chords list: first-appearance order, no duplicates.
    # Filter out None, empty string, and 'N' (no-chord marker).
    # ------------------------------------------------------------------
    seen: set[str] = set()
    unique_chords: list[str] = []
    for sec in pipeline_sections:
        for event in sec.get('chord_sequence', []):
            chord = event.get('chord')
            if chord and chord != 'N' and chord not in seen:
                seen.add(chord)
                unique_chords.append(chord)

    # ------------------------------------------------------------------
    # Pair pipeline sections with lyric sections (zip truncates at shorter).
    # ------------------------------------------------------------------
    chart_sections: list[Section] = []
    for (pipeline_sec, lyric_sec), sec_end in zip(
        zip(pipeline_sections, lyric_sections),
        section_ends,
    ):
        lines = _align_chords_to_lines(
            section_start=pipeline_sec['start'],
            section_end=sec_end,
            chord_events=pipeline_sec.get('chord_sequence', []),
            lyric_lines=lyric_sec,
        )
        chart_sections.append(Section(label=pipeline_sec['label'], lines=lines))

    return ChartData(
        key=pipeline_result['key'],
        bpm=pipeline_result['tempo_bpm'],
        unique_chords=unique_chords,
        sections=chart_sections,
    )
