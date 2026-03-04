"""Pydantic v2 response models — API contract for /analyze endpoint."""

from pydantic import BaseModel


class ChordAnnotation(BaseModel):
    chord: str
    position: float


class LyricLine(BaseModel):
    text: str
    chords: list[ChordAnnotation]


class Section(BaseModel):
    label: str
    lines: list[LyricLine]


class ChartData(BaseModel):
    key: str
    bpm: float
    unique_chords: list[str]
    sections: list[Section]
