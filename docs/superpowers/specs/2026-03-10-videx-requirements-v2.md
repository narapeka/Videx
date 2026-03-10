# Videx — Implementation Requirements v2

> Reorganized from `architecture/requirements.md` for planning and implementation.
> Resolves ambiguities and gaps identified during review.
> Original doc should be considered superseded by this one.

---

## 0. What This Document Is

This document is the single authoritative spec for building Videx. It is organized by
**module** (not by feature), so each section maps directly to an implementation unit.
Interfaces between modules are stated explicitly. Decisions that were ambiguous in v1
are resolved here.

---

## 1. System Overview

### 1.1 Purpose

Videx monitors one or more folders on a 115 Cloud storage (accessed via CloudDrive2),
recognizes incoming media files using LLM + TMDB, renames and organizes them into a
well-structured library, and optionally generates `.strm` files and notifies an Emby
server.

### 1.2 Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Backend framework | FastAPI |
| Frontend | Vue 3 (Vite) |
| Database | SQLite via SQLAlchemy (sync) |
| Task scheduling | APScheduler |
| Containerization | Docker + docker-compose |
| Package management | pip + requirements.txt |
| File operations | clouddrive2-client (gRPC) |
| File watching | watchfiles (on CloudDrive2 mount point) |

### 1.3 Deployment Layout

```
/config/
    videx.yaml          # all config (LLM, TMDB, Emby, file types, naming, categories, strm)
    videx.db            # SQLite database
    logs/               # log files (also written to stdout)
```

All config lives in `videx.yaml`. Tasks are stored in the database (not in the config
file). The YAML is read at startup; config changes require an app restart (no hot
reload in v1).

### 1.4 Module Map

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI Layer                    │
│   REST endpoints + WebSocket/SSE real-time updates  │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │  Pipeline Orchestrator  │  chains modules, drives state machine
        └─┬──────┬──────┬────────┘
          │      │      │
   ┌──────▼─┐ ┌──▼───┐ ┌▼──────────────┐
   │ Watch  │ │ Rec- │ │  Post-Org      │
   │Service │ │ogniz-│ │  (transfer,    │
   │(tasks) │ │ er   │ │  strm, emby)   │
   └──────┬─┘ └──┬───┘ └┬──────────────┘
          │      │       │
   ┌──────▼──────▼───────▼──────────────┐
   │             Core Services           │
   │  FileService  LLMClient  TMDBClient │
   │  CategoryService  NamingService     │
   └─────────────────────────────────────┘
```

---

## 2. Data Layer

### 2.1 Config File (`videx.yaml`)

The config file is the single source of truth for all connections, rules, and
defaults. It is read once at startup. Environment variable references (`${VAR}`) are
resolved at load time.

```yaml
file_types:
  video:    ['.mkv', '.mp4', '.avi', '.iso', '.ts', '.m2ts', '.wmv', '.flv', '.rmvb', '.mov']
  subtitle: ['.srt', '.ass', '.ssa', '.sub', '.sup', '.idx']
  companion: ['.nfo', '.jpg', '.png', '.bmp', '.txt']

clouddrive2:
  address: "192.168.1.100:19798"
  username: "user"
  password: "password"

llm:
  base_url: "https://api.openai.com/v1"
  api_key: "${LLM_API_KEY}"
  model: "gpt-4o-mini"
  batch_size: 10          # filenames per LLM call
  timeout: 30
  max_retries: 3

tmdb:
  api_key: "${TMDB_API_KEY}"
  proxy: ""
  rate_limit: 40          # requests per 10 seconds
  language: "zh-CN"       # primary language for metadata

naming:
  movie_folder: "{title} ({year}) {{tmdb-{tmdb_id}}}"
  movie_file:   "{title}.{ext}"
  tv_folder:    "{title} ({year}) {{tmdb-{tmdb_id}}}"
  season_folder: "Season {season}"
  episode_file:  "{title} - S{season:02d}E{episode:02d} - {episode_title}.{ext}"

