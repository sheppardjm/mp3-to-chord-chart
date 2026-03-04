# Phase 1: Project Scaffold - Research

**Researched:** 2026-03-03
**Domain:** FastAPI project setup + Vite vanilla JS scaffold + CORS wiring
**Confidence:** HIGH (official docs verified for all core decisions)

---

## Summary

Phase 1 is a standard "prove the stack" scaffold — no business logic, just get FastAPI running and Vite serving a page that successfully fetches from the backend. The technical domain is well-understood and every relevant piece has authoritative documentation.

The prescribed stack (FastAPI 0.135.1 + uvicorn + Vite vanilla JS) is correct and installable on the target machine (macOS, Python 3.14.2, Node 20.19.5). One important finding: Python 3.14.2 is installed locally, which is newer than the version FastAPI was originally designed for. FastAPI 0.135.1 includes the Python 3.14 compatibility fix (added in 0.128.1, backported through releases), so installation is clean — but `fastapi[standard]` extras can fail on 3.14 due to transitive binary dependencies. Install base `fastapi` + explicit `uvicorn` instead.

Two approaches exist for wiring frontend to backend: CORS headers on the backend, or a Vite proxy. For local dev, the Vite proxy approach is cleaner — the browser sees the same origin, CORS issues are impossible, and no CORS middleware is needed during development. In production, CORS would be configured. For this personal tool that will only ever run locally, the proxy approach is recommended and simpler.

**Primary recommendation:** `backend/` + `frontend/` flat layout at project root; Python venv at `backend/.venv`; Vite proxy to backend (no CORS config needed); pyproject.toml without build-system block (app, not library); single `main.py` with health endpoint; `GET /health` returns `{"status": "ok"}`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.1 | Python ASGI web framework | Auto-docs, async support, Pydantic validation; locked in project research |
| uvicorn | 0.41.0 | ASGI server | Standard runner for FastAPI; started with `uvicorn main:app --reload` |
| Vite | latest (>=6.x) | Frontend dev server + build tool | `npm create vite@latest` scaffolds vanilla JS in seconds; locked in project research |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.2.2 | `.env` file loading | When config (e.g., CORS origin, port) needs to be environment-specific |
| CORSMiddleware | (built into starlette, FastAPI dependency) | CORS headers on backend responses | Only needed if NOT using Vite proxy; not needed for Phase 1 dev workflow |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vite proxy (no CORS) | FastAPI CORSMiddleware | Proxy is simpler for all-local dev; CORSMiddleware is needed if frontend and backend are on different domains/hosts |
| `python -m venv .venv` | `uv venv` | uv is faster but requires installing uv; standard venv has zero additional dependencies |
| `pyproject.toml` | `requirements.txt` | pyproject.toml is the modern standard; requirements.txt is simpler but less informative |

### Installation

```bash
# Python backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fastapi==0.135.1 uvicorn==0.41.0

# Frontend
npm create vite@latest frontend -- --template vanilla
cd frontend
npm install
```

**Note on `fastapi[standard]`:** Do NOT use `pip install "fastapi[standard]"` on Python 3.14. Some transitive dependencies in the `[standard]` extra fail to build on Python 3.14 due to binary compilation requirements. Install `fastapi` and `uvicorn` as separate explicit packages instead.

---

## Architecture Patterns

### Recommended Project Structure

```
dontCave/              ← project root (already exists)
├── backend/
│   ├── .venv/         ← virtualenv (gitignored)
│   ├── main.py        ← FastAPI app + health endpoint
│   └── pyproject.toml ← Python project metadata + deps
├── frontend/          ← created by Vite scaffold
│   ├── index.html     ← entry point (Vite serves this)
│   ├── src/
│   │   ├── main.js    ← JS entry point
│   │   └── style.css  ← base styles
│   ├── package.json
│   └── vite.config.js ← proxy config pointing at backend
├── .planning/
└── Don't Cave.mp3
```

