# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## What this project is

**Asad** is a self-hosted PWA for managing film/video translation projects and
downloading source videos. It runs as a single FastAPI process that serves both
the JSON API (`/api/*`) and the static PWA frontend (everything else). The app
is designed to be installed as a desktop app on Windows (Chrome/Edge) and added
to the Home Screen on iPhone (Safari). The UI strings and most docs are in
Vietnamese; code identifiers and comments are mixed English/Vietnamese.

Core capabilities:
- **Projects** — one per film/episode, tracking source→target language,
  provider, and source URL.
- **Translations** — timestamped subtitle lines with a status workflow
  (`draft → in_progress → reviewing → completed`); exportable as `.srt`.
- **Downloads** — a background async queue that streams video files to
  `storage/videos/`, with progress polling, cancel/retry, and a direct
  "save to device" endpoint.
- **Providers** — a plugin registry so a new download source = one new Python
  file (no other code changes needed).

## Running & developing

```bash
pip install -r requirements.txt
python run.py            # serves on 0.0.0.0:8000
```

- App: <http://localhost:8000>  ·  Swagger docs: <http://localhost:8000/docs>
- `run.py` launches uvicorn with `reload=False`. For active development run
  `uvicorn backend.main:app --reload` instead.
- There is **no test suite, linter config, or CI** in the repo. Verify changes
  manually via `/docs` or the UI. If you add tooling, document it here.

## Architecture

```
run.py                      # uvicorn entrypoint → backend.main:app
backend/
  main.py                   # FastAPI app, CORS, lifespan (init_db + start worker),
                            # router includes, static mount of frontend/ at "/"
  config.py                 # paths; creates storage dirs; SQLite DATABASE_URL
  database.py               # SQLAlchemy Base, engine, SessionLocal, get_db, init_db
  models.py                 # Project, Download, Translation + status enums
  schemas.py                # Pydantic v2 request/response models
  download_manager.py       # async background worker (single global `manager`)
  downloaders/
    base.py                 # BaseDownloader, DownloadContext/Result, registry
    generic.py              # GenericHttpDownloader (streams any direct HTTP URL)
    douyin.py               # placeholder provider (enabled=False)
    hongguo.py              # placeholder provider (enabled=False)
    __init__.py             # imports provider modules so they self-register
  routers/
    projects.py             # /api/projects CRUD
    translations.py         # /api/translations CRUD + /export/srt
    downloads.py            # /api/downloads CRUD + /providers + /{id}/file
frontend/                   # vanilla PWA (no build step, no framework)
  index.html, app.js, style.css
  manifest.json, sw.js      # PWA manifest + service worker (caches app shell)
  icons/                    # 192 & 512 px PWA icons
storage/                    # runtime data (gitignored except .gitkeep)
  app.db                    # SQLite DB (created at startup)
  videos/, subtitles/       # downloaded files
tools/
  fast_render.py            # standalone CLI: region blur + burn SRT subs via
                            # ffmpeg (NVDEC/NVENC w/ CPU fallback); stdlib only
  README.md                 # usage & performance notes (Vietnamese)
```

### Data model (`backend/models.py`)
- `Project` 1→N `Download` and 1→N `Translation`, both with
  `cascade="all, delete-orphan"` and `ON DELETE CASCADE`.
- `DownloadStatus`: `pending | downloading | completed | failed | cancelled`.
- `TranslationStatus`: `draft | in_progress | reviewing | completed`.
- Tables are created with `Base.metadata.create_all` at startup. **There are no
  migrations** — if you change a model, existing `storage/app.db` rows won't be
  altered. During development, deleting `storage/app.db` recreates the schema.

### Download flow
1. `POST /api/downloads` resolves a provider via `registry.resolve(url, provider)`,
   inserts a `pending` row, and calls `manager.enqueue(row.id)`.
2. The `DownloadManager` worker (started in the app lifespan) processes the
   queue **one job at a time**. It re-validates the provider, refuses disabled
   non-generic providers, sets status `downloading`, then runs
   `downloader.download(ctx, on_progress)`.
3. Progress is persisted to the DB (via short-lived sessions) so any client can
   poll `GET /api/downloads/{id}`. On success the row becomes `completed` with
   `file_path`/`file_size`; on exception it becomes `failed` with an error.
4. `GET /api/downloads/{id}/file` streams the saved file back for direct save.

### Adding a download provider
Create `backend/downloaders/<name>.py`, subclass `BaseDownloader`, register it,
and import it in `backend/downloaders/__init__.py` so it self-registers:

```python
@registry.register("myprovider")
class MyDownloader(BaseDownloader):
    name = "My Provider"
    enabled = True                       # False = placeholder, worker rejects it

    @classmethod
    def matches(cls, url: str) -> bool:  # used for auto-detection
        return "example.com" in url

    async def download(self, ctx, on_progress):
        # resolve to a direct URL, then reuse GenericHttpDownloader, or stream
        # to ctx.output_dir yourself and call on_progress(0..1) as you go.
        ...
```

The Providers tab and `GET /api/downloads/providers` pick it up automatically.
`registry.resolve` falls back to the `generic` provider when nothing matches.

### Frontend
- Plain ES (no bundler/framework). `app.js` holds a single `state` object,
  fetches the API with the `api()` helper, and renders tab views
  (projects / translate / downloads / providers). Edit files directly — no build.
- `sw.js` caches the app shell (`asad-shell-v1`) but **never** caches `/api/*` or
  non-GET requests. Bump the `CACHE` version string when you change cached assets.

## API surface

- Projects: `GET/POST /api/projects`, `GET/PATCH/DELETE /api/projects/{id}`
- Translations: `GET/POST /api/translations`, `PATCH/DELETE /api/translations/{id}`,
  `GET /api/translations/export/srt?project_id=…`
- Downloads: `GET/POST /api/downloads`, `GET /api/downloads/{id}`,
  `POST /api/downloads/{id}/cancel|retry`, `DELETE /api/downloads/{id}`,
  `GET /api/downloads/{id}/file`, `GET /api/downloads/providers`
- Health: `GET /api/health`

## Conventions

- **Stack**: FastAPI + SQLAlchemy 2.0 (typed `Mapped` columns) + Pydantic v2
  (`ConfigDict(from_attributes=True)` on response models). `httpx` + `aiofiles`
  for async streaming downloads. Python ≥ 3.10 (uses `X | None` unions).
- **Imports inside `backend/`** are relative (`from ..database import get_db`).
- **DB access in routes** uses the `get_db` dependency; the background worker
  manages its own `SessionLocal()` sessions (and uses fresh short-lived sessions
  for progress writes to avoid cross-thread session sharing).
- **Routers** use `APIRouter(prefix="/api/...", tags=[...])` and typed
  `response_model`s; raise `HTTPException` for errors.
- New `storage/` artifacts and `app.db` are gitignored — never commit them.

## Git workflow for this environment

- Develop on branch **`claude/claude-md-docs-ot8g7r`**; create it locally if
  missing. Never push to another branch without explicit permission.
- Commit with clear messages and `git push -u origin <branch>`. Do **not** open
  a pull request unless explicitly asked.
- Keep `README.md` (user-facing, Vietnamese) and this file in sync when behavior
  or structure changes.