categories:
  movie:
    REMUX:
      filename_keywords: 'remux'
      library_path: '/mnt/115/library/REMUX'
      organize_by_initial: true
    Web-DL:
      filename_keywords: 'web-dl,webdl'
      library_path: '/mnt/115/library/Web-DL'
      organize_by_initial: true
    ISO:
      file_extension: '.iso'
      library_path: '/mnt/115/library/ISO'
      organize_by_initial: true
    其他电影:
      library_path: '/mnt/115/library/其他电影'
      organize_by_initial: true
  tv:
    国漫:
      genre_ids: '16'
      origin_country: 'CN,TW,HK'
      library_path: '/mnt/115/library/国漫'
      organize_by_initial: false
    欧美剧:
      origin_country: 'US,GB,CA,AU,NZ,FR,DE,ES,IT,NL,PT,PL,SE,NO,DK,FI'
      library_path: '/mnt/115/library/欧美剧'
      organize_by_initial: true
    未分类:
      library_path: '/mnt/115/library/未分类'
      organize_by_initial: false

strm:
  enabled: true
  base_path: "/CloudDrive2/115"
  output_path: "/strm_library"
  path_mapping:
    from: "/mnt/115"
    to: "/CloudDrive2/115"

emby:
  address: "http://192.168.1.100"
  port: 8096
  api_key: "${EMBY_API_KEY}"
  auto_refresh: true
  libraries:
    - library_id: "abc123"
      name: "Movies"
      root_path: "/library/Movies"
    - library_id: "ghi789"
      name: "Strm Library"
      root_path: "/strm_library"
```

**Category match conditions** (all conditions on a rule must match; OR within a condition):

| Key | Type | Semantics |
|-----|------|-----------|
| `filename_keywords` | comma-separated strings | Match in original filename (case-insensitive) |
| `origin_country` | comma-separated ISO codes | TMDB `origin_country`, e.g. `CN,TW,HK` |
| `genre_ids` | comma-separated ints | TMDB genre IDs, e.g. `16` for animation |
| `original_language` | comma-separated codes | TMDB `original_language` |
| `file_extension` | comma-separated extensions | Video file extension |
| Exclusion prefix `!` | prefix any value | Exclude items matching this value |

Categories are evaluated **in order**; first match wins. A category with no conditions
is a fallback. If no fallback exists and no rule matches, the item is placed in a
default "Uncategorized" category with `library_path` = organized folder root (not
an error state).

**`organize_by_initial`:** When true, items are placed under `<library_path>/<initial>/`
where `<initial>` is the uppercase first letter of the title (using `pypinyin` for
Chinese titles → pinyin initial). Numerics go to `0-9`.

### 2.2 Database Schema

**`tasks`**

```sql
id              INTEGER PRIMARY KEY
name            TEXT NOT NULL
watch_folder    TEXT NOT NULL
organized_folder TEXT NOT NULL
unmatched_folder TEXT NOT NULL    -- subfolder of organized_folder, e.g. "_unmatched"
polling_interval INTEGER NOT NULL DEFAULT 300
auto_transfer   BOOLEAN NOT NULL DEFAULT FALSE
transfer_schedule TEXT             -- cron expression, nullable
overwrite       TEXT NOT NULL DEFAULT 'replace_folder'
strm_enabled    BOOLEAN NOT NULL DEFAULT TRUE
enabled         BOOLEAN NOT NULL DEFAULT TRUE
status          TEXT NOT NULL DEFAULT 'idle'
                -- values: idle | watching | processing | error
last_poll_at    DATETIME
last_error      TEXT
created_at      DATETIME NOT NULL
updated_at      DATETIME NOT NULL
```

**`media_items`**

```sql
id              INTEGER PRIMARY KEY
task_id         INTEGER              -- NULL for manual pipeline items
source_path     TEXT NOT NULL        -- original path in watch folder
media_type      TEXT                 -- 'movie' | 'tv'
status          TEXT NOT NULL        -- see state machine below
confidence      TEXT                 -- 'high' | 'low' | NULL
tmdb_id         INTEGER
title           TEXT
year            INTEGER
category        TEXT                 -- matched category name
organized_path  TEXT                 -- path after organize step
transferred_path TEXT                -- path in library after transfer
created_at      DATETIME NOT NULL
updated_at      DATETIME NOT NULL
```

**`media_items.status` state machine:**

```
detected
  └─► recognizing
        ├─► recognized      (high confidence → proceeds automatically)
        │     └─► organizing
        │           └─► organized
        │                 └─► transferring
        │                       └─► transferred
        │                             └─► strm_generated  (if strm enabled)
        ├─► unmatched       (low confidence or LLM/TMDB failure → moved to unmatched_folder)
        │     └─► recognized  (after user manual resolution)
        └─► failed          (unexpected error, not retried automatically)