**Rationale:**
- `backend/` and `frontend/` as siblings at project root is the standard pattern for FastAPI + JS monorepos (confirmed via GitHub discussion #4344). Flat, discoverable, no magic.
- `main.py` at `backend/` root (not `backend/app/main.py`) keeps Phase 1 simple. The deeper `app/` nesting is for mature multi-module backends — unnecessary now. Can always be refactored in Phase 5 when the backend grows.
- `.venv/` inside `backend/` keeps the Python environment scoped to the backend directory.
- `vite.config.js` at the `frontend/` root is where Vite expects it.

### Pattern 1: Vite Proxy for Backend API Calls

**What:** Configure Vite's dev server to proxy requests to the backend. The frontend calls `/api/health` (same origin), Vite forwards the request to `http://localhost:8000/health`.

**When to use:** All local development. Eliminates all browser CORS restrictions without needing CORS headers on the backend.

**How it works:** The browser sends `GET http://localhost:5173/api/health`. Vite intercepts this, strips the `/api` prefix, forwards to `http://localhost:8000/health`, and returns the response. The browser sees everything as same-origin.

**vite.config.js:**
```javascript
// Source: https://vite.dev/config/server-options.html
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

**Frontend fetch call:**
```javascript
// Fetches from Vite dev server same-origin; Vite proxies to backend
const response = await fetch('/api/health')
const data = await response.json()
```

### Pattern 2: Minimal FastAPI App with Health Endpoint

**What:** Single `main.py` file with a FastAPI app instance and one GET endpoint at `/health`.

**When to use:** Phase 1 and beyond. The health endpoint stays. It's also used by Phase 4/5 success criteria.

**main.py:**
```python
# Source: https://fastapi.tiangolo.com/tutorial/first-steps/
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Run command:**
```bash
# From backend/ directory, with .venv activated
uvicorn main:app --reload --port 8000
```

The `--reload` flag enables hot-reload on file changes. The `--port 8000` makes the port explicit and documented.

### Pattern 3: Vite Vanilla Template Structure

**What:** The `npm create vite@latest frontend -- --template vanilla` command generates a ready-to-run project. The generated `src/main.js` and `index.html` are boilerplate that gets replaced with project-specific code.

**Generated structure:**
```
frontend/
├── public/
│   └── vite.svg
├── src/
│   ├── counter.js     ← boilerplate; delete or replace
│   ├── javascript.svg ← boilerplate; delete or replace
│   ├── main.js        ← entry point; replace contents
│   └── style.css      ← base styles; replace
├── .gitignore
├── index.html
└── package.json
```

**Generated index.html (canonical):**
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite + JS</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

**Minimal src/main.js for Phase 1 (replaces boilerplate):**
```javascript
document.querySelector('#app').innerHTML = '<div id="status">Loading...</div>'

fetch('/api/health')
  .then(r => r.json())
  .then(data => {
    document.querySelector('#status').textContent =
      `Backend: ${data.status}`
  })
  .catch(() => {
    document.querySelector('#status').textContent = 'Backend: unreachable'
  })
```

### Pattern 4: pyproject.toml for App (Not Library)

**What:** A `pyproject.toml` without a `[build-system]` block. This is valid for applications — the `[build-system]` block is only needed if you're publishing to PyPI. For an app, `[project]` with `requires-python` and `dependencies` is sufficient.

**pyproject.toml:**
```toml
[project]
name = "dontcave-backend"
version = "0.1.0"
description = "MP3-to-chord-chart personal tool - backend"
requires-python = ">=3.10"
dependencies = [
    "fastapi==0.135.1",
    "uvicorn==0.41.0",
    "librosa==0.11.0",
    "pychord==1.3.2",
    "numpy>=2.4",
    "soundfile==0.13.1",
    "python-multipart==0.0.22",
    "python-dotenv==1.2.2",
]
```

**Note:** Listing all future dependencies now means the file is always a source of truth. Running `pip install -r requirements.txt` is common but pyproject.toml is the modern equivalent. For pip to install from pyproject.toml: `pip install -e .` (editable install) or just install the deps directly.

**Simple alternative:** Keep pyproject.toml for metadata and use a `requirements.txt` generated from it for pip installs. The cleanest Phase 1 approach: put only Phase 1 deps in pyproject.toml now, install with pip, add more deps in later phases.

### Anti-Patterns to Avoid

- **`fastapi[standard]` on Python 3.14:** Fails due to transitive binary dependencies. Use `fastapi` + `uvicorn` separately.
- **CORSMiddleware in dev without a real need:** If using Vite proxy, CORSMiddleware adds unnecessary code and potential misconfiguration surface. Skip it in dev.
- **Hardcoding `http://localhost:8000` in the frontend JS:** Always route through the Vite proxy (`/api/...`) so the same code works regardless of where the backend runs.
- **`uvicorn main:app` without `--reload`:** During development, always use `--reload` to avoid manually restarting the server after every edit.
- **Putting `.venv` in the project root:** Put it in `backend/` so it's scoped to the backend. The root will eventually have both Python and Node artifacts and keeping them separated is cleaner.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CORS handling | Custom headers in route handlers | CORSMiddleware (Starlette/FastAPI) or Vite proxy | Preflight requests, headers, credentials are complex; already solved |
| Request proxying in dev | Express/Flask proxy shim | Vite `server.proxy` config | Built into Vite; zero code, just config |
| Dev server | `python -m http.server` | `vite` dev server | HMR, ES modules, proxy support |
| Python dependency listing | Custom install scripts | `pyproject.toml` + `pip install` | Standard; toolable |

**Key insight:** Phase 1 is almost entirely configuration, not code. The only real code is 5 lines of FastAPI and 10 lines of JS. Everything else is scaffolding commands and config files.

---

## Common Pitfalls

### Pitfall 1: Python 3.14 + `fastapi[standard]`

**What goes wrong:** `pip install "fastapi[standard]"` fails with build errors for transitive dependencies (binary compilation failures on Python 3.14).

**Why it happens:** Python 3.14 is very new. Some packages in the `[standard]` extras group (email-validator and friends) haven't published pre-built wheels for 3.14 yet and fall back to building from source, which may fail.

**How to avoid:** Install `fastapi==0.135.1` and `uvicorn==0.41.0` as separate packages. The base `fastapi` package (without extras) installs cleanly on Python 3.14.

**Warning signs:** `error: cargo manifest path /tmp/.../Cargo.toml` or `RuntimeError: Unable to find a compatible version` during pip install.

### Pitfall 2: Vite Proxy Rewrite and Backend Route Mismatch

**What goes wrong:** The frontend calls `/api/health`, the proxy rewrites to `/health`, but the backend only has a route at `/api/health` — 404.

**Why it happens:** Confusion about where the prefix stripping happens. The rewrite in vite.config.js `(path) => path.replace(/^\/api/, '')` strips `/api` before forwarding. So the backend must NOT have `/api` in its routes.

**How to avoid:** Establish the rule clearly: frontend calls `/api/*`, backend defines `/*`. The proxy handles the translation. Backend route is `@app.get("/health")`, frontend calls `fetch('/api/health')`.

**Warning signs:** 404 from backend for requests that the proxy is forwarding.

### Pitfall 3: Port Conflicts

**What goes wrong:** `uvicorn main:app` tries to bind port 8000 but something else is already there. Or `vite` tries port 5173 and bumps to 5174 silently.

**Why it happens:** Default ports are popular. Vite silently bumps to the next available port if 5173 is taken, which breaks the proxy config.

**How to avoid:** Always pass `--port 8000` to uvicorn explicitly. Check `lsof -i :8000` before starting. If Vite bumps ports, update the proxy config or kill the conflicting process.

**Warning signs:** Backend says `Application startup complete` on a different port than expected; Vite console says `Port 5173 is in use, trying another port`.

### Pitfall 4: FastAPI 0.132.0 `strict_content_type` Breaking Change

**What goes wrong:** Any POST request from the frontend without an explicit `Content-Type: application/json` header returns a 422 Unprocessable Entity from FastAPI 0.132.0+.

**Why it happens:** FastAPI 0.132.0 introduced strict JSON content-type validation by default. The health endpoint is a GET so this doesn't affect Phase 1, but it will affect Phase 5 (file upload). Noting here because it's a recent breaking change that may surprise developers upgrading from older tutorials.

**How to avoid:** Set `Content-Type: application/json` on all JSON POST requests. For file uploads (Phase 5), use `multipart/form-data` (which is correct for file uploads — this pitfall applies to JSON body endpoints).

**Warning signs:** 422 on POST requests that previously worked.

### Pitfall 5: Vite Dev Server CORS Security Change (Vite 6.x)

**What goes wrong:** Requests from third-party origins to the Vite dev server (serving the frontend assets) are blocked.

**Why it happens:** Vite 6.x changed `server.cors` default from `true` (allow all) to restricted mode. This affects scripts and assets served by Vite's dev server, not the API proxy.

**How to avoid:** When using the Vite proxy pattern, the Vite dev server is the only origin the browser talks to, so this change doesn't affect the dev workflow. Only an issue if loading Vite-served assets from a different origin.

**Warning signs:** Browser console shows `Access-Control-Allow-Origin` errors for `.js` or `.css` files served by Vite (not the API).

---

## Code Examples

### Complete main.py for Phase 1

```python
# Source: https://fastapi.tiangolo.com/tutorial/first-steps/
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Complete vite.config.js for Phase 1

```javascript
// Source: https://vite.dev/config/server-options.html
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

### Complete src/main.js for Phase 1

```javascript
// Fetches health endpoint from backend via Vite proxy
document.querySelector('#app').innerHTML = `
  <h1>dontCave</h1>
  <p id="status">Checking backend...</p>
`

fetch('/api/health')
  .then(r => r.json())
  .then(data => {
    document.querySelector('#status').textContent =
      `Backend: ${data.status}`
  })
  .catch(err => {
    document.querySelector('#status').textContent =
      `Backend: unreachable (${err.message})`
  })
```

### Backend start command

```bash
# From backend/ with .venv activated
uvicorn main:app --reload --port 8000
```

### Frontend start command

```bash
# From frontend/
npm run dev
```

### Verify backend health (curl)

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

### Verify proxy is working (frontend talks to backend)

Open browser to `http://localhost:5173`. Page should display "Backend: ok".

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `requirements.txt` only | `pyproject.toml` | PEP 517/518, ~2018; mainstream by 2022 | pyproject.toml is now the standard |
| Flask WSGI | FastAPI ASGI | 2019+ | Async support; no blocking on long operations |
| webpack / parcel | Vite | 2020+ | Instant dev server start, ES module native |
| `pip install "fastapi[standard]"` | `pip install fastapi uvicorn` | Python 3.14 (2025+) | `[standard]` extra breaks on Python 3.14 |
| `server.cors = true` (Vite default) | Restricted CORS (Vite 6+) | Vite 6.0.9, ~2025 | Dev assets no longer CORS-open by default |

**Deprecated/outdated:**
- `audioread`: Deprecated in librosa 0.10+, removal in 1.0. Don't reference in tutorials.
- `fastapi[standard]` on Python 3.14: Broken; use base `fastapi` + `uvicorn` explicitly.
- Vite <= 5 CORS-open default: Gone in Vite 6. Don't rely on it.

---

## Open Questions

1. **CSS approach for Phase 1**
   - What we know: CONTEXT.md defers CSS to Claude's discretion; project is a personal tool
   - What's unclear: No decision made on CSS framework vs raw CSS
   - Recommendation: Raw CSS with CSS custom properties. Zero dependencies, no build overhead, sufficient for a personal tool's simple UI. Use a single `src/style.css` imported in `main.js`. No framework needed until the UI needs a component library.

2. **Dev workflow: separate terminals vs Makefile/script**
   - What we know: Two servers must run: `uvicorn` and `vite`. CONTEXT.md defers to Claude.
   - What's unclear: Whether to provide a convenience script or just document the two commands
   - Recommendation: Document both commands clearly in comments at the top of each config file. A Makefile is overkill for a personal tool where both servers are usually started once and left running. If convenience is desired, a single shell script `./start-dev.sh` with two background processes is sufficient.

3. **Python environment: `python -m venv` vs `uv`**
   - What we know: Machine has Python 3.14.2. `uv` is faster and recommended by FastAPI docs. But `uv` requires installation.
   - What's unclear: Whether `uv` is installed on the machine (not checked).
   - Recommendation: Use `python -m venv .venv` — universally available, zero additional dependencies, perfectly adequate for one dev.

---

## Sources

### Primary (HIGH confidence)

- FastAPI official tutorial — https://fastapi.tiangolo.com/tutorial/first-steps/ — minimal app structure, uvicorn run command
- FastAPI CORS tutorial — https://fastapi.tiangolo.com/tutorial/cors/ — CORSMiddleware exact API
- FastAPI virtual environments — https://fastapi.tiangolo.com/virtual-environments/ — venv setup steps
- FastAPI release notes — https://fastapi.tiangolo.com/release-notes/ — 0.132.0 strict_content_type, 0.128.1 Python 3.14 support, 0.135.1 latest
- Vite Getting Started — https://vite.dev/guide/ — scaffold command, default port 5173, Node >=20.19 requirement
- Vite Server Options — https://vite.dev/config/server-options.html — proxy configuration exact API
- GitHub: vitejs/vite template-vanilla index.html — canonical template file contents
- Python Packaging User Guide — https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ — pyproject.toml without build-system for apps

### Secondary (MEDIUM confidence)

- FastAPI + frontend project structure discussion — https://github.com/fastapi/fastapi/discussions/4344 — `backend/` + `frontend/` flat layout community consensus
- FastAPI + Python 3.14 issues — https://github.com/fastapi/fastapi/discussions/14175 — `fastapi[standard]` install failure on Python 3.14
- FastAPI + Pydantic v1 Python 3.14 warning — https://github.com/fastapi/fastapi/discussions/14187 — fixed in 0.119.1+; not relevant for 0.135.1
- Vite CORS security change discussion — https://dev.to/mandrasch/vite-is-suddenly-not-working-anymore-due-to-cors-error-ddev-3673 — Vite 6.x CORS default change

### Tertiary (LOW confidence)

- FastAPI health check patterns — https://www.index.dev/blog/how-to-implement-health-check-in-python — `{"status": "ok"}` response format is a community convention, not an official standard

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified versions against PyPI and official docs; Python 3.14 compat confirmed via GitHub issues
- Architecture (directory layout): HIGH — FastAPI official discussion confirms `backend/` + `frontend/` pattern; Vite docs confirm structure
- Proxy configuration: HIGH — Vite official docs, exact API confirmed
- Python 3.14 pitfall: HIGH — confirmed via two separate GitHub discussions in fastapi repo
- CSS approach: MEDIUM — reasonable inference for personal tool; no official recommendation
- pyproject.toml without build-system: HIGH — Python Packaging User Guide explicitly supports this for apps

**Research date:** 2026-03-03
**Valid until:** 2026-06-03 (stable ecosystem; FastAPI and Vite release often but scaffold patterns are stable)
