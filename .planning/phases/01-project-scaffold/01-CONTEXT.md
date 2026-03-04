# Phase 1: Project Scaffold - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up a running FastAPI backend and Vite vanilla JS frontend, wired together with CORS configured. No business logic — just prove the stack runs and the two halves can communicate.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User deferred all scaffold decisions to Claude. The following are open for Claude to decide during planning/implementation:

- Project layout (directory structure, monorepo organization)
- Dev workflow (how to start backend/frontend, scripts vs manual)
- Frontend CSS approach (framework vs raw CSS, theming)
- API conventions (endpoint naming, response format, error shape)
- Python environment setup (virtualenv, pyproject.toml structure)
- Node/npm setup (package.json structure, dev dependencies)

**Guiding constraint from research:** FastAPI 0.135.1 + uvicorn, Vite vanilla JS template, soundfile 0.13.1 for MP3 support. Keep it simple — personal tool.

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow patterns from STACK.md research.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-project-scaffold*
*Context gathered: 2026-03-03*
