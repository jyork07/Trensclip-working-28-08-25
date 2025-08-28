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
                ], label="API Setup", tab_id="api-setup"),
                
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
                ], label="Tools", tab_id="tools")
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
            
            # Recent Activity
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Recent Activity"),
                    dbc.CardBody([
                        html.Div(id="recent-activity")
                    ])
                ])
            ], width=12, className="mt-3")
        ])
    
    def create_api_setup_tab(self):
        """Create the API setup tab content"""
        return dbc.Row([
            # API Status
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("API Configuration Status"),
                    dbc.CardBody([
                        html.Div(id="api-status"),
                        dbc.Button("Check API Status", id="check-api-status", color="primary", className="mt-2")
                    ])
                ])
            ], width=6),
            
            # API Setup
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("API Setup"),
                    dbc.CardBody([
                        dbc.Button("Setup YouTube OAuth", id="setup-youtube", color="success", className="me-2 mb-2"),
                        dbc.Button("Setup API Keys", id="setup-api-keys", color="info", className="mb-2"),
                        html.Div(id="api-setup-output", className="mt-3")
                    ])
                ])
            ], width=6),
            
            # Configuration
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Configuration"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Region"),
                                dbc.Select(
                                    id="region-select",
                                    options=[
                                        {"label": "United Kingdom", "value": "GB"},
                                        {"label": "United States", "value": "US"},
                                        {"label": "Canada", "value": "CA"},
                                        {"label": "Australia", "value": "AU"}
                                    ],
                                    value=self.config.get('region', 'GB')
                                )
                            ], width=6),
                            dbc.Col([
                                dbc.Label("CPM (GBP)"),
                                dbc.Input(
                                    id="cpm-input",
                                    type="number",
                                    step=0.1,
                                    value=self.config.get('cpm_gbp', 3.5)
                                )
                            ], width=6)
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Clip Duration (seconds)"),
                                dbc.Input(
                                    id="duration-input",
                                    type="number",
                                    value=self.config.get('clip_duration', 60)
                                )
                            ], width=6),
                            dbc.Col([
                                dbc.Button("Save Config", id="save-config", color="primary", className="mt-4")
                            ], width=6)
                        ]),
                        html.Div(id="config-save-output", className="mt-3")
                    ])
                ])
            ], width=12, className="mt-3")
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
            # Video Processing
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Video Processing"),
                    dbc.CardBody([
                        dbc.Button("Test Video Processing", id="test-video", color="primary", className="me-2"),
                        dbc.Button("Process Sample", id="process-sample", color="success", className="me-2"),
                        html.Div(id="video-processing-output", className="mt-3")
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
            ], width=6),
            
            # Logs
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("System Logs"),
                    dbc.CardBody([
                        html.Div(id="system-logs", style={"maxHeight": "300px", "overflow": "auto"})
                    ])
                ])
            ], width=12, className="mt-3")
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
        
        @self.app.callback(
            Output("api-status", "children"),
            Input("check-api-status", "n_clicks")
        )
        def check_api_status(n_clicks):
            if n_clicks is None:
                return "Click 'Check API Status' to verify configuration"
            
            try:
                if not self.api_wizard:
                    return "❌ API Wizard not available"
                
                # Check environment variables
                env_keys = self.api_wizard.check_environment_variables()
                
                # Check OAuth
                oauth_ready = self.api_wizard.client_secret_file.exists() and self.api_wizard.token_file.exists()
                
                status_items = []
                status_items.append(f"Environment Keys: {'✅' if env_keys else '❌'}")
                status_items.append(f"YouTube OAuth: {'✅' if oauth_ready else '❌'}")
                
                if env_keys:
                    status_items.append("Found keys:")
                    for key in env_keys.keys():
                        status_items.append(f"  - {key}")
                
                return [html.P(item) for item in status_items]
                
            except Exception as e:
                return html.P(f"❌ API status check failed: {e}")
        
        @self.app.callback(
            Output("api-setup-output", "children"),
            Input("setup-youtube", "n_clicks"),
            Input("setup-api-keys", "n_clicks")
        )
        def handle_api_setup(youtube_clicks, api_keys_clicks):
            ctx = callback_context
            if not ctx.triggered:
                return ""
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            try:
                if button_id == "setup-youtube" and self.api_wizard:
                    success = self.api_wizard.setup_youtube_oauth()
                    return f"{'✅' if success else '❌'} YouTube OAuth setup {'completed' if success else 'failed'}"
                
                elif button_id == "setup-api-keys" and self.api_wizard:
                    api_keys = self.api_wizard.setup_api_keys()
                    if api_keys:
                        self.api_wizard.save_api_keys_to_env_file(api_keys)
                        return f"✅ {len(api_keys)} API keys configured"
                    else:
                        return "⚠️ No API keys entered"
                
                return ""
                
            except Exception as e:
                return f"❌ Setup failed: {e}"
        
        @self.app.callback(
            Output("config-save-output", "children"),
            Input("save-config", "n_clicks"),
            State("region-select", "value"),
            State("cpm-input", "value"),
            State("duration-input", "value")
        )
        def save_configuration(n_clicks, region, cpm, duration):
            if n_clicks is None:
                return ""
            
            try:
                if not self.api_wizard:
                    return "❌ API Wizard not available"
                
                config_settings = {
                    'region': region,
                    'cpm_gbp': float(cpm),
                    'clip_duration': int(duration)
                }
                
                success = self.api_wizard.update_config(config_settings)
                if success:
                    self.config.update(config_settings)
                    return "✅ Configuration saved"
                else:
                    return "❌ Failed to save configuration"
                
            except Exception as e:
                return f"❌ Save failed: {e}"
        
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
