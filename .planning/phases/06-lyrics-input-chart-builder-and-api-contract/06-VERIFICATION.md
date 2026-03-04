---
phase: 06-lyrics-input-chart-builder-and-api-contract
verified: 2026-03-04T15:30:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
---

# Phase 6: Lyrics Input, Chart Builder, and API Contract Verification Report

**Phase Goal:** Users can paste lyrics into the interface and receive a structured ChartData JSON response that correctly aligns detected chords to the corresponding lyric lines by section
**Verified:** 2026-03-04T15:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                      | Status     | Evidence                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------- |
| 1   | User can type or paste lyrics into a textarea in the browser and submit alongside the MP3                                 | VERIFIED   | `frontend/src/main.js` line 9: `<textarea id="lyrics" rows="20">` present; line 34: `formData.append('lyrics', ...)` present |
| 2   | Backend returns ChartData JSON with sections, lyric lines, and chord annotations                                          | VERIFIED   | `/analyze` route has `response_model=ChartData`; `build_chart(result, lyrics)` returns a validated `ChartData` instance; all models import and construct cleanly |
| 3   | Chords are distributed across lyric lines proportionally — no section has all chords on one line while others have none    | VERIFIED   | `_align_chords_to_lines()` divides `[section_start, section_end)` into N equal slices, one per lyric line; runtime test with 3-line section confirmed G:maj→line 0, C:maj→line 1, D:maj→line 2 |
| 4   | unique_chords contains only distinct chord names (no duplicates, N filtered)                                              | VERIFIED   | `build()` uses `seen: set[str]` to track first appearance; filters `None`, empty string, and `'N'`; runtime test with duplicates and N confirmed `['G:maj', 'C:maj', 'D:maj']` |
| 5   | Pydantic response model validates ChartData and rejects malformed input with 422                                          | VERIFIED   | `@app.post('/analyze', response_model=ChartData)` present; `ValidationError/KeyError/ValueError` caught and re-raised as `HTTPException(422)`; `ValidationError` test passed |
| 6   | Missing or empty lyrics raise 422 before reaching chart builder                                                           | VERIFIED   | `main.py` line 163-164: `if not lyrics or not lyrics.strip(): raise HTTPException(status_code=422, detail='Lyrics are required')`; whitespace-only case also caught |
| 7   | detect_key() output is included in pipeline result and consumed by chart builder                                          | VERIFIED   | `main.py` line 65: `key = detect_key(audio['y_harmonic'], audio['sr'])`; line 87: `'key': key` in return dict; `build()` reads `pipeline_result['key']` |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact                              | Expected                                           | Status      | Details                                                                                         |
| ------------------------------------- | -------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------- |
| `backend/audio/models.py`             | 4 Pydantic v2 BaseModel classes                    | VERIFIED    | 25 lines; ChordAnnotation, LyricLine, Section, ChartData all present; no v1 syntax; imports cleanly |
| `backend/audio/chart_builder.py`      | _parse_lyrics, _align_chords_to_lines, build()     | VERIFIED    | 148 lines; all 3 functions substantive and correct; imports from audio.models; wired into main.py |
| `backend/main.py`                     | lyrics Form param, response_model=ChartData, 422   | VERIFIED    | 181 lines; all required wiring present; existing 413/415 validation preserved                   |
| `frontend/src/main.js`                | lyrics textarea + formData.append('lyrics', ...)   | VERIFIED    | 59 lines; textarea at line 9, formData.append at line 34; no manual Content-Type header        |

---

### Key Link Verification

