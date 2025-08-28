<# 
 File: Install_TrendClip_Desktop.ps1
 Purpose: Desktop (no external browser) TrendClip — wraps the Dash app in a native window via pywebview.
 Usage:
   .\Install_TrendClip_Desktop.ps1                      # install + run desktop app (venv)
   .\Install_TrendClip_Desktop.ps1 -UseSystemPython     # use system Python (no venv)
   .\Install_TrendClip_Desktop.ps1 -Reinstall           # rebuild venv
   .\Install_TrendClip_Desktop.ps1 -RebuildDash         # force-reinstall dash/plotly/pywebview
   .\Install_TrendClip_Desktop.ps1 -Detached            # start in background
   .\Install_TrendClip_Desktop.ps1 -Pack                # create distributable ZIP and exit
   .\Install_TrendClip_Desktop.ps1 -RunWizard           # also open CLI wizard console
   .\Install_TrendClip_Desktop.ps1 -Purge               # STOP processes & DELETE %USERPROFILE%\TrendClipOne
#>

param(
  [switch]$Detached,
  [switch]$RunWizard,
  [switch]$Pack,
  [switch]$Reinstall,
  [switch]$RebuildDash,
  [switch]$UseSystemPython,
  [switch]$Purge
)

$ErrorActionPreference = 'Stop'
$Version = '1.9.0-desktop'   # bumped for purge support

function Write-Log { param([string]$Message)
  $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  if (-not $script:LogFile) { $script:LogFile = Join-Path $env:USERPROFILE 'TrendClipOne\logs\install.log' }
  $logDir = Split-Path -Parent $script:LogFile
  if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
  Add-Content -LiteralPath $script:LogFile -Value "[$ts] $Message"
  Write-Host $Message
}

function Ensure-Dir { param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null }
}

