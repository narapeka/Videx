# Media File State Machine — Design Spec

**Date:** 2026-03-10
**Status:** Approved

---

## Overview

A web-based media library management system that automates the classification, renaming, and organization of newly received media files using LLM recognition and TMDB metadata. A human review step (web UI) guards the final library from incorrect results.

---

## States

Files flow through four states, each represented by a folder on disk:

| State | Folder | Description |
|-------|--------|-------------|
| Received | `received/` | New files manually dropped in by the user |
| Received (temp) | `received/temp/` | Uncertain files — ignored by the processor |
| Organized | `organized/` | Recognized and renamed, awaiting human review |
| Failed | `failed/` | Recognition failed; held for manual retry |
| Library | `library/<category>/` | Final, approved destination |

**State transitions:**

```
received/ → (LLM + TMDB) → organized/   [recognition succeeded]
received/ → (LLM + TMDB) → failed/      [recognition failed]
organized/ → (human approve) → library/ [via web UI or auto-approve]
organized/ → (human reject) → failed/   [via web UI]
failed/ → (re-process) → organized/     [after manual correction]
```

---

## Architecture: Filesystem + SQLite

State is represented by **both** folder location and a SQLite database. The filesystem is always human-readable; the database enables rich metadata queries, confidence tracking, and the web UI.

Files in `received/` are **not** tracked in the DB — they enter the DB only when processing begins.

---

## Data Model

### `media_items` table

The recognition unit. One record per movie or TV show batch.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | |
| `type` | TEXT | `movie` or `tv_show` |
| `title` | TEXT | Official title from TMDB (or LLM guess if no match) |
| `tmdb_id` | INTEGER | TMDB identifier (null if no match) |
| `confidence` | TEXT | `high`, `medium`, or `low` |
| `category` | TEXT | Target library folder (e.g. `UHD Movies`, `US TV Shows`) |
| `state` | TEXT | `organized`, `failed`, or `library` |
| `error_reason` | TEXT | Human-readable reason for failure or low confidence |
| `created_at` | DATETIME | |
| `updated_at` | DATETIME | |

**All files belonging to the same media item share the same confidence and category.**

### `files` table

Individual files linked to a media item.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | |
| `media_item_id` | INTEGER FK | References `media_items.id` |
| `file_path` | TEXT | Current absolute path |
| `original_name` | TEXT | Filename before renaming |
| `file_type` | TEXT | `video`, `subtitle`, or `extra` |
| `state` | TEXT | Mirrors `media_items.state` |

**Examples:**
- Movie with 2 parts + 3 subtitles → 1 media item, 5 file records
- 3 episodes of the same show in one batch → 1 media item, 3 file records

---

## Folder Structure

```
received/
  Movie.Name.2023.mkv
  Show.S03E01.mkv
  temp/
    uncertain.file.mkv        ← ignored by processor

failed/
  unrecognized.mkv

organized/
  The.Matrix.1999.mkv
  Breaking.Bad.S03E01.mkv
  Breaking.Bad.S03E01.srt

library/
  UHD Movies/
  Web-DL Movies/
  China Movies/
  US TV Shows/
    Breaking Bad/
      Season 03/

videx.db                      ← SQLite database
```

---

## Processing Pipeline

When processing is triggered, the following steps run on files in `received/` (excluding `received/temp/`):

1. **Scan & group** — collect all video files; group files that appear to belong together (same filename prefix, same subfolder) into candidate media items.

2. **LLM recognition** — send filenames to LLM. LLM returns: `title`, `year`, `type` (movie/tv_show), `season`/`episode` if TV, a `confidence` level (high/medium/low), and a plain-language reason for the confidence rating.

3. **TMDB lookup** — query TMDB using LLM's title + year. On match: enrich with `tmdb_id`, official title, poster URL, genres, origin country. On no match: confidence is downgraded to `low`.

4. **Category classification** — combine filename keywords (e.g. `2160p` → UHD, `WEB-DL` → Web-DL) with TMDB metadata (origin country, language → China Movie, US TV Show, etc.) to determine the `category`.

5. **Outcome:**
   - **Succeeded:** rename files using the standard naming convention → move to `organized/` → write `media_items` + `files` records to DB → remove from `received/`
   - **Failed:** move files to `failed/` → write DB record with `state=failed` + `error_reason` → remove from `received/`

6. **Auto-approve (future):** if `confidence = high` and auto-approve is enabled in settings, skip the review queue and move directly to Library.

After every run, `received/` is empty (all files moved to either `organized/` or `failed/`).

### Ongoing TV Shows

New episodes of an ongoing TV show that already exists in the Library are **appended** (not blocked). If an episode file already exists in Library, it is **overwritten** — the newer file wins.

---

## Web Application

A locally-hosted web app. The server runs continuously; all interaction happens in the browser.

### Pages

| Page | Purpose |
|------|---------|
| **Dashboard** | Status counters (received / pending review / failed / library), "Run Now" button, watcher status, recent activity log |
| **Review** | Queue of organized media items with confidence badges, TMDB metadata, file list, Approve / Reject per item, "Approve All High" bulk action, confidence reason shown for medium/low |
| **Failed** | Unrecognized files with error reasons, Re-process button |
| **Library** | Browse the library by category |
| **Settings** | Folder paths, file watcher on/off, cron schedule, auto-approve confidence threshold, TMDB API key, LLM config |

### Triggering

All three trigger modes ultimately run the same processing pipeline:

| Mode | How |
|------|-----|
| **Manual** | "Run Now" button on Dashboard |
| **File watcher** | Server watches `received/` for new files; waits for a settle delay (~30s) before triggering to avoid processing partial copies |
| **Scheduled** | Cron-style schedule configured in Settings; runs processing at the specified interval |

---

## Confidence & Auto-Approval

Confidence reflects the quality of the recognition result for a given batch — it is not related to what is already in the Library.

| Confidence | Meaning | Default behaviour |
|------------|---------|-------------------|
| `high` | LLM certain + TMDB match found | Auto-approvable (future feature) |
| `medium` | LLM somewhat certain, or minor TMDB ambiguity | Requires review |
| `low` | LLM guessed from filename only, or no TMDB match | Requires review |

The DB stores confidence and error reason from day one, so auto-approval rules can be enabled later without a schema change.

---

## Key Constraints

- `received/temp/` is never touched by the processor — it is for uncertain files awaiting manual judgement
- Recognition unit is the **media item** (show or movie), not individual files — all files in a batch that belong to the same item share one confidence score and one category
- `received/` is always emptied after a processing run — either to `organized/` or `failed/`
- The web app is the only interface for day-to-day use