| From                                    | To                               | Via                                           | Status     | Details                                                          |
| --------------------------------------- | -------------------------------- | --------------------------------------------- | ---------- | ---------------------------------------------------------------- |
| `models.py ChartData`                   | `pydantic.BaseModel`             | class inheritance                             | WIRED      | `class ChartData(BaseModel)` — runtime construction confirmed    |
| `models.py Section`                     | `LyricLine`                      | `lines: list[LyricLine]` field                | WIRED      | Field declared; nested construction verified                     |
| `chart_builder.py build()`              | `audio.models.ChartData`         | `return ChartData(...)` at line 143           | WIRED      | Constructs and returns ChartData; runtime test passed            |
| `main.py _run_pipeline()`               | `audio.key_detection.detect_key` | `key = detect_key(...)` at line 65             | WIRED      | Result dict carries `'key'` field consumed by `build()`         |
| `main.py analyze()`                     | `audio.chart_builder.build()`    | `chart = build_chart(result, lyrics)` line 167 | WIRED     | Called with pipeline result and lyrics; result returned          |
| `main.py analyze()`                     | `HTTPException(422)`             | `if not lyrics.strip(): raise HTTPException`  | WIRED      | Lines 163-164 and 169-170                                        |
| `main.py analyze()`                     | `Form(None)`                     | `lyrics: str = Form(None)` in signature       | WIRED      | Line 106; confirmed by route inspection                          |
| `frontend/src/main.js FormData`         | `/api/analyze lyrics param`      | `formData.append('lyrics', ...)` line 34      | WIRED      | Value read from `#lyrics` textarea; no manual Content-Type set  |

---

### Requirements Coverage

| Requirement | Status    | Blocking Issue |
| ----------- | --------- | -------------- |
| INPUT-02    | SATISFIED | None — textarea present; lyrics sent as multipart field; 422 on empty  |
| INTG-01     | SATISFIED | None — ChartData contract complete; backend returns structured JSON; Pydantic validates shape |

---

### Anti-Patterns Found

| File           | Line | Pattern               | Severity | Impact                                                                 |
| -------------- | ---- | --------------------- | -------- | ---------------------------------------------------------------------- |
| `main.py`      | 181  | `pass` in except OSError | Info  | Intentional silent ignore for temp file cleanup — correct pattern; not a stub |
| `main.js`      | 9    | `placeholder=` attr   | Info     | HTML input placeholder text — not a code stub, correct UX usage       |

No blockers or warnings found.

---

### Human Verification Required

The automated code checks fully cover the structural goal of this phase. However, one item requires human verification:

#### 1. End-to-end browser flow

**Test:** Start backend (`uvicorn main:app --reload`) and frontend (`npm run dev`). Open browser, select a real MP3, paste lyrics with blank-line-separated sections, click Analyze.
**Expected:** After 10-30 seconds, ChartData JSON is displayed with `key`, `bpm`, `unique_chords`, `sections` (each with `label` and `lines`), and chord annotations distributed across lines — not all on line 0.
**Why human:** Cannot verify real audio pipeline execution, browser rendering, or user-perceived chord distribution without running the full stack.

Note: Per 06-03-SUMMARY.md, this end-to-end flow was verified by the user during plan execution (checkpoint:human-verify approved). Structural code verification confirms the wiring is intact.

---

## Summary

All 7 observable truths verified against the actual codebase:

- `backend/audio/models.py`: Four substantive Pydantic v2 BaseModel classes (ChordAnnotation, LyricLine, Section, ChartData) import and validate correctly at runtime.
- `backend/audio/chart_builder.py`: Three fully implemented functions — `_parse_lyrics` splits on blank lines, `_align_chords_to_lines` distributes chords by equal time slice (runtime-tested with correct per-line assignment), `build()` assembles ChartData with deduplicated unique_chords and zip-truncation for mismatched section counts.
- `backend/main.py`: `detect_key()` wired into `_run_pipeline()` return dict; `/analyze` route carries `response_model=ChartData`, `lyrics: str = Form(None)` parameter, 422 guard for missing/empty lyrics, and ValidationError/KeyError/ValueError catch block. Existing 413/415 validation preserved.
- `frontend/src/main.js`: Textarea with `id="lyrics"` present in the upload form; `formData.append('lyrics', document.querySelector('#lyrics').value)` wired in the submit handler; no manual `Content-Type` header.

The phase goal is achieved: the complete pathway from user pasting lyrics in the browser to receiving a structured, validated ChartData JSON response is implemented and structurally sound.

---

_Verified: 2026-03-04T15:30:00Z_
_Verifier: Claude (gsd-verifier)_