function Write-TextFileUtf8 { 
  param([Parameter(Mandatory=$true)][string]$Path,[Parameter(Mandatory=$true)][string]$Content)
  $dir = Split-Path -Parent $Path; Ensure-Dir $dir
  [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
}

function Get-FreePort { param([int]$Start=8700,[int]$End=8999)
  for ($p=$Start; $p -le $End; $p++) {
    try { $l=[System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$p); $l.Start(); $l.Stop(); return $p } catch {}
  }
  throw "No free TCP port in $Start..$End"
}

function Stop-TrendClipProcesses {
  Write-Log "Scanning for running TrendClip processes..."
  try {
    $procs = Get-CimInstance Win32_Process | Where-Object {
      ($_.Name -match 'python\.exe' -and $_.CommandLine -match 'TrendClipDesktop\.py|TrendClipDashboard_Standalone\.py') -or
      ($_.Name -match 'TrendClipDesktop\.exe')
    }
    foreach ($p in $procs) {
      Write-Log "Stopping PID $($p.ProcessId): $($p.Name)"
      Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
  } catch {
    Write-Log "Process scan/stop failed (non-fatal): $_"
  }
}

# Base paths
$BASE   = Join-Path $env:USERPROFILE 'TrendClipOne'
$ASSETS = Join-Path $BASE 'assets'
$SECRETS= Join-Path $BASE '.secrets'
$SCRIPTS= Join-Path $BASE 'scripts'
$DIST   = Join-Path $BASE 'dist'
$LOGS   = Join-Path $BASE 'logs'
$VENV   = Join-Path $BASE '.venv'

# Purge (optional full reset)
if ($Purge) {
  Write-Host "⚠ PURGE MODE: This will delete $BASE completely (including .secrets). CTRL+C to abort." -ForegroundColor Yellow
  Start-Sleep -Seconds 2
  Stop-TrendClipProcesses
  if (Test-Path -LiteralPath $BASE) {
    Write-Log "Removing $BASE ..."
    try {
      # First attempt
      Remove-Item -LiteralPath $BASE -Recurse -Force -ErrorAction Stop
    } catch {
      Write-Log "Direct removal failed, retrying with CMD rmdir: $_"
      # Retry via cmd (sometimes handles locked junctions better)
      & cmd /c "rmdir /s /q `"$BASE`"" | Out-Null
      Start-Sleep -Milliseconds 500
      if (Test-Path -LiteralPath $BASE) {
        Write-Log "Purge failed. Close any running apps using TrendClipOne and re-run with -Purge."
        throw
      }
    }
  } else {
    Write-Log "Nothing to purge; $BASE does not exist."
  }
}

# Create fresh structure
Ensure-Dir $BASE; Ensure-Dir $ASSETS; Ensure-Dir $SECRETS; Ensure-Dir $SCRIPTS; Ensure-Dir $DIST; Ensure-Dir $LOGS
$script:LogFile = Join-Path $LOGS 'install.log'
Write-Log "TrendClip Desktop v$Version — Installing to $BASE"

# Version & env
Write-TextFileUtf8 -Path (Join-Path $BASE 'VERSION') -Content $Version
$port = Get-FreePort -Start 8700 -End 8999
$env:TRENDCLIP_PORT = "$port"
$env:TRENDCLIP_BIND = '127.0.0.1'
$env:TRENDCLIP_BASE = $BASE
Write-Log "Selected port: $env:TRENDCLIP_PORT"

# requirements.txt
$requirements = @'
dash>=2.16
plotly>=5.22
requests>=2.32
pandas>=2.2
PyYAML>=6.0
tenacity>=8.3
google-api-python-client>=2.153
google-auth>=2.33
google-auth-oauthlib>=1.2
google-auth-httplib2>=0.2
moviepy>=1.0.3
pywebview>=4.4
yt-dlp>=2025.1.1
'@
Write-TextFileUtf8 -Path (Join-Path $BASE 'requirements.txt') -Content $requirements

# config.yaml
$config = @"
version: $Version
currency: GBP
app:
  port_env: TRENDCLIP_PORT
  bind_env: TRENDCLIP_BIND
  open_browser: false
paths:
  base: .
  assets: assets
  secrets: .secrets
  dist: dist
  logs: logs
youtube:
  scopes:
    - https://www.googleapis.com/auth/youtube.upload
  default_privacy: private
  add_shorts_hashtag: true
keys:
  prefer_env: true
"@
Write-TextFileUtf8 -Path (Join-Path $BASE 'config.yaml') -Content $config

# CSS
$css = @'
:root { --gap: 12px; --radius: 14px; }
body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; background:#0b0f17; color:#e8eef9; }
.container { max-width: 1200px; margin: auto; padding: 24px; }
.card { background:#121826; padding:16px; border-radius:var(--radius); box-shadow:0 2px 24px rgba(0,0,0,.25); }
button, .btn { border:none; border-radius:12px; padding:10px 14px; font-weight:600; cursor:pointer; }
.link { color:#8cc6ff; text-decoration:none; }
pre { background:#0d1320; border-radius:12px; padding:12px; overflow:auto; }
input, select, textarea { background:#0d1320; color:#e8eef9; border:1px solid #1e293b; border-radius:10px; padding:10px; width:100%; }
.grid { display:grid; gap:var(--gap); }
.grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
@media (max-width:900px){ .grid-2,.grid-3{ grid-template-columns: 1fr; } }
'@
Write-TextFileUtf8 -Path (Join-Path $ASSETS 'style.css') -Content $css

# video_helpers.py
$video_helpers_py = @'
"""Helper functions for the CLI wizard and dashboard demos."""
from __future__ import annotations
from typing import Iterable, List, Dict

def _safe_title(v: Dict) -> str:
    return str(v.get("title", "Untitled"))

_SAMPLE = [
    {"title": "Epic Mountain Trail", "url": "https://example.com/a", "views": 120_000, "category": "outdoors"},
    {"title": "30s Pasta Trick", "url": "https://example.com/b", "views": 980_000, "category": "cooking"},
    {"title": "Phone Photography Tips", "url": "https://example.com/c", "views": 560_300, "category": "tech"},
]

def load_sample_videos() -> List[Dict]:
    return list(_SAMPLE)

def filter_videos_by_keywords(videos: Iterable[Dict], keywords: List[str]) -> List[Dict]:
    kws = [k.lower() for k in keywords]
    return [v for v in videos if any(k in _safe_title(v).lower() for k in kws)]

def filter_videos_by_category(videos: Iterable[Dict], categories: List[str]) -> List[Dict]:
    if not categories:
        return list(videos)
    cats = {c.lower() for c in categories}
    return [v for v in videos if str(v.get("category", "")).lower() in cats]

def get_top_videos(videos: Iterable[Dict], top_n: int = 10) -> List[Dict]:
    return sorted(list(videos), key=lambda v: int(v.get("views", 0)), reverse=True)[: max(1, top_n)]

def apply_improvements(videos: Iterable[Dict]) -> List[Dict]:
    out = []
    for v in videos:
        nv = dict(v)
        nv["improved"] = True
        out.append(nv)
    return out
'@
Write-TextFileUtf8 -Path (Join-Path $BASE 'video_helpers.py') -Content $video_helpers_py

# wizard.py
$wizard_py = @'
"""
wizard.py - Setup wizard for TrendClip
"""
from typing import List
from video_helpers import (
    load_sample_videos,
    filter_videos_by_keywords,
    filter_videos_by_category,
    get_top_videos,
    apply_improvements,
)

def prompt_for_keywords() -> List[str]:
    raw = input("Enter keywords or tags (comma-separated) that describe the videos you want: ")
    return [kw.strip() for kw in raw.split(",") if kw.strip()]

def prompt_for_categories() -> List[str]:
    raw = input("Enter categories to include (comma-separated), or press Enter to include all categories: ")
    return [cat.strip() for cat in raw.split(",") if cat.strip()]

def prompt_for_max_results() -> int:
    while True:
        try:
            value_str = input("Enter the maximum number of videos to retrieve (default 10): ") or "10"
            value = int(value_str)
            if value > 0:
                return value
            print("Please enter a positive integer.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def main() -> None:
    print("Welcome to the TrendClip setup wizard!")
    videos = load_sample_videos()
    keywords = prompt_for_keywords()
    categories = prompt_for_categories()
    max_results = prompt_for_max_results()
    filtered_videos = videos
    if keywords:
        filtered_videos = filter_videos_by_keywords(filtered_videos, keywords)
    if categories:
        filtered_videos = filter_videos_by_category(filtered_videos, categories)
    if not filtered_videos:
        print("No videos matched your criteria.")
        return
    top_videos = get_top_videos(filtered_videos, top_n=max_results)
    improved_videos = apply_improvements(top_videos)
    print("\nHere are your videos after applying improvements:")
    for idx, vid in enumerate(improved_videos, start=1):
        title = vid.get("title", "Untitled")
        url = vid.get("url", "")
        improved_flag = " (improved)" if vid.get("improved") else ""
        print(f"{idx}. {title}{improved_flag} - {url}")
    print("Setup wizard complete.")

if __name__ == "__main__":
    main()
'@
Write-TextFileUtf8 -Path (Join-Path $BASE 'wizard.py') -Content $wizard_py

# youtube_uploader.py
$youtube_uploader_py = @'
"""YouTube uploader for TrendClipOne."""
from __future__ import annotations
import os
import pathlib
from typing import Optional, Sequence
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

BASE = pathlib.Path(os.environ.get("TRENDCLIP_BASE", pathlib.Path.cwd()))
SECRETS_DIR = BASE / ".secrets"
TOKEN_PATH = SECRETS_DIR / "token.json"
CLIENT_SECRET_PATH = SECRETS_DIR / "client_secret.json"

def ensure_secrets_dir() -> None:
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

def authenticate(installed_app_port: int | None = None) -> Credentials:
    ensure_secrets_dir()
    creds: Optional[Credentials] = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_PATH.exists():
                raise FileNotFoundError(
                    f"Missing OAuth client secrets at {CLIENT_SECRET_PATH}. Download from Google Cloud Console (Desktop app)."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)
            creds = flow.run_local_server(port=installed_app_port or 0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds

def build_service(creds: Credentials):
    return build("youtube", "v3", credentials=creds)

def upload_video(
    file_path: str,
    *,
    title: str,
    description: str = "",
    tags: Optional[Sequence[str]] = None,
    privacy_status: str = "private",
    category_id: str = "24",
    add_shorts_hashtag: bool = True,
) -> dict:
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    creds = authenticate()
    yt = build_service(creds)
    if add_shorts_hashtag and "#shorts".lower() not in (title + " " + description).lower():
        title = f"{title} #Shorts"
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": list(tags or [])[:500],
            "categoryId": category_id,
        },
        "status": {"privacyStatus": privacy_status},
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = yt.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
    return response
'@
Write-TextFileUtf8 -Path (Join-Path $BASE 'youtube_uploader.py') -Content $youtube_uploader_py

# jobs.py — minimal queue + pipeline (download -> short -> upload)
$jobs_py = @'
"""
jobs.py - simple JSON-backed queue + processing pipeline.
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

BASE = Path(os.environ.get("TRENDCLIP_BASE") or Path.cwd())
DIST = BASE / "dist"
LOGS = BASE / "logs"
DATA = BASE / "data"
QUEUE_PATH = DATA / "queue.json"
HISTORY_PATH = DATA / "history.json"
for p in (DIST, LOGS, DATA): p.mkdir(parents=True, exist_ok=True)

def _utc() -> str: return datetime.utcnow().isoformat()

@dataclass
class Job:
    id: str
    url: str
    status: str = "queued"   # queued | processing | done | error
    created: str = ""
    updated: str = ""
    title: str = ""
    file: str = ""
    out_file: str = ""
    error: str = ""

def _load(path: Path) -> List[Dict[str, Any]]:
    if path.exists():
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception: return []
    return []

def _save(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

def list_queue() -> List[Dict[str, Any]]:
    return _load(QUEUE_PATH)

def list_history() -> List[Dict[str, Any]]:
    return _load(HISTORY_PATH)

def add_job(url: str) -> Dict[str, Any]:
    q = list_queue()
    now = _utc()
    j = Job(id=str(uuid.uuid4()), url=url, created=now, updated=now)
    q.append(asdict(j))
    _save(QUEUE_PATH, q)
    return asdict(j)

def pop_next() -> Optional[Dict[str, Any]]:
    q = list_queue()
    if not q: return None
    j = q.pop(0)
    _save(QUEUE_PATH, q)
    return j

def append_history(j: Dict[str, Any]) -> None:
    h = list_history()
    h.append(j)
    _save(HISTORY_PATH, h)

def _have_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg","-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except Exception:
        return False

def _download(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    # yt-dlp bestvideo+bestaudio merged; fallback to mp4
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-o", str(dest_dir / "%(title).80s.%(ext)s"),
        "-S", "res:1080,fps,codec:avc:vp9",
        "-f", "bv*+ba/b",
        "--merge-output-format", "mp4",
        url
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {r.stderr[-400:]}")
    # pick newest file
    files = sorted(dest_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise RuntimeError("Download produced no MP4.")
    return files[0]

def _make_short_60s(src: Path, out_dir: Path) -> Path:
    """
    Create a <=60s vertical short using MoviePy (center-crop 9:16 and subclip first 60s).
    Requires ffmpeg.
    """
    from moviepy.editor import VideoFileClip, vfx
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (src.stem + "_short.mp4")
    with VideoFileClip(str(src)) as clip:
        dur = min(60, clip.duration or 60)
        # compute center crop to 9:16
        w, h = clip.w, clip.h
        target_ratio = 9/16
        cur_ratio = w / h
        if cur_ratio > target_ratio:  # too wide => crop width
            new_w = int(h * target_ratio)
            x1 = (w - new_w)//2
            x2 = x1 + new_w
            c = clip.crop(x1=x1, y1=0, x2=x2, y2=h)
        else:  # too tall => crop height
            new_h = int(w / target_ratio)
            y1 = (h - new_h)//2
            y2 = y1 + new_h
            c = clip.crop(x1=0, y1=y1, x2=w, y2=y2)
        c = c.resize(height=1920)  # 1080x1920 if ratio exact
        c = c.subclip(0, dur)
        c = c.fx(vfx.fadein, 0.2).fx(vfx.fadeout, 0.2)
        c.write_videofile(str(out), codec="libx264", audio_codec="aac", threads=0, verbose=False, logger=None)
    return out

def process_next(upload: bool = False) -> Dict[str, Any]:
    if not _have_ffmpeg():
        raise RuntimeError("FFmpeg not found in PATH. Install ffmpeg and try again.")
    j = pop_next()
    if not j:
        return {"ok": False, "msg": "Queue empty."}
    j["status"] = "processing"; j["updated"] = _utc()
    scratch = Path(tempfile.mkdtemp(prefix="tco_"))
    try:
        raw = _download(j["url"], scratch)
        j["title"] = raw.stem
        out = _make_short_60s(raw, DIST)
        j["file"] = str(raw); j["out_file"] = str(out)
        if upload:
            from youtube_uploader import upload_video
            resp = upload_video(str(out), title=j["title"], description="", tags=["trendclip","shorts"], privacy_status="private")
            j["yt"] = resp
        j["status"] = "done"; j["updated"] = _utc()
    except Exception as e:
        j["status"] = "error"; j["error"] = str(e); j["updated"] = _utc()
    finally:
        append_history(j)
        try: shutil.rmtree(scratch, ignore_errors=True)
        except Exception: pass
    return j
'@
Write-TextFileUtf8 -Path (Join-Path $BASE 'jobs.py') -Content $jobs_py

# autopilot.py (calls jobs.process_next)
$autopilot_py = @'
"""Autopilot: process one queued job via jobs.process_next()."""
from __future__ import annotations
import os, pathlib, datetime as dt
from jobs import process_next

BASE = pathlib.Path(os.environ.get("TRENDCLIP_BASE", pathlib.Path.cwd()))
LOGS = BASE / "logs"; LOGS.mkdir(parents=True, exist_ok=True)
LOG = LOGS / "autopilot.log"

def _w(msg: str) -> None:
    t = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    LOG.write_text((LOG.read_text(encoding="utf-8") if LOG.exists() else "") + f"[{t}] {msg}\n", encoding="utf-8")

if __name__ == "__main__":
    try:
        res = process_next(upload=False)
        _w(f"Autopilot result: {res}")
    except Exception as e:
        _w(f"Autopilot error: {e}")
'@
Write-TextFileUtf8 -Path (Join-Path $BASE 'autopilot.py') -Content $autopilot_py

# Dash app (adds Jobs tab)
$dashboard_py = @'
"""TrendClip One — standalone Dash app (desktop)."""
from __future__ import annotations
import base64, os, pathlib, sys, textwrap, zipfile, json, subprocess
from datetime import datetime
import yaml
from dash import Dash, dcc, html, Input, Output, State, no_update
import plotly.express as px

_env_base = os.environ.get("TRENDCLIP_BASE")
BASE = pathlib.Path(_env_base) if _env_base else pathlib.Path(__file__).resolve().parent
ASSETS_DIR = BASE / "assets"
LOGS_DIR = BASE / "logs"
DIST_DIR = BASE / "dist"
SECRETS_DIR = BASE / ".secrets"
DATA_DIR = BASE / "data"
PY_EXE = os.environ.get("TRENDCLIP_VENV_PY", sys.executable)
for p in (ASSETS_DIR, LOGS_DIR, DIST_DIR, SECRETS_DIR, DATA_DIR): p.mkdir(parents=True, exist_ok=True)

cfg_path = BASE / "config.yaml"; CONFIG = {}
if cfg_path.exists():
    with open(cfg_path, "r", encoding="utf-8") as f: CONFIG = yaml.safe_load(f) or {}
port_env = CONFIG.get("app", {}).get("port_env", "TRENDCLIP_PORT")
bind_env = CONFIG.get("app", {}).get("bind_env", "TRENDCLIP_BIND")
port = int(os.environ.get(port_env, os.environ.get("TRENDCLIP_PORT", "8788")))
host = os.environ.get(bind_env, "127.0.0.1")

server = __import__("flask").Flask(__name__)
@server.get("/healthz")
def healthz():
    from datetime import datetime as _dt
    return {"ok": True, "time": _dt.utcnow().isoformat()}, 200

app = Dash(__name__, server=server, assets_folder=str(ASSETS_DIR), suppress_callback_exceptions=True, title="TrendClip One")

header = html.Div(className="container", children=[
    html.H1("TrendClip One"),
    html.P("Desktop build — jobs queue, wizard, uploader, self-test, packager, autopilot"),
    html.Div([html.Span("Base: "), html.Code(str(BASE)), html.Span(" — Host: "), html.Code(host), html.Span(":"), html.Code(str(port))]),
])

# ----- Tabs -----
overview_tab = html.Div(className="container", children=[
    html.Div(className="card", children=[
        html.H3("Overview"),
        html.P("OAuth secrets:"), html.Code(str(SECRETS_DIR / "client_secret.json")),
        dcc.Graph(id="demo-graph", figure=px.line(x=list(range(10)), y=[i*i for i in range(10)], title="Demo chart")),
    ])
])

selftest_tab = html.Div(className="container", children=[
    html.Div(className="card", children=[
        html.H3("Self-Test"), html.Button("Run Self-Test", id="btn-selftest", className="btn"),
        html.Div(id="selftest-output", style={"whiteSpace":"pre-wrap","marginTop":"10px"}), dcc.Graph(id="selftest-figure"),
    ])
])

wizard_tab = html.Div(className="container", children=[
    html.Div(className="card", children=[
        html.H3("Setup Wizard"), html.P("Launch the CLI wizard in a new console window."),
        html.Button("Open Wizard", id="btn-wizard", className="btn"), html.Div(id="wizard-status", style={"marginTop":"10px"}),
    ])
])

upload_tab = html.Div(className="container", children=[
    html.Div(className="card", children=[
        html.H3("Upload to YouTube (Shorts supported)"),
        dcc.Upload(id="upload-video", children=html.Div(["Drag & Drop or ", html.A("Select video")]), multiple=False),
        html.Br(), html.Label("Title"), dcc.Input(id="yt-title", type="text", value="My TrendClip", style={"width":"100%"}),
        html.Br(), html.Label("Description"), dcc.Textarea(id="yt-desc", value="", style={"width":"100%","height":"100px"}),
        html.Br(), html.Label("Tags (comma separated)"), dcc.Input(id="yt-tags", type="text", value="trendclip,shorts", style={"width":"100%"}),
        html.Br(), html.Label("Privacy"), dcc.Dropdown(id="yt-privacy", options=[{"label":"private","value":"private"},{"label":"unlisted","value":"unlisted"},{"label":"public","value":"public"}], value="private"),
        html.Br(), html.Button("Upload", id="btn-upload", className="btn"), html.Div(id="upload-status", style={"whiteSpace":"pre-wrap","marginTop":"10px"}),
    ])
])

pack_tab = html.Div(className="container", children=[
    html.Div(className="card", children=[
        html.H3("Packager"), html.P("Create a distributable ZIP (no venv/tokens)."), html.Button("Create ZIP", id="btn-pack", className="btn"),
        html.Div(id="pack-status", style={"whiteSpace":"pre-wrap","marginTop":"10px"}),
    ])
])

# Jobs tab
jobs_tab = html.Div(className="container", children=[
    html.Div(className="card", children=[
        html.H3("Jobs Queue"),
        html.Div(className="grid grid-2", children=[
            html.Div(children=[
                html.Label("New job URL (YouTube/TikTok/etc)"),
                dcc.Input(id="job-url", type="text", value="", placeholder="https://...", style={"width":"100%"}),
                html.Br(), html.Br(),
                html.Button("Add Job", id="btn-add-job", className="btn"),
                html.Button("Process Next", id="btn-proc-next", className="btn", style={"marginLeft":"8px"}),
                html.Button("Refresh", id="btn-refresh", className="btn", style={"marginLeft":"8px"}),
                html.Div(id="jobs-status", style={"whiteSpace":"pre-wrap","marginTop":"10px"}),
            ]),
            html.Div(children=[
                html.H4("Queue (pending)"),
                html.Pre(id="queue-json", style={"maxHeight":"280px","overflow":"auto"}),
                html.H4("History (last 20)"),
                html.Pre(id="hist-json", style={"maxHeight":"260px","overflow":"auto"}),
            ])
        ]),
    ])
])

autopilot_tab = html.Div(className="container", children=[
    html.Div(className="card", children=[
        html.H3("Autopilot"), html.P("Run one cycle using queued jobs."),
        html.Button("Run Do1", id="btn-do1", className="btn"), html.Div(id="do1-status", style={"whiteSpace":"pre-wrap","marginTop":"10px"}),
    ])
])

app.layout = html.Div([
    header,
    dcc.Tabs(id="tabs", value="tab-overview", children=[
        dcc.Tab(label="Overview", value="tab-overview"),
        dcc.Tab(label="Self-Test", value="tab-selftest"),
        dcc.Tab(label="Wizard", value="tab-wizard"),
        dcc.Tab(label="YouTube Upload", value="tab-upload"),
        dcc.Tab(label="Jobs", value="tab-jobs"),
        dcc.Tab(label="Packager", value="tab-pack"),
        dcc.Tab(label="Autopilot", value="tab-autopilot"),
    ]),
    html.Div(id="tab-content")
])

@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab):
    return {
        "tab-selftest": selftest_tab,
        "tab-wizard": wizard_tab,
        "tab-upload": upload_tab,
        "tab-pack": pack_tab,
        "tab-autopilot": autopilot_tab,
        "tab-jobs": jobs_tab,
    }.get(tab, overview_tab)

# ----- Self-test -----
@app.callback(Output("selftest-output", "children"), Output("selftest-figure", "figure"), Input("btn-selftest", "n_clicks"), prevent_initial_call=True)
def run_selftest(n):
    try:
        css_ok = (ASSETS_DIR / "style.css").exists()
        (LOGS_DIR / "selftest.txt").write_text(f"Self-test at {datetime.now().isoformat()}\n", encoding="utf-8")
        # ffmpeg check
        have_ffmpeg = subprocess.run(["ffmpeg","-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        fig = px.scatter(x=list(range(30)), y=[i * 0.5 for i in range(30)], title="Self-test scatter")
        msg = textwrap.dedent(f"""
            ✅ Self-test
            - Assets/style.css present: {css_ok}
            - FFmpeg available: {have_ffmpeg}
            - Log written: {LOGS_DIR / 'selftest.txt'}
            - Python: {sys.version.split()[0]} at {PY_EXE}
            - Base: {BASE}
        """).strip()
        return msg, fig
    except Exception as e:
        fig = px.scatter(x=[0], y=[0], title="Self-test error")
        return f"❌ Self-test failed: {e}", fig

# ----- Wizard launcher -----
@app.callback(Output("wizard-status", "children"), Input("btn-wizard", "n_clicks"), prevent_initial_call=True)
def open_wizard(n):
    try:
        if os.name == "nt":
            script = BASE / "wizard.py"
            os.system(f'start "" "{PY_EXE}" "{script}"')
        else:
            import subprocess
            subprocess.Popen([PY_EXE, str(BASE / "wizard.py")])
        return "Wizard opened in new console."
    except Exception as e:
        return f"Failed to open wizard: {e}"

# ----- Upload handling -----
import pathlib as _pl
def _save_uploaded(contents: str, filename: str) -> _pl.Path:
    header, data = contents.split(",", 1)
    import base64 as _b64
    binary = _b64.b64decode(data)
    out_dir = DIST_DIR / "uploads"; out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    with open(out_path, "wb") as f: f.write(binary)
    return out_path

@app.callback(Output("upload-status", "children"), Input("btn-upload", "n_clicks"),
              State("upload-video", "contents"), State("upload-video", "filename"),
              State("yt-title", "value"), State("yt-desc", "value"), State("yt-tags", "value"),
              State("yt-privacy", "value"), prevent_initial_call=True)
def handle_upload(n, contents, filename, title, desc, tags_csv, privacy):
    try:
        if not contents or not filename: return "Please select a video file first."
        saved = _save_uploaded(contents, filename)
        tags = [t.strip() for t in (tags_csv or "").split(",") if t.strip()]
        from youtube_uploader import upload_video
        resp = upload_video(str(saved), title=title or _pl.Path(filename).stem, description=desc or "", tags=tags, privacy_status=privacy or "private")
        vid = resp.get("id") or (resp.get("snippet", {}) or {}).get("resourceId", {}).get("videoId")
        return f"✅ Uploaded. Video ID: {vid or '<unknown>'}\nFile: {saved}"
    except Exception as e:
        return f"❌ Upload failed: {e}"

# ----- Packager -----
@app.callback(Output("pack-status", "children"), Input("btn-pack", "n_clicks"), prevent_initial_call=True)
def create_zip(n):
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S"); zip_path = DIST_DIR / f"TrendClipOne_{ts}.zip"
        include = ["TrendClipDashboard_Standalone.py","wizard.py","video_helpers.py","youtube_uploader.py","autopilot.py","jobs.py","requirements.txt","config.yaml","assets/","data/"]
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for item in include:
                p = BASE / item
                if p.is_dir():
                    for root, _, files in os.walk(p):
                        for f in files:
                            fp = _pl.Path(root) / f; z.write(fp, fp.relative_to(BASE))
                elif p.exists(): z.write(p, p.relative_to(BASE))
        try:
            import shutil, os as _os
            desktop = _os.path.join(_os.path.expanduser('~'),'Desktop'); shutil.copy2(zip_path, desktop)
        except Exception: pass
        return f"Created ZIP at: {zip_path}"
    except Exception as e:
        return f"Failed to pack: {e}"

# ----- Jobs tab callbacks -----
def _read_json(path: _pl.Path):
    if path.exists():
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception: return []
    return []

@app.callback(
    Output("jobs-status", "children"),
    Output("queue-json", "children"),
    Output("hist-json", "children"),
    Input("btn-add-job","n_clicks"),
    Input("btn-proc-next","n_clicks"),
    Input("btn-refresh","n_clicks"),
    State("job-url","value"),
    prevent_initial_call=True
)
def jobs_actions(n_add, n_proc, n_ref, url):
    ctx = dash_ctx = None
    try:
        from dash import ctx as dash_ctx
    except Exception:
        pass
    which = (dash_ctx.triggered_id if dash_ctx else None)

    status = ""
    try:
        if which == "btn-add-job":
            url = (url or "").strip()
            if not url: return "Enter a URL first.", no_update, no_update
            from jobs import add_job
            j = add_job(url)
            status = f"✅ Added job {j['id']}"
        elif which == "btn-proc-next":
            from jobs import process_next
            res = process_next(upload=False)
            status = f"Processed: {json.dumps(res, indent=2)[:800]}"
        else:
            status = "Refreshed."
    except Exception as e:
        status = f"❌ {e}"

    queue = _read_json(BASE / "data" / "queue.json")
    hist = _read_json(BASE / "data" / "history.json")[-20:]
    return status, json.dumps(queue, indent=2), json.dumps(hist, indent=2)

# ----- Autopilot -----
@app.callback(Output("do1-status", "children"), Input("btn-do1", "n_clicks"), prevent_initial_call=True)
def do1(n):
    try:
        import subprocess
        p = subprocess.run([PY_EXE, str(BASE / 'autopilot.py')], capture_output=True, text=True, cwd=str(BASE))
        log = (LOGS_DIR/ 'autopilot.log')
        msg = f"Return: {p.returncode}\n" + (log.read_text(encoding='utf-8') if log.exists() else '')[-800:]
        return msg
    except Exception as e:
        return f"Do1 failed: {e}"

if __name__ == "__main__":
    server.run(host=host, port=port, debug=False, use_reloader=False)
'@
Write-TextFileUtf8 -Path (Join-Path $BASE 'TrendClipDashboard_Standalone.py') -Content $dashboard_py

# Desktop wrapper (pywebview)
$desktop_py = @'
"""TrendClip Desktop wrapper — launches the Dash server in-process and shows a native window."""
from __future__ import annotations
import os, time, threading, runpy, socket
from pathlib import Path

_env_base = os.environ.get("TRENDCLIP_BASE")
BASE = Path(_env_base) if _env_base else Path(__file__).resolve().parent

def _get_free_port(start: int = 8700, end: int = 8999) -> int:
    for port in range(start, end+1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port)); return port
            except OSError:
                continue
    raise RuntimeError("No free TCP port")

port = int(os.environ.get("TRENDCLIP_PORT") or _get_free_port())
os.environ["TRENDCLIP_PORT"] = str(port)
os.environ.setdefault("TRENDCLIP_BIND", "127.0.0.1")
os.environ.setdefault("TRENDCLIP_BASE", str(BASE))

DASH_ENTRY = str(BASE / "TrendClipDashboard_Standalone.py")

def _run_dash():
    runpy.run_path(DASH_ENTRY, run_name="__main__")

def _wait_ready(url: str, timeout: float = 45.0) -> None:
    import urllib.request, time
    start = time.time(); last_err = None
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url) as r:
                if r.status == 200: return
        except Exception as e:
            last_err = e; time.sleep(0.3)
    raise RuntimeError(f"Server not ready at {url}: {last_err}")

thr = threading.Thread(target=_run_dash, daemon=True); thr.start()
health = f"http://{os.environ['TRENDCLIP_BIND']}:{port}/healthz"
_wait_ready(health, timeout=45)

import webview
url = f"http://{os.environ['TRENDCLIP_BIND']}:{port}/"
webview.create_window("TrendClip One", url, width=1200, height=800, easy_drag=False)
webview.start()
'@
Write-TextFileUtf8 -Path (Join-Path $BASE 'TrendClipDesktop.py') -Content $desktop_py

# venv / Python
$VENV_PY = $null
if ($UseSystemPython) {
  Write-Log 'Using system Python (no venv).'
  if (Get-Command py -ErrorAction SilentlyContinue) { $VENV_PY = (& py -3 -c "import sys; print(sys.executable)").Trim() }
  elseif (Get-Command python -ErrorAction SilentlyContinue) { $VENV_PY = (Get-Command python).Source }
  else { throw 'Python not found. Install Python 3.x and re-run.' }
} else {
  $pythonCmd = if (Get-Command py -ErrorAction SilentlyContinue) { 'py -3' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { throw 'Python not found. Install Python 3.x and re-run.' }
  if ($Reinstall -and (Test-Path -LiteralPath $VENV)) { Write-Log 'Removing existing venv...'; Remove-Item -Recurse -Force $VENV }
  if (-not (Test-Path -LiteralPath $VENV)) { iex "$pythonCmd -m venv `"$VENV`"" }
  $VENV_PY = Join-Path $VENV 'Scripts\python.exe'
}
$env:TRENDCLIP_VENV_PY = $VENV_PY
Write-Log "Python: $VENV_PY"

# pip & deps
& $VENV_PY -m pip install --upgrade pip
if ($RebuildDash) { & $VENV_PY -m pip install --upgrade --force-reinstall dash plotly pywebview yt-dlp }
& $VENV_PY -m pip install -r (Join-Path $BASE 'requirements.txt')

# Pack only?
if ($Pack) {
  Write-Log 'Creating distributable ZIP (headless)'
  $packPy = @'
import os, pathlib, zipfile, datetime, shutil
BASE = pathlib.Path(os.environ.get("TRENDCLIP_BASE") or pathlib.Path.cwd())
DIST = BASE / "dist"; DIST.mkdir(parents=True, exist_ok=True)
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
zip_path = DIST / f"TrendClipDesktop_{ts}.zip"
include = ["TrendClipDesktop.py","TrendClipDashboard_Standalone.py","wizard.py","video_helpers.py","youtube_uploader.py","autopilot.py","jobs.py","requirements.txt","config.yaml","assets","data"]
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for item in include:
        p = BASE / item
        if p.is_dir():
            for root, _, files in os.walk(p):
                for f in files:
                    fp = pathlib.Path(root) / f
                    z.write(fp, fp.relative_to(BASE))
        elif p.exists():
            z.write(p, p.relative_to(BASE))
try:
    desktop = pathlib.Path.home() / "Desktop"
    shutil.copy2(zip_path, desktop)
except Exception:
    pass
print(zip_path)
'@
  $tmp = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), 'trendclip_pack.py')
  [System.IO.File]::WriteAllText($tmp, $packPy, [System.Text.UTF8Encoding]::new($false))
  & $VENV_PY $tmp
  Remove-Item $tmp -Force -ErrorAction SilentlyContinue
  Write-Log 'ZIP created.'
  return
}

# Launch desktop app
Write-Log "Launching TrendClip Desktop (no external browser) on http://$($env:TRENDCLIP_BIND):$($env:TRENDCLIP_PORT)/"
if ($Detached) {
  Start-Process -FilePath $VENV_PY -ArgumentList (Join-Path $BASE 'TrendClipDesktop.py') -WorkingDirectory $BASE | Out-Null
  Write-Log "Started in background."
} else {
  & $VENV_PY (Join-Path $BASE 'TrendClipDesktop.py')
}

# Optional wizard
if ($RunWizard) {
  $launchWizard = @'
param([string]$Base)
$py = Join-Path $Base ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "py -3" }
Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", "$py `"$Base\wizard.py`"") -WorkingDirectory $Base
'@
  Write-TextFileUtf8 -Path (Join-Path $SCRIPTS 'launch_wizard.ps1') -Content $launchWizard
  Start-Process powershell -ArgumentList @('-NoExit','-ExecutionPolicy','Bypass','-File', (Join-Path $SCRIPTS 'launch_wizard.ps1'), '-Base', $BASE)
}
