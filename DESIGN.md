# TrendClip Desktop - Program Design & Architecture

**Version:** 1.5 + Queued Features  
**Last Updated:** 28 August 2025

## 1. Objectives (North Star)

### Core Mission
- **One-click, fully local Windows toolkit** that runs on a clean PC (no Python pre-install)
- **Self-healing** when tools are missing
- **Never auto-closing consoles** for visibility
- Everything under `%USERPROFILE%\TrendClipOne`

### Automation-First Pipeline
1. **Discover** → trending videos from YouTube
2. **Rank** → by views/likes/duration + keyword score
3. **Fetch** → download with yt-dlp
4. **Clip** → 9:16 vertical format
5. **Sidecars** → metadata, tags, thumbnails
6. **Upload** → optional YouTube Shorts
7. **Analytics** → income tracking in GBP

### Zero-Friction Onboarding
- Guided wizard for keys/filters
- Sensible defaults
- Desktop shortcuts
- Future "remote control" option

### Portable & Shippable
- Packager/USB build producing distributable ZIP
- Config + tools included
- One-click deployment

### Observability
- Robust logging
- Correction trails
- Clip statistics
- Clear dashboards

## 2. Feature Inventory

### ✅ Implemented (Stable Build 1.5)

#### Core Application
- **Standalone Dashboard**: tkinter GUI with tabs (Overview, Trending, Analytics)
- **Autopilot Controls**: Start/Stop with live status + progress bar
- **Setup Wizard**: Collects YouTube/OpenAI/Tavily/TikTok/GitHub + filter knobs
- **Live Log Tail**: Real-time logging in UI
- **Folder Integration**: Open feeds/folders from UI

#### Trending Pipeline
- **Feeds Pipeline**: Pulls YouTube "Most Popular" for region
- **Ranking Engine**: Views/likes/duration + keyword score
- **URL Management**: Writes top URLs to `feeds.txt`
- **UI Integration**: Push "top N" to feeds from Trending tab

#### Autopilot System
- **Loop Processing**: Reads `feeds.txt` → downloads → clips → sidecars
- **Download Engine**: yt-dlp integration with resume capability
- **Clip Engine**: FFmpeg processing (first N seconds)
- **File Management**: Moves originals to `processed/`
- **Sidecar Generation**: `.summary.txt`, `.tags.txt`, thumbnails
- **Statistics**: Logs to `clipstats.csv`
- **Cooldown Tracking**: `processed_urls.json`

#### Analytics & Income
- **GBP Revenue Tracking**: Dashboard plots views per clip
- **Cumulative Income**: Based on `clipstats.csv` and CPM (GBP) setting
- **Performance Metrics**: Processing time, success rates

#### Configuration & Logging
- **Versioned Config**: `TrendClip.config.json` (v1.5)
- **Local Storage**: All under `%USERPROFILE%\TrendClipOne`
- **Rolling Logs**: Dashboard log with lifecycle events
- **Corrections Log**: Filename fixes and sanitization trail

### 🔄 Queued / Partially Implemented

#### 9:16 Vertical Transform
- **Smart Framing**: Intelligent crop/scale + safe re-encode presets
- **Format Optimization**: H.264/AAC, black-bar avoidance heuristics
- **Resolution**: 1080×1920 @ 30/60fps
- **Audio Processing**: Normalize to -16 LUFS, limiter, stereo downmix

#### Self-Healing Toolchain
- **Auto-Fetch**: Portable FFmpeg/yt-dlp if missing
- **Checksum Validation**: Version pinning and integrity checks
- **Recovery**: Automatic tool restoration and retry

#### YouTube Uploader (Shorts)
- **OAuth Integration**: Browser-based authentication
- **Secrets Management**: `%USERPROFILE%\TrendClipOne\.secrets\`
- **Token Storage**: `client_secret.json`, `token.json`
- **Metadata**: Title, description, tags from sidecars

#### Packager & Distribution
- **One-Click Packager**: `-Pack` flag for ZIP creation
- **Desktop Shortcuts**: Start Menu + Desktop integration
- **Console Persistence**: Never auto-close for visibility
- **USB Build**: Portable, future-proof bundle

#### Advanced Features
- **Resource-Max Mode**: Parallel processing tuned to CPU/RAM/NVMe
- **Remote Control**: Local endpoint for autopilot control
- **Push Notifications**: iPhone integration (Email/Pushover/Telegram)
- **Environment Variables**: Prefer `OPENAI_API_KEY`, `YOUTUBE_API_KEY`, `TAVILY_API_KEY`
- **Saved Cue**: "do 1" triggers fetch workflow
- **Script UX**: Mini window with progress bar + Copy button

## 3. Program Design

### 3.1 High-Level Architecture

```
[User]
  |  (Wizard, Dashboard, CLI cues)
  v