Any state ──► skipped       (user action)
```

**`recognition_results`**

```sql
id              INTEGER PRIMARY KEY
media_item_id   INTEGER NOT NULL REFERENCES media_items(id)
llm_raw         TEXT                 -- raw LLM response JSON
tmdb_candidates TEXT                 -- JSON array of TMDB candidate objects
selected_tmdb_id INTEGER             -- final confirmed TMDB ID
confidence      TEXT                 -- 'high' | 'low'
created_at      DATETIME NOT NULL
```

**`file_operations`**

```sql
id              INTEGER PRIMARY KEY
media_item_id   INTEGER REFERENCES media_items(id)
operation       TEXT NOT NULL        -- 'move' | 'rename' | 'mkdir' | 'copy'
source_path     TEXT NOT NULL
target_path     TEXT NOT NULL
status          TEXT NOT NULL        -- 'planned' | 'completed' | 'failed'
timestamp       DATETIME NOT NULL
error           TEXT                 -- NULL on success
```

Each batch operation writes all planned moves with `status='planned'` before executing.
On success, status is updated to `completed`. On failure, status stays `planned` or
becomes `failed`, giving the user a full audit trail to manually reverse operations.

**`transfer_history`**

```sql
id              INTEGER PRIMARY KEY
task_id         INTEGER              -- NULL for manual pipeline
started_at      DATETIME NOT NULL
completed_at    DATETIME
file_count      INTEGER
status          TEXT NOT NULL        -- 'running' | 'completed' | 'failed'
affected_paths  TEXT                 -- JSON list of destination paths written
error           TEXT
```

**`logs`**

```sql
id              INTEGER PRIMARY KEY
task_id         INTEGER              -- NULL for manual pipeline
level           TEXT NOT NULL        -- DEBUG | INFO | WARNING | ERROR
message         TEXT NOT NULL
timestamp       DATETIME NOT NULL
```

Log cleanup: entries older than 30 days are deleted by a scheduled job (interval
configurable). Applies to both task logs and manual pipeline logs.

---

## 3. Core Services

### 3.1 FileService

Abstraction over `clouddrive2-client`. All file operations in the app go through this
service — never raw filesystem calls.

**Interface:**

```python
class FileService:
    def list_dir(self, path: str) -> list[FileEntry]: ...
    def move(self, src: str, dst: str) -> None: ...
    def copy(self, src: str, dst: str) -> None: ...
    def mkdir(self, path: str) -> None: ...
    def exists(self, path: str) -> bool: ...
    def stat(self, path: str) -> FileStat: ...
```

All operations raise `FileServiceError` on failure. Callers handle retries.

### 3.2 LLMClient

Sends batches of filenames/folder names to the LLM for media recognition.

**Batch input:** up to `batch_size` filenames in a single call.

**Expected LLM response format (JSON):**

```json
[
  {
    "input": "Test movie1.web-dl.2160p.AAC.mp4",
    "title": "Test Movie 1",
    "year": 2009,
    "media_type": "movie",
    "confidence": "high"
  },
  {
    "input": "Test tv show1",
    "title": "Test TV Show 1",
    "year": null,
    "media_type": "tv",
    "confidence": "low"
  }
]
```

**Port from:** `reference/AIGua/` LLM client + prompt templates, and
`reference/aigua.tv/llm.py`. Use the prompt templates from these references — do not
write new ones from scratch.

Rate limiting: token bucket, default `rate_limit` requests/sec from LLM config.

### 3.3 TMDBClient

Wraps TMDB REST API with rate limiting (40 req / 10 sec, token bucket).

**Operations:**

```python
class TMDBClient:
    def search_movie(self, title: str, year: int | None) -> list[TMDBCandidate]: ...
    def search_tv(self, title: str, year: int | None) -> list[TMDBCandidate]: ...
    def get_movie(self, tmdb_id: int) -> MovieDetail: ...
    def get_tv(self, tmdb_id: int) -> TVDetail: ...
    def get_season(self, tmdb_id: int, season: int) -> SeasonDetail: ...
    def get_episode(self, tmdb_id: int, season: int, episode: int) -> EpisodeDetail: ...
