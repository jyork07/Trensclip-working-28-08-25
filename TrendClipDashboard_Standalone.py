#!/usr/bin/env python3
"""
TrendClip Desktop - Standalone Dashboard
Comprehensive web interface with API wizard integration
"""

import os
import sys
import json
import yaml
import logging
import pathlib
import base64
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots

import dash
from dash import dcc, html, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

# Import our modules
try:
    from api_wizard import APIWizard
    from video_processor import create_video_processor
    from self_heal import create_self_heal_toolchain
    from packager import create_packager
except ImportError:
    print("Some modules not available - running in basic mode")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrendClipDashboard:
    """Main dashboard application"""
    
    def __init__(self):
        self.base_path = Path(os.environ.get('TRENDCLIP_BASE', os.path.expanduser('~/TrendClipOne')))
        self.config_file = self.base_path / "config.yaml"
        self.logs_dir = self.base_path / "logs"
        self.clips_dir = self.base_path / "clips"
        self.stats_file = self.base_path / "stats" / "clipstats.csv"
        self.secrets_dir = self.base_path / ".secrets"
        self.dist_dir = self.base_path / "dist"
        
        # Ensure directories exist
        for dir_path in [self.logs_dir, self.clips_dir, self.secrets_dir, self.dist_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize components
        self.api_wizard = None
        self.video_processor = None
        self.self_heal = None
        self.packager = None
        
        try:
            self.api_wizard = APIWizard(str(self.base_path))
            self.video_processor = create_video_processor(self.config)
            self.self_heal = create_self_heal_toolchain(str(self.base_path))
            self.packager = create_packager(str(self.base_path))
        except Exception as e:
            logger.warning(f"Some components not available: {e}")
        
        # Initialize Dash app
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.DARKLY],
            suppress_callback_exceptions=True
        )
        
        self.setup_layout()
        self.setup_callbacks()
    
    def load_config(self) -> dict:
        """Load configuration from YAML file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
        
        # Default configuration
        return {
            'version': '1.9.0-desktop',
            'currency': 'GBP',
            'region': 'GB',
            'cpm_gbp': 3.5,
            'clip_duration': 60,
            'app': {
                'port_env': 'TRENDCLIP_PORT',
                'bind_env': 'TRENDCLIP_BIND',
                'open_browser': False
            },
            'youtube': {
                'scopes': ['https://www.googleapis.com/auth/youtube.upload'],
                'default_privacy': 'private',
                'add_shorts_hashtag': True
            }
        }
    
    def setup_layout(self):
        """Setup the dashboard layout"""
        self.app.layout = dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("🎯 TrendClip Desktop", className="text-center mb-4"),
                    html.P("Desktop build — autopilot, uploader, self-test, packager, and API setup", className="text-center"),
                    html.Div([
                        html.Span("Base: "), 
                        html.Code(str(self.base_path))
                    ], className="text-center"),
                    html.Hr()
                ])
            ]),
            
            # Navigation Tabs
            dbc.Tabs([
                # Overview Tab
                dbc.Tab([
                    self.create_overview_tab()
                ], label="Overview", tab_id="overview"),
                
                # API Setup Tab
                dbc.Tab([
                    self.create_api_setup_tab()
                ], label="API & Auth", tab_id="api-setup"),
                
                # YouTube Upload Tab
                dbc.Tab([
                    self.create_upload_tab()
                ], label="YouTube Upload", tab_id="upload"),
                
                # Trending Tab
                dbc.Tab([
                    self.create_trending_tab()
                ], label="Trending", tab_id="trending"),
                
                # Analytics Tab
                dbc.Tab([
                    self.create_analytics_tab()
                ], label="Analytics", tab_id="analytics"),
                
                # Tools Tab
                dbc.Tab([
                    self.create_tools_tab()
                ], label="Tools", tab_id="tools"),
                
                # Autopilot Tab
                dbc.Tab([
                    self.create_autopilot_tab()
                ], label="Autopilot", tab_id="autopilot")
            ], id="tabs", active_tab="overview"),
            
            # Status Bar
            dbc.Row([
                dbc.Col([
                    html.Div(id="status-bar", className="mt-3 p-2 bg-secondary rounded")
                ])
            ])
        ], fluid=True)
    
    def create_overview_tab(self):
        """Create the overview tab content"""
        return dbc.Row([
            # System Status
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("System Status"),
                    dbc.CardBody([
                        html.Div(id="system-status"),
                        dbc.Button("Refresh Status", id="refresh-status", color="primary", className="mt-2")
                    ])
                ])
            ], width=6),
            
            # Quick Actions
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Quick Actions"),
                    dbc.CardBody([
                        dbc.Button("Run API Wizard", id="run-api-wizard", color="success", className="me-2 mb-2"),
                        dbc.Button("Self-Heal Tools", id="self-heal", color="warning", className="me-2 mb-2"),
                        dbc.Button("Create Package", id="create-package", color="info", className="me-2 mb-2"),
                        dbc.Button("Open Folders", id="open-folders", color="secondary", className="mb-2"),
                        html.Div(id="quick-actions-output", className="mt-3")
                    ])
                ])
            ], width=6),
            
            # Demo Chart
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Demo Chart"),
                    dbc.CardBody([
                        dcc.Graph(id="demo-graph", figure=px.line(
                            x=list(range(10)), 
                            y=[i*i for i in range(10)], 
                            title="Demo chart"
                        ))
                    ])
                ])
            ], width=12, className="mt-3")
        ])
    
    def create_api_setup_tab(self):
        """Create the API setup tab content with inline paste/upload functionality"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("API & Auth"),
                    dbc.CardBody([
                        html.P("Create a Google OAuth client (Desktop) and place client_secret.json into .secrets. You can paste JSON or upload the file here."),
                        html.Ul([
                            html.Li(html.A("Google Cloud Console", href="https://console.cloud.google.com/", className="link", target="_blank")),
                            html.Li(html.A("Create OAuth client (Desktop)", href="https://console.cloud.google.com/apis/credentials/oauthclient", className="link", target="_blank")),
                            html.Li(html.A("Enable YouTube Data API v3", href="https://console.cloud.google.com/apis/library/youtube.googleapis.com", className="link", target="_blank")),
                        ]),
                        html.Label("Paste client_secret.json contents"),
                        dcc.Textarea(id="client-json", value="", style={"width":"100%","height":"140px"}),
                        html.Div(style={"marginTop":"8px"}),
                        html.Label("Or select client_secret.json file"),
                        dcc.Upload(id="upload-client-json", children=html.Div(["Drag & Drop or ", html.A("Select file")]), multiple=False),
                        html.Div(style={"marginTop":"8px"}),
                        html.Label("Or paste a file path to client_secret.json"),
                        dcc.Input(id="client-path", type="text", value="", style={"width":"100%"}),
                        html.Div(style={"marginTop":"10px"}, children=[
                            dbc.Button("Save client_secret.json", id="btn-save-secret", color="success", className="me-2"),
                            dbc.Button("Clear token.json", id="btn-clear-token", color="warning", className="me-2"),
                            dbc.Button("Test YouTube Login", id="btn-test-auth", color="info", className="me-2"),
                            dbc.Button("Open .secrets", id="btn-open-secrets", color="secondary")
                        ]),
                        html.Div(id="api-status", style={"whiteSpace":"pre-wrap","marginTop":"10px"}),
                    ])
                ])
            ], width=12)
        ])
    
    def create_upload_tab(self):
        """Create the YouTube upload tab"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("YouTube Upload (Shorts)"),
                    dbc.CardBody([
                        dcc.Upload(id="upload-video", children=html.Div(["Drag & Drop or ", html.A("Select video")]), multiple=False),
                        html.Br(), 
                        html.Label("Title"), 
                        dcc.Input(id="yt-title", type="text", value="My TrendClip", style={"width":"100%"}),
                        html.Br(), 
                        html.Label("Description"), 
                        dcc.Textarea(id="yt-desc", value="", style={"width":"100%","height":"100px"}),
                        html.Br(), 
                        html.Label("Tags (comma separated)"), 
                        dcc.Input(id="yt-tags", type="text", value="trendclip,shorts", style={"width":"100%"}),
                        html.Br(), 
                        html.Label("Privacy"), 
                        dcc.Dropdown(id="yt-privacy", options=[
                            {"label":v,"value":v} for v in ("private","unlisted","public")
                        ], value="private"),
                        html.Br(), 
                        dbc.Button("Upload", id="btn-upload", color="primary"),
                        html.Div(id="upload-status", style={"whiteSpace":"pre-wrap","marginTop":"10px"}),
                    ])
                ])
            ], width=12)
        ])
    
    def create_trending_tab(self):
        """Create the trending tab content"""
        return dbc.Row([
            # Trending Controls
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Trending Controls"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Region"),
                                dbc.Select(
                                    id="trending-region",
                                    options=[
                                        {"label": "United Kingdom", "value": "GB"},
                                        {"label": "United States", "value": "US"},
                                        {"label": "Canada", "value": "CA"},
                                        {"label": "Australia", "value": "AU"}
                                    ],
                                    value=self.config.get('region', 'GB')
                                )
                            ], width=4),
                            dbc.Col([
                                dbc.Label("Limit"),
                                dbc.Input(
                                    id="trending-limit",
                                    type="number",
                                    value=50,
                                    min=10,
                                    max=200
                                )
                            ], width=4),
                            dbc.Col([
                                dbc.Button("Fetch Trends", id="fetch-trends", color="primary", className="mt-4")
                            ], width=4)
                        ]),
                        html.Div(id="trending-output", className="mt-3")
                    ])
                ])
            ], width=12),
            
            # Trending Results
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Trending Videos"),
                    dbc.CardBody([
                        html.Div(id="trending-results")
                    ])
                ])
            ], width=12, className="mt-3")
        ])
    
    def create_analytics_tab(self):
        """Create the analytics tab content"""
        return dbc.Row([
            # Analytics Overview
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Analytics Overview"),
                    dbc.CardBody([
                        html.Div(id="analytics-overview")
                    ])
                ])
            ], width=12),
            
            # Charts
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Performance Charts"),
                    dbc.CardBody([
                        dcc.Graph(id="views-chart"),
                        dcc.Graph(id="revenue-chart")
                    ])
                ])
            ], width=12, className="mt-3")
        ])
    
    def create_tools_tab(self):
        """Create the tools tab content"""
        return dbc.Row([
            # Self-Test
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Self-Test"),
                    dbc.CardBody([
                        dbc.Button("Run Self-Test", id="btn-selftest", color="primary", className="me-2"),
                        dbc.Button("Open Logs Folder", id="btn-open-logs", color="secondary"),
                        html.Div(id="selftest-output", style={"whiteSpace":"pre-wrap","marginTop":"10px"}),
                        dcc.Graph(id="selftest-figure"),
                    ])
                ])
            ], width=6),
            
            # Packager
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Packager"),
                    dbc.CardBody([
                        html.P("Create a distributable ZIP (no venv/tokens)."),
                        dbc.Button("Create ZIP", id="btn-pack", color="info"),
                        html.Div(id="pack-status", style={"whiteSpace":"pre-wrap","marginTop":"10px"}),
                    ])
                ])
            ], width=6),
            
            # System Tools
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("System Tools"),
                    dbc.CardBody([
                        dbc.Button("Check Tools", id="check-tools", color="info", className="me-2"),
                        dbc.Button("Install Missing", id="install-missing", color="warning", className="me-2"),
                        dbc.Button("Create Package", id="create-package-tools", color="secondary"),
                        html.Div(id="system-tools-output", className="mt-3")
                    ])
                ])
            ], width=12, className="mt-3")
        ])
    
    def create_autopilot_tab(self):
        """Create the autopilot tab content"""
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Autopilot"),
                    dbc.CardBody([
                        html.P("Edit urls.txt, then run one cycle. Outputs to /dist."),
                        dbc.Button("Open urls.txt", id="btn-open-urls", color="primary", className="me-2"),
                        dbc.Button("Open dist Folder", id="btn-open-dist", color="secondary", className="me-2"),
                        dbc.Button("Run Once", id="btn-do1", color="success"),
                        html.Div(id="do1-status", style={"whiteSpace":"pre-wrap","marginTop":"10px"}),
                    ])
                ])
            ], width=12)
        ])
    
    def setup_callbacks(self):
        """Setup Dash callbacks"""
        
        @self.app.callback(
            Output("system-status", "children"),
            Input("refresh-status", "n_clicks")
        )
        def update_system_status(n_clicks):
            if n_clicks is None:
                n_clicks = 0
            
            try:
                # Check system status
                status_items = []
                
                # Check Python
                python_version = sys.version.split()[0]
                status_items.append(f"✅ Python: {python_version}")
                
                # Check tools
                if self.self_heal:
                    ffmpeg_available, _ = self.self_heal.check_tool_availability('ffmpeg')
                    ytdlp_available, _ = self.self_heal.check_tool_availability('yt-dlp')
                    
                    status_items.append(f"{'✅' if ffmpeg_available else '❌'} FFmpeg")
                    status_items.append(f"{'✅' if ytdlp_available else '❌'} yt-dlp")
                
                # Check API keys
                env_keys = self.api_wizard.check_environment_variables() if self.api_wizard else {}
                if env_keys:
                    status_items.append(f"✅ API Keys: {len(env_keys)} found")
                else:
                    status_items.append("❌ API Keys: None found")
                
                # Check disk space
                disk_usage = self.base_path.stat().st_size
                disk_gb = disk_usage / (1024**3)
                status_items.append(f"💾 Disk Usage: {disk_gb:.1f} GB")
                
                return [html.P(item) for item in status_items]
                
            except Exception as e:
                return html.P(f"❌ Status check failed: {e}")
        
        # API Setup callbacks
        @self.app.callback(
            Output("api-status", "children"),
            Input("btn-open-secrets", "n_clicks"),
            prevent_initial_call=True
        )
        def open_secrets(n):
            try:
                if os.name == "nt":
                    os.startfile(str(self.secrets_dir))
                else:
                    import subprocess
                    subprocess.Popen(["open" if sys.platform=="darwin" else "xdg-open", str(self.secrets_dir)])
                return f"Opened: {self.secrets_dir}"
            except Exception as e:
                return f"Open failed: {e}"
        
        def _save_client_json_from_text(text: str) -> str:
            if not text.strip():
                return "Paste JSON or upload a file."
            try:
                obj = json.loads(text)
            except Exception as e:
                return f"Invalid JSON: {e}"
            out = self.secrets_dir / "client_secret.json"
            out.write_text(json.dumps(obj, indent=2), encoding="utf-8")
            return f"✅ Saved client_secret.json → {out}"

        def _save_client_json_from_upload(contents: str, filename: str) -> str:
            if not contents: 
                return "No file provided."
            try:
                header, data = contents.split(",", 1)
                raw = base64.b64decode(data)
                obj = json.loads(raw.decode("utf-8"))
            except Exception as e:
                return f"Upload parse failed: {e}"
            out = self.secrets_dir / "client_secret.json"
            out.write_text(json.dumps(obj, indent=2), encoding="utf-8")
            return f"✅ Saved client_secret.json from {filename} → {out}"

        @self.app.callback(
            Output("api-status", "children", allow_duplicate=True),
            Input("btn-save-secret", "n_clicks"),
            State("client-json", "value"),
            State("upload-client-json", "contents"),
            State("upload-client-json", "filename"),
            State("client-path", "value"),
            prevent_initial_call=True
        )
        def save_secret(n, pasted, up_contents, up_name, path_value):
            try:
                if up_contents:
                    return _save_client_json_from_upload(up_contents, up_name or "upload")
                if pasted and pasted.strip():
                    return _save_client_json_from_text(pasted)
                if path_value and str(path_value).strip():
                    p = pathlib.Path(path_value.strip('"'))
                    if not p.exists():
                        return f"Path not found: {p}"
                    try:
                        text = p.read_text(encoding="utf-8")
                    except Exception:
                        # try binary decode
                        text = p.read_bytes().decode("utf-8", errors="ignore")
                    return _save_client_json_from_text(text)
                return "Provide JSON (paste, upload, or path)."
            except Exception as e:
                return f"❌ Save failed: {e}"

        @self.app.callback(
            Output("api-status", "children", allow_duplicate=True), 
            Input("btn-clear-token", "n_clicks"), 
            prevent_initial_call=True
        )
        def clear_token(n):
            try:
                tok = self.secrets_dir / "token.json"
                if tok.exists(): 
                    tok.unlink()
                return "🔄 token.json cleared."
            except Exception as e:
                return f"Clear failed: {e}"

        @self.app.callback(
            Output("api-status", "children", allow_duplicate=True), 
            Input("btn-test-auth", "n_clicks"), 
            prevent_initial_call=True
        )
        def test_auth(n):
            try:
                from youtube_uploader import authenticate
                authenticate(installed_app_port=0)
                return "✅ Auth OK. Token saved in .secrets/token.json"
            except Exception as e:
                return f"❌ Auth failed: {e}"
        
        # Upload callbacks
        def _save_uploaded(contents: str, filename: str) -> Path:
            header, data = contents.split(",", 1)
            binary = base64.b64decode(data)
            out_dir = self.dist_dir / "uploads"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / filename
            with open(out_path, "wb") as f: 
                f.write(binary)
            return out_path

        @self.app.callback(
            Output("upload-status", "children"), 
            Input("btn-upload", "n_clicks"),
            State("upload-video", "contents"), 
            State("upload-video", "filename"),
            State("yt-title", "value"), 
            State("yt-desc", "value"), 
            State("yt-tags", "value"),
            State("yt-privacy", "value"), 
            prevent_initial_call=True
        )
        def handle_upload(n, contents, filename, title, desc, tags_csv, privacy):
            try:
                if not contents or not filename: 
                    return "Please select a video file first."
                saved = _save_uploaded(contents, filename)
                tags = [t.strip() for t in (tags_csv or "").split(",") if t.strip()]
                from youtube_uploader import upload_video
                resp = upload_video(
                    str(saved), 
                    title=title or pathlib.Path(filename).stem, 
                    description=desc or "", 
                    tags=tags, 
                    privacy_status=privacy or "private"
                )
                vid = resp.get("id") or (resp.get("snippet", {}) or {}).get("resourceId", {}).get("videoId")
                return f"✅ Uploaded. Video ID: {vid or '<unknown>'}\nFile: {saved}"
            except Exception as e:
                return f"❌ Upload failed: {e}"
        
        # Packager callback
        @self.app.callback(
            Output("pack-status", "children"), 
            Input("btn-pack", "n_clicks"), 
            prevent_initial_call=True
        )
        def create_zip(n):
            try:
                import zipfile
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_path = self.dist_dir / f"TrendClipOne_{ts}.zip"
                include = [
                    "TrendClipDashboard_Standalone.py","wizard.py","video_helpers.py",
                    "youtube_uploader.py","autopilot.py","jobs.py","requirements.txt",
                    "config.yaml","assets/","data/"
                ]
                with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
                    for item in include:
                        p = self.base_path / item
                        if p.is_dir():
                            for root, _, files in os.walk(p):
                                for f in files:
                                    fp = pathlib.Path(root) / f
                                    z.write(fp, fp.relative_to(self.base_path))
                        elif p.exists(): 
                            z.write(p, p.relative_to(self.base_path))
                try:
                    import shutil
                    desktop = pathlib.Path.home() / "Desktop"
                    shutil.copy2(zip_path, desktop)
                except Exception: 
                    pass
                return f"Created ZIP at: {zip_path}"
            except Exception as e:
                return f"Failed to pack: {e}"
        
        # Self-test callback
        @self.app.callback(
            Output("selftest-output", "children"), 
            Output("selftest-figure", "figure"), 
            Input("btn-selftest", "n_clicks"), 
            prevent_initial_call=True
        )
        def run_selftest(n):
            try:
                (self.logs_dir / "selftest.txt").write_text(
                    f"Self-test at {datetime.now().isoformat()}\n", 
                    encoding="utf-8"
                )
                fig = px.scatter(
                    x=list(range(30)), 
                    y=[i * 0.5 for i in range(30)], 
                    title="Self-test scatter"
                )
                return "✅ Self-test passed", fig
            except Exception as e:
                fig = px.scatter(x=[0], y=[0], title="Self-test error")
                return f"❌ Self-test failed: {e}", fig
        
        # Autopilot callbacks
        @self.app.callback(
            Output("do1-status", "children"), 
            Input("btn-do1", "n_clicks"), 
            prevent_initial_call=True
        )
        def do1(n):
            try:
                import subprocess
                py_exe = os.environ.get("TRENDCLIP_VENV_PY", sys.executable)
                p = subprocess.run(
                    [py_exe, str(self.base_path / "autopilot.py")], 
                    capture_output=True, 
                    text=True, 
                    cwd=str(self.base_path)
                )
                log = self.logs_dir / "autopilot.log"
                tail = (log.read_text(encoding="utf-8") if log.exists() else "")[-2000:]
                return f"Return: {p.returncode}\n--- autopilot.log (tail) ---\n{tail}"
            except Exception as e:
                return f"Do1 failed: {e}"

        @self.app.callback(
            Output("do1-status", "children", allow_duplicate=True), 
            Input("btn-open-urls", "n_clicks"), 
            prevent_initial_call=True
        )
        def open_urls(n):
            u = self.base_path / "urls.txt"
            if not u.exists(): 
                u.write_text("# Put one URL per line (YouTube/TikTok/etc.)\n", encoding="utf-8")
            try:
                if os.name == "nt":
                    os.startfile(str(u))
                else:
                    import subprocess
                    subprocess.Popen(["open" if sys.platform=="darwin" else "xdg-open", str(u)])
                return f"Opened: {u}"
            except Exception as e:
                return f"Open failed: {e}"

        @self.app.callback(
            Output("do1-status", "children", allow_duplicate=True), 
            Input("btn-open-dist", "n_clicks"), 
            prevent_initial_call=True
        )
        def open_dist(n):
            try:
                if os.name == "nt":
                    os.startfile(str(self.dist_dir))
                else:
                    import subprocess
                    subprocess.Popen(["open" if sys.platform=="darwin" else "xdg-open", str(self.dist_dir)])
                return f"Opened: {self.dist_dir}"
            except Exception as e:
                return f"Open failed: {e}"
        
        # Other existing callbacks...
        @self.app.callback(
            Output("quick-actions-output", "children"),
            Input("run-api-wizard", "n_clicks"),
            Input("self-heal", "n_clicks"),
            Input("create-package", "n_clicks"),
            Input("open-folders", "n_clicks")
        )
        def handle_quick_actions(wizard_clicks, heal_clicks, package_clicks, folders_clicks):
            ctx = callback_context
            if not ctx.triggered:
                return ""
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            try:
                if button_id == "run-api-wizard" and self.api_wizard:
                    success = self.api_wizard.run_wizard()
                    return f"{'✅' if success else '❌'} API Wizard {'completed' if success else 'failed'}"
                
                elif button_id == "self-heal" and self.self_heal:
                    results = self.self_heal.heal_all_tools()
                    success_count = sum(1 for success in results.values() if success)
                    return f"✅ Self-heal completed: {success_count}/{len(results)} tools ready"
                
                elif button_id == "create-package" and self.packager:
                    package_path = self.packager.create_package()
                    return f"✅ Package created: {Path(package_path).name}"
                
                elif button_id == "open-folders":
                    import subprocess
                    subprocess.Popen(['explorer', str(self.base_path)])
                    return "✅ Opened TrendClip folder"
                
                return ""
                
            except Exception as e:
                return f"❌ Action failed: {e}"
    
    def run(self, debug=False):
        """Run the dashboard"""
        port = int(os.environ.get('TRENDCLIP_PORT', 8700))
        host = os.environ.get('TRENDCLIP_BIND', '127.0.0.1')
        
        logger.info(f"Starting TrendClip Dashboard on http://{host}:{port}")
        
        self.app.run_server(
            debug=debug,
            host=host,
            port=port,
            use_reloader=False
        )

def main():
    """Main entry point"""
    dashboard = TrendClipDashboard()
    dashboard.run(debug=False)

if __name__ == "__main__":
    main()