[Launcher PS] —— starts ——> [App Core (Python)]
                                |  
                                +— [Trending Fetcher]
                                +— [Feeds Manager]
                                +— [Autopilot Orchestrator]
                                |       |
                                |       +— [Downloader (yt-dlp)]
                                |       +— [Clip Engine (FFmpeg)]
                                |       +— [Sidecar/Thumb Writer]
                                |       +— [Uploader (Shorts) — optional]
                                |
                                +— [Analytics & Income]
                                +— [Self-Heal & Health Checks]
                                +— [Packager]
                                +— [Notifier]
                                +— [Remote Control (local)]
                                +— [Logging]
```

### 3.2 Data Flow (End-to-End)

```
YouTube Trends/API  ──► Trending Fetcher ──► Ranked List ──► Feeds Manager ──► feeds.txt
                                                                │
                                                                ▼
                                                        Autopilot Orchestrator
                                                                │
                         ┌─────────────── Downloader (yt-dlp) ◄─┘
                         │               │
                         │               └──► Original video (.mp4/.mkv)
                         ▼
                    Clip Engine (FFmpeg) ──► 9:16 Clip (.mp4)
                         │                       + Thumbnail (.jpg)
                         │                       + Sidecars (.summary.txt/.tags.txt)
                         ▼
                    Analytics Writer ──► clipstats.csv (views, secs, cpm_gbp, est_gbp)
                         │
                         └──► (Optional) Uploader (Shorts) → YouTube
```

### 3.3 Autopilot State Machine

```
IDLE → (start) → SCAN_FEEDS → (url found) → CHECK_COOLDOWN →
  → (ok) DOWNLOAD → CLIP → SIDECARS → STATS → (upload?) → COMPLETE → SCAN_FEEDS
  → (cooldown hit) SKIP → SCAN_FEEDS
  → (error) RETRY_n → (exhausted) FAIL_LOG → SCAN_FEEDS
(stop) at any time → IDLE
```

### 3.4 Folder & File Layout

```
%USERPROFILE%\TrendClipOne\
  ├─ TrendClipStandalone.py
  ├─ TrendClip.config.json
  ├─ feeds.txt
  ├─ logs\
  │   ├─ dashboard.log
  │   └─ corrections.log
  ├─ downloads\ (raw)
  ├─ processed\ (archive originals)
  ├─ clips\ <YYYY-MM-DD>\ <sanitized_title>\
  │    ├─ clip.mp4
  │    ├─ thumb.jpg
  │    ├─ clip.summary.txt
  │    └─ clip.tags.txt
  ├─ stats\ clipstats.csv
  ├─ tools\ ffmpeg\, yt-dlp.exe (portable)
  └─ .secrets\ client_secret.json, token.json (OAuth), local keys if used