```

**Port from:** `reference/aigua.tv/tmdb.py`. This file has battle-tested rate limiting,
retry logic, proxy support, and language fallback handling. Port it as-is, adapting
to the class interface above.

### 3.4 CategoryService

Evaluates category rules in order against a recognized media item. Returns the first
matching category name and its config.

**Input:** `title`, `year`, `media_type`, `tmdb_detail` (genres, origin_country,
original_language), `filename` (for keyword matching), `file_extension`.

**Output:** `CategoryMatch(name: str, library_path: str, organize_by_initial: bool)`

If no rule matches and no fallback exists, returns a synthetic "Uncategorized" category
pointing to the task's `organized_folder`.

**Port from:** `reference/filenamecategory/__init__.py` for the rule evaluation logic
and pinyin initial extraction.

### 3.5 NamingService

Applies naming templates from config to produce organized paths.

**Inputs:** `TMDBDetail`, `episode info (season, episode, episode_title)`, `ext`, `naming config`

**Outputs:** folder path + filename strings

Template variables: `{title}`, `{year}`, `{tmdb_id}`, `{season}`, `{episode}`,
`{episode_title}`, `{ext}`. Double-brace `{{...}}` produces literal `{...}`.

---

## 4. Detection and Recognition

### 4.1 Media Detection

Determines whether an item in the watch folder is a **movie** or **TV show** based
on video file count. No LLM call needed.

**Rules:**

| Item type | Video file count | Additional check | Classification |
|-----------|-----------------|-----------------|---------------|
| Standalone file (no subfolder) | 1 | — | Movie |
| Subfolder | 1 | — | Movie |
| Subfolder | 2 | filename contains disc/part pattern | Movie (multi-disc) |
| Subfolder | 2 | no disc/part pattern | TV show |
| Subfolder | 3+ | — | TV show |

**Disc/part patterns** (case-insensitive): `disc1`, `disc2`, `disk1`, `disk2`, `CD1`,
`CD2`, `part1`, `part2`, `pt1`, `pt2`.

### 4.2 Movie Recognizer

**Input:** detected item (path + file list)
**Output:** `RecognitionResult(tmdb_id, title, year, confidence, candidates)`

**Port from:** `reference/AIGua/` — specifically the movie recognition + TMDB search
logic. Preserve confidence scoring and edge case handling exactly.

**Process:**
1. Extract title + year from filename/folder name via LLM
2. Search TMDB with extracted title (+ year if available)
3. Score candidates; select if single strong match → `confidence=high`
4. If multiple plausible candidates or ambiguous → `confidence=low`

### 4.3 TV Show Recognizer

**Input:** detected item (path + file list, folder structure)
**Output:** `RecognitionResult` + `EpisodeMapping` (per video file: season, episode, episode_title)

**Port from:** `reference/aigua.tv/tv_show_organizer.py` and `pattern.py` — these cover
all season/episode detection patterns. Do not rewrite; port and adapt to module interface.

**Season/episode patterns handled** (in priority order):

| Pattern | Example |
|---------|---------|
| `S01E01` | `show.S01E01.mkv` |
| `S01E01-E03` | multi-episode range |
| Season folder + bare number | `S02/1.mp4` → Season 2, Episode 1 |
| No season info, bare episode number | `episode1.mkv` → Season 1 |
| Absolute episode number | `Show - 25.mkv` → map via TMDB |
| Specials / SP / OVA | → Season 0 / "Specials" folder |

---

## 5. Organization Pipeline

### 5.1 Organize Step

Triggered automatically (high-confidence items) or after user resolution (unmatched items).

**Process per item:**
1. Apply `NamingService` to produce target folder + file names
2. Determine category via `CategoryService`
3. Log all planned moves to `file_operations` (status=`planned`)
4. Move files via `FileService` into the `organized_folder`:
   ```
   <organized_folder>/
     <category_name>/
       <movie_folder_name>/
         <movie_file>
         <subtitle_file(s)>     ← renamed to match video, deduped
         <companion_files>      ← original names kept
   ```
5. Mark `media_items.status = organized`
6. Update `file_operations` to `completed`

**Low-confidence / unrecognized items:**
- Moved to `unmatched_folder` (configured per task, e.g. `<organized_folder>/_unmatched/`)
- `media_items.status = unmatched`
- Listed in "Pending Review" in UI

**Subtitle deduplication** (per format extension):
- Keep one subtitle per format (`.srt`, `.ass`, `.sup`, etc.)
- Prefer Chinese subtitle if present (detect by `chs`, `cht`, `chinese`, `zh` in filename)
- Otherwise keep one arbitrarily
- Non-selected subtitles are **deleted** (they are not moved; user has already accepted
  the source copy)

### 5.2 Transfer Step

Moves organized files from `organized_folder` to their category's `library_path`.

**Overwrite modes:**

| Mode | Movie | TV Show |
|------|-------|---------|
| `replace_folder` | Delete existing movie folder, move new folder | Delete existing season folder, move new season folder |
| `append_episode` | Same as `replace_folder` | Move episode files one-by-one into existing season folder (overwrite individual files) |

**A-Z subfolders** (when `organize_by_initial=true`):
- Target path: `<library_path>/<initial>/<item_folder>`
- Initial: uppercase first letter via pypinyin for Chinese, `0-9` for numerics

**After transfer:**
- `media_items.status = transferred`
- Record all destination paths in `transfer_history.affected_paths`
- Source organized folder is removed (it was a move)

### 5.3 strm Generation

Generates `.strm` files mirroring the library folder structure.

**Path structure:**

```
Library:   <library_path>/<item_folder>/<video_file>.mkv
strm root: <strm_output_path>/
strm file: <strm_output_path>/<category_name>/<item_folder>/<video_file>.strm
```

**strm file content:**
```
/CloudDrive2/115/library/REMUX/Test Movie2 (2022) {tmdb-234555}/Test movie2.mkv
```
(after path mapping: replace `path_mapping.from` → `path_mapping.to` in library path)

**Companion files (subtitles, `.nfo`, `.jpg`, etc.):**
- **Copied** (not moved) from library path to the strm folder alongside the `.strm` file
- Originals in library path are **kept** (not deleted)

**After strm generation:**
- `media_items.status = strm_generated`
- Record all strm output paths in `transfer_history.affected_paths` (these paths are
  used for Emby refresh, not the library paths)

### 5.4 Emby Refresh

Sends targeted refresh calls to Emby after transfer and/or strm generation.

**Library matching:** For each path in `affected_paths`, find the Emby library whose
`root_path` is a prefix of that path. Call `POST /Library/Media/Updated` with the
matched sub-path.

**Refresh targets:**
- If strm was generated: refresh strm output paths (Emby reads from there)
- If only physical transfer (no strm): refresh physical library paths

---

## 6. Watch Service

### 6.1 File Change Detection

**Mechanism: polling via APScheduler + CloudDrive2 gRPC**

`watchfiles` is **not** used in production. CloudDrive2 gRPC is faster and more
reliable than filesystem events on a FUSE mount. The watch service polls
the `watch_folder` via `FileService.list_dir()` on each `polling_interval` tick.

`watchfiles` may be used as an optional development convenience but is not the
production mechanism.

**Change detection:** Compare the directory listing snapshot (filenames + sizes +
mtimes) from the current poll to the previous snapshot stored in memory. Items that
are new or have changed size trigger the pipeline.

### 6.2 Task Lifecycle

Tasks are stored in the `tasks` table. Task status values:

| Status | Meaning |
|--------|---------|
| `idle` | Task exists, watching disabled |
| `watching` | Polling loop is active, no processing running |
| `processing` | A pipeline run is in progress |
| `error` | Last run encountered an unrecoverable error |

APScheduler manages one job per enabled task (keyed by `task_id`). Starting a task
adds the job; stopping removes it.

### 6.3 Scheduled Transfer

If `transfer_schedule` is set (cron expression), APScheduler runs an independent
transfer job on that schedule. This runs regardless of `auto_transfer`. Items in
`status=organized` are transferred.

---

## 7. Manual Pipeline

The manual pipeline is an on-demand, one-shot operation. It uses the same core modules
as the watch-based pipeline but is driven by user interaction via a wizard UI.

**Steps:**
1. User selects source folder (CloudDrive2 folder picker)
2. App lists detected items (media type auto-detected, user can override)
3. User configures run: organized folder, overwrite mode, auto-transfer, strm, Emby
4. App runs pipeline; low-confidence items can be resolved inline
5. User reviews organized results; confirms transfer

**DB conventions for manual pipeline:**
- `media_items.task_id = NULL`
- `transfer_history.task_id = NULL`
- `logs.task_id = NULL`
- All file operations are still recorded in `file_operations`

---

## 8. API Layer (FastAPI)

### 8.1 Real-Time Updates

The frontend receives pipeline events via **Server-Sent Events (SSE)**.

`GET /api/events` — SSE stream. Events emitted:

```json
{ "type": "item_status_changed", "item_id": 42, "status": "organized" }
{ "type": "task_status_changed", "task_id": 1, "status": "processing" }
{ "type": "log_entry", "task_id": 1, "level": "INFO", "message": "..." }
{ "type": "pipeline_progress", "task_id": 1, "stage": "organize", "current": 3, "total": 10 }
```

### 8.2 REST Endpoints

**Tasks**

```
GET    /api/tasks                    list all tasks
POST   /api/tasks                    create task
GET    /api/tasks/{id}               get task detail
PUT    /api/tasks/{id}               update task settings
DELETE /api/tasks/{id}               delete task
POST   /api/tasks/{id}/start         enable watching
POST   /api/tasks/{id}/stop          disable watching
POST   /api/tasks/{id}/scan          trigger immediate scan
POST   /api/tasks/{id}/transfer      trigger transfer of all organized items
POST   /api/tasks/{id}/strm          trigger strm generation
POST   /api/tasks/{id}/emby-refresh  trigger Emby refresh
```

**Media Items (per task)**

```
GET    /api/tasks/{id}/items         list items (filterable by status)
GET    /api/items/{id}               get item detail + recognition result
POST   /api/items/{id}/resolve       submit manual TMDB resolution
POST   /api/items/{id}/skip          mark as skipped
POST   /api/items/{id}/rerun         re-run recognition
```

**Manual Pipeline**

```
POST   /api/manual/scan              scan a folder, return detected items
POST   /api/manual/run               start a manual pipeline run
GET    /api/manual/runs/{run_id}     get run status + results
POST   /api/manual/runs/{run_id}/transfer   confirm transfer step
```

**Settings**

```
GET    /api/settings                 get full config (API keys masked)
PUT    /api/settings                 update config + reload
POST   /api/settings/test/clouddrive2
POST   /api/settings/test/llm
POST   /api/settings/test/tmdb
POST   /api/settings/test/emby
```

**Logs**

```
GET    /api/tasks/{id}/logs          get logs (params: level, from, to, limit)
DELETE /api/tasks/{id}/logs          delete logs older than threshold
```

**File Browser (for CloudDrive2 folder picker)**

```
GET    /api/files/browse?path=...    list directory contents
```

### 8.3 Response Conventions

- All responses: `{ "data": ..., "error": null }` or `{ "data": null, "error": { "code": "...", "message": "..." } }`
- Pagination: `?page=1&per_page=50` on list endpoints; response includes `total`
- Timestamps: ISO 8601 UTC

---

## 9. Frontend (Vue 3)

### 9.1 Design

- Dark mode
- Mobile-responsive
- Uses SSE for real-time updates (no polling from frontend)

### 9.2 Information Architecture

```
/ (Dashboard)                — all tasks, activity feed, quick actions
/tasks/:id                   — task detail (tabbed)
  ?tab=activity              — activity feed
  ?tab=pending               — pending review
  ?tab=organized             — organized items
  ?tab=pipeline              — transfer / strm / emby controls
  ?tab=logs                  — task logs
  ?tab=settings              — task settings
