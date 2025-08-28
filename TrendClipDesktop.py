#!/usr/bin/env python3
"""
TrendClip Desktop - Native Window Launcher
Wraps the dashboard in a native window using pywebview
"""

import os
import sys
import threading
import time
import logging
from pathlib import Path

try:
    import webview
except ImportError:
    print("pywebview not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview"])
    import webview

# Import our dashboard
try:
    from TrendClipDashboard_Standalone import TrendClipDashboard
except ImportError:
    print("Dashboard module not found. Running in basic mode.")
    TrendClipDashboard = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrendClipDesktop:
    """Desktop application wrapper"""
    
    def __init__(self):
        self.base_path = Path(os.environ.get('TRENDCLIP_BASE', os.path.expanduser('~/TrendClipOne')))
        self.dashboard = None
        self.webview_window = None
        self.dashboard_thread = None
        
    def start_dashboard(self):
        """Start the dashboard in a separate thread"""
        try:
            if TrendClipDashboard:
                self.dashboard = TrendClipDashboard()
                self.dashboard.run(debug=False)
            else:
                # Fallback to basic dashboard
                self.run_basic_dashboard()
        except Exception as e:
            logger.error(f"Dashboard failed to start: {e}")
            self.run_basic_dashboard()
    
    def run_basic_dashboard(self):
        """Run a basic dashboard if the main one fails"""
        from flask import Flask, render_template_string
        
        app = Flask(__name__)
        
        @app.route('/')
        def index():
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>TrendClip Desktop</title>
                <style>
                    body { font-family: Arial, sans-serif; background: #0b0f17; color: #e8eef9; margin: 0; padding: 20px; }
                    .container { max-width: 800px; margin: 0 auto; }
                    .card { background: #121826; padding: 20px; border-radius: 10px; margin: 20px 0; }
                    .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
                    .btn:hover { background: #0056b3; }
                    .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
                    .success { background: #28a745; }
                    .warning { background: #ffc107; color: #000; }
                    .error { background: #dc3545; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎯 TrendClip Desktop</h1>
                    
                    <div class="card">
                        <h2>System Status</h2>
                        <div class="status success">✅ Dashboard is running</div>
                        <div class="status warning">⚠️ Running in basic mode</div>
                        <p>Some features may not be available. Please check the console for details.</p>
                    </div>
                    
                    <div class="card">
                        <h2>Quick Actions</h2>
                        <button class="btn" onclick="alert('API Wizard not available in basic mode')">Run API Wizard</button>
                        <button class="btn" onclick="alert('Self-heal not available in basic mode')">Self-Heal Tools</button>
                        <button class="btn" onclick="alert('Package creation not available in basic mode')">Create Package</button>
                    </div>
                    
                    <div class="card">
                        <h2>Next Steps</h2>
                        <p>To get full functionality:</p>
                        <ol>
                            <li>Check that all Python modules are installed</li>
                            <li>Run the API wizard to configure YouTube OAuth</li>
                            <li>Set up your API keys</li>
                            <li>Restart the application</li>
                        </ol>
                    </div>
                </div>
            </body>
            </html>
            ''')
        
        port = int(os.environ.get('TRENDCLIP_PORT', 8700))
        host = os.environ.get('TRENDCLIP_BIND', '127.0.0.1')
        
        app.run(host=host, port=port, debug=False, use_reloader=False)
    
    def create_window(self):
        """Create the native window"""
        try:
            port = int(os.environ.get('TRENDCLIP_PORT', 8700))
            host = os.environ.get('TRENDCLIP_BIND', '127.0.0.1')
            url = f"http://{host}:{port}"
            
            # Start dashboard in background thread
            self.dashboard_thread = threading.Thread(target=self.start_dashboard, daemon=True)
            self.dashboard_thread.start()
            
            # Wait for dashboard to start
            time.sleep(3)
            
            # Create window
            self.webview_window = webview.create_window(
                title="TrendClip Desktop",
                url=url,
                width=1200,
                height=800,
                resizable=True,
                text_select=True,
                confirm_close=False
            )
            
            logger.info(f"Starting TrendClip Desktop window at {url}")
            webview.start(debug=False)
            
        except Exception as e:
            logger.error(f"Failed to create window: {e}")
            print(f"❌ Failed to start TrendClip Desktop: {e}")
            print("Please check the console for error details.")
    
    def run(self):
        """Run the desktop application"""
        print("🚀 Starting TrendClip Desktop...")
        print(f"Base path: {self.base_path}")
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create window
        self.create_window()

def main():
    """Main entry point"""
    desktop = TrendClipDesktop()
    desktop.run()

if __name__ == "__main__":
    main()