```

### 3.5 Configuration Schema (v1.5 → forward)

```json
{
  "version": "1.5",
  "paths": {
    "root": "%USERPROFILE%/TrendClipOne",
    "downloads": "downloads",
    "clips": "clips",
    "logs": "logs",
    "stats": "stats/clipstats.csv",
    "tools": "tools"
  },
  "region": "GB",
  "trending_limit": 50,
  "keywords": ["example", "topic"],
  "clip": { 
    "seconds": 60, 
    "target_aspect": "9:16", 
    "preset": "veryfast", 
    "crf": 23 
  },
  "income": { "cpm_gbp": 3.5 },
  "uploader": { "enabled": false, "mode": "shorts" },
  "remote": { "enabled": false, "port": 8765 },
  "notifications": { "enabled": false, "provider": "pushover" },
  "env_pref": ["OPENAI_API_KEY", "YOUTUBE_API_KEY", "TAVILY_API_KEY"]
}
```

### 3.6 Logging & Telemetry

- **dashboard.log**: Lifecycle events (start/stop, fetch, download, clip, upload, errors)
- **corrections.log**: Original filename → sanitized filename; reason
- **clipstats.csv**: timestamp, title, video_id, source_url, seconds, views, cpm_gbp, est_gbp, clip_path, thumb_path, status
- **Log Levels**: INFO (default), WARN, ERROR; rotate daily; max 10MB/roll

### 3.7 Error Handling & Recovery

- **Retry Policy**: 3 attempts with back-off per stage (download/clip/upload)
- **Quarantine**: Files that repeatedly fail land in `clips\_quarantine` with reason.txt
- **Self-Heal**: When ffmpeg/yt-dlp missing or bad checksum → auto-download into `tools\` and re-try

### 3.8 Installer & Packager Design

#### Installer Script (`Install_TrendClip_FreshStart.ps1`)
- **Flags**: `-Detached` (background), `-RunWizard` (open wizard after launch), `-Pack` (create distributable ZIP then exit)
- **Setup**: Creates `%USERPROFILE%\TrendClipOne`, folders, default config, shortcuts
- **Python Check**: Provisions minimal runtime or launches bundled build
- **First-Run Wizard**: Prompts for region, CPM (GBP), keywords, secrets (or detects env vars)
- **Progress UI**: Small window with progress bar; on finish, reveals Copy button with script text

#### Packager
- **ZIP Creation**: Excludes heavy caches; includes tools, config template, scripts, shortcuts
- **Output**: `TrendClipOne_<version>_<date>.zip` to Desktop

### 3.9 UX Design

#### Dashboard (Desktop)
- **Overview**: Start/Stop Autopilot, current status, next action, log tail, quick links
- **Trending**: Controls for region/limits/keywords; list with scores; buttons Send Top N to feeds / Open Selected
- **Analytics**: Charts for clips/day, views/clip, cumulative GBP, top performers

#### CLI Integration
- **Saved Cue**: Typing "do 1" executes fetch workflow (`TrendClip_Do1.ps1`)
- **Script Window Pattern**: Tiny modal with progress bar; complete shows Copy button

### 3.10 Performance & Resource Modes

- **Normal**: 1 download + 1 clip worker
- **Resource-Max**: N parallel downloads, M parallel clips; bounded by CPU cores, RAM, disk I/O; queue back-pressure; per-stage metrics

### 3.11 Security & Secrets

- **Environment Variables**: Prefer Windows env vars for keys; fallback to `%USERPROFILE%\TrendClipOne\.secrets`
- **Log Security**: Avoid printing secrets to logs; mask tokens
- **OAuth Storage**: Tokens under `.secrets\token.json` with file ACLs to current user

### 3.12 Extensibility & Remote Control

#### Local Remote Endpoint (opt-in)
- **POST** `/autopilot/start`, `/autopilot/stop`
- **POST** `/feeds` (add URLs)
- **GET** `/health`

#### Plugin Hooks
- Pre-download, post-clip, pre-upload, post-upload events
- Additional sources: TikTok/IG Reels (queued), RSS bridges

### 3.13 Diagnostics / Self-Test

- **First-Run Self-Test**: Checks tool versions, writes/reads test file, 5-sec synthetic clip with FFmpeg, verifies logs/paths
- **Health Indicator**: Surface in Overview tab with green/amber/red and "Fix" button that runs self-heal

### 3.14 9:16 Clip Strategy (queued)

- **Smart Framing**: Detect pillarboxes/letterboxes; center-weighted crop for subject; face/edge-contrast heuristics
- **Presets**: 1080×1920 @ 30/60fps; bitrate auto; `-pix_fmt yuv420p` for Shorts compatibility
- **Audio**: Normalize to -16 LUFS; limiter; stereo downmix if needed

### 3.15 USB / Portable Build

- **Entire Folder**: `TrendClipOne` folder is shippable; first run sets user-specific paths
- **Shortcuts**: Target launcher script; no installer admin rights required

### 3.16 Governance & Versioning

- **Semantic Versioning**: e.g., 1.5.0
- **CHANGELOG.md**: In root; version field in config; logs include version at start

## 4. Acceptance Criteria (per module)

### Trending Fetcher
- Returns N ranked items with deterministic score
- Handles API errors gracefully

### Feeds Manager
- Idempotent write to `feeds.txt`
- Deduplicates; preserves manual entries

### Downloader
- Supports YouTube URLs and playlists
- Resumes; timeout & retry
- Records source_url & video_id

### Clip Engine
- Produces H.264/AAC 9:16 MP4
- Under target duration
- Exits non-zero on error
- Writes sidecars & thumb

### Uploader
- Publishes to Shorts with title/tags from sidecars
- Captures returned video URL/ID

### Analytics
- Daily aggregation, cumulative GBP, top 10 clips report

### Self-Heal
- Restores missing tools and re-tries failed stage automatically

### Packager
- Produces ZIP under Desktop named `TrendClipOne_<ver>_<date>.zip` under 500MB (tools included)

## 5. Next Up (Execution Plan)

1. **Implement 9:16 pipeline** with presets + tests
2. **Add self-heal installers** for FFmpeg/yt-dlp with checksum pinning
3. **Wire Packager** (`-Pack`) into launcher + desktop ZIP output
4. **Add Shorts uploader** (OAuth) behind toggle; env-var first
5. **Surface Health widget** + one-click Fix in Overview
6. **Add resource-max concurrency** knobs + guardrails

---

**TrendClip Desktop** - Transform your video workflow with automated processing and YouTube integration.