/manual                      — manual pipeline wizard
/settings                    — global settings (4-section tabbed)
```

### 9.3 Key Components

- **TaskCard** (Dashboard): status badge, pending count, quick action buttons
- **ActivityFeed**: chronological list of pipeline events (SSE-driven, live)
- **PendingReviewList**: items needing manual resolution; inline TMDB search
- **FolderPicker**: CloudDrive2 tree browser (used in manual pipeline + task settings)
- **PipelineWizard**: 4-step wizard for manual pipeline
- **LogViewer**: filterable log stream per task

---

## 10. File Operation Semantics

All file moves within 115 Cloud are done via CloudDrive2 gRPC (rename/move API),
which is near-instant and does not consume bandwidth. This applies to:
- Organize step (watch folder → organized folder)
- Transfer step (organized folder → library folder)

`.strm` generation writes new files to the strm output path (local filesystem or
separate mount). Companion file copy during strm generation is also a local copy.

---

## 11. Reference Projects — Migration Guide

| Module | Port From | Notes |
|--------|-----------|-------|
| LLMClient | `reference/AIGua/` LLM code + `reference/aigua.tv/llm.py` | Use AIGua prompt templates for movie, aigua.tv for TV |
| TMDBClient | `reference/aigua.tv/tmdb.py` | Entire file, adapt to class interface |
| MovieRecognizer | `reference/AIGua/` recognition logic | Preserve confidence scoring exactly |
| TVShowRecognizer | `reference/aigua.tv/tv_show_organizer.py` + `pattern.py` | Preserve all edge cases |
| CategoryService | `reference/filenamecategory/__init__.py` | Port rule evaluation + pinyin initial logic |
| TransferService | `reference/addlib/addlib_core.py` | Port `replace_folder` + A-Z logic; adapt `append_episode` |

**Critical:** Read each reference file in full before porting. The requirements
descriptions are summaries — the reference implementations handle many more edge
cases than documented. Do not rewrite from the spec; port from the code.

---

## 12. Non-Functional Requirements

### 12.1 Performance

- Polling interval: configurable, default 300 seconds
- LLM: batch up to `batch_size` filenames per call
- TMDB: token bucket, max 40 req / 10 sec
- CloudDrive2 gRPC moves: near-instant for same-storage renames

### 12.2 Reliability

- API failures (LLM, TMDB, Emby): retry with exponential backoff (max `max_retries`), then log error, set item to `failed`
- CloudDrive2 unavailable: pause task, set `status=error`, alert via UI
- Pre-operation DB logging of planned moves enables manual recovery after crash

### 12.3 Security

- API keys stored in `videx.yaml` (file permissions protect them); never stored in DB
- GET `/api/settings` masks all API key values (replace with `***`)
- No authentication on the web UI in v1 (single-user, local network deployment)

### 12.4 Logging

- Dual output: SQLite `logs` table (for UI) + stdout (for `docker logs`)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Key events: file detected, LLM result, TMDB match, file moved, transfer complete, API error
- Cleanup: scheduled deletion of entries older than 30 days (configurable)

---

## 13. Docker Deployment

```yaml
# docker-compose.yml
services:
  videx:
    image: videx:latest
    ports:
      - "8080:8080"
    volumes:
      - ./config:/config
      - /mnt/115:/mnt/115         # CloudDrive2 mount point
      - /strm_library:/strm_library
    environment:
      - LLM_API_KEY=${LLM_API_KEY}
      - TMDB_API_KEY=${TMDB_API_KEY}
      - EMBY_API_KEY=${EMBY_API_KEY}
    restart: unless-stopped
```

Config file: `/config/videx.yaml`
Database: `/config/videx.db`
Logs (file): `/config/logs/`

---

## 14. Open Questions

These are unresolved decisions that the implementer should confirm before building
the affected modules:

1. **Rollback UI:** The `file_operations` table supports recovery, but no UI action for
   it exists. Add a "Revert operation" feature, or document it as manual DB inspection?

2. **Config hot reload:** Should `PUT /api/settings` reload config without restart?
   Current spec says restart required. Reconsider if settings page UX demands live reload.

3. **Multi-user / auth:** v1 has no auth. If the app will be exposed beyond local LAN,
   add basic auth or API key protection before deploying.
