#!/usr/bin/env python3
"""
TrendClip Desktop - API Wizard
Handles YouTube OAuth setup and API key configuration
"""

import os
import sys
import json
import webbrowser
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Google API libraries not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", 
                          "google-api-python-client", "google-auth", 
                          "google-auth-oauthlib", "google-auth-httplib2"])
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

class APIWizard:
    """Handles YouTube API setup and OAuth authentication"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.secrets_dir = self.base_path / ".secrets"
        self.secrets_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # OAuth scopes
        self.SCOPES = [
            'https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/youtube.readonly'
        ]
        
        # File paths
        self.client_secret_file = self.secrets_dir / "client_secret.json"
        self.token_file = self.secrets_dir / "token.json"
        self.config_file = self.base_path / "config.yaml"
        
    def check_environment_variables(self) -> Dict[str, str]:
        """Check for API keys in environment variables"""
        env_keys = {}
        
        # Check for YouTube API key
        youtube_key = os.environ.get('YOUTUBE_API_KEY')
        if youtube_key:
            env_keys['YOUTUBE_API_KEY'] = youtube_key
            self.logger.info("Found YOUTUBE_API_KEY in environment")
            
        # Check for OpenAI API key
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            env_keys['OPENAI_API_KEY'] = openai_key
            self.logger.info("Found OPENAI_API_KEY in environment")
            
        # Check for Tavily API key
        tavily_key = os.environ.get('TAVILY_API_KEY')
        if tavily_key:
            env_keys['TAVILY_API_KEY'] = tavily_key
            self.logger.info("Found TAVILY_API_KEY in environment")
            
        return env_keys
    
    def create_client_secret_template(self) -> str:
        """Create a template client_secret.json file"""
        template = {
            "installed": {
                "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
                "project_id": "your-project-id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "YOUR_CLIENT_SECRET",
                "redirect_uris": ["http://localhost"]
            }
        }
        return json.dumps(template, indent=2)
    
    def setup_youtube_oauth(self) -> bool:
        """Set up YouTube OAuth authentication"""
        try:
            self.logger.info("Setting up YouTube OAuth...")
            
            # Check if client_secret.json exists
            if not self.client_secret_file.exists():
                self.logger.error("client_secret.json not found")
                print("\n❌ YouTube OAuth setup failed!")
                print("You need to create a client_secret.json file.")
                print("\nSteps to get your YouTube API credentials:")
                print("1. Go to https://console.developers.google.com/")
                print("2. Create a new project or select existing")
                print("3. Enable YouTube Data API v3")
                print("4. Create OAuth 2.0 credentials")
                print("5. Download the JSON file as 'client_secret.json'")
                print("6. Place it in the .secrets folder")
                
                # Create template file
                template_content = self.create_client_secret_template()
                with open(self.client_secret_file, 'w') as f:
                    f.write(template_content)
                print(f"\n📝 Template created at: {self.client_secret_file}")
                print("Please edit this file with your actual credentials.")
                return False
            
            # Load client secrets
            with open(self.client_secret_file, 'r') as f:
                client_secrets = json.load(f)
            
            # Create flow
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secret_file), self.SCOPES)
            
            # Check if we have valid credentials
            creds = None
            if self.token_file.exists():
                creds = Credentials.from_authorized_user_file(
                    str(self.token_file), self.SCOPES)
            
            # If no valid credentials, let user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    print("\n🔐 YouTube OAuth Authentication Required")
                    print("A browser window will open for you to sign in to Google.")
                    print("Please authorize TrendClip to access your YouTube account.")
                    
                    # Run the OAuth flow
                    creds = flow.run_local_server(port=0)
                
                # Save credentials
                with open(self.token_file, 'w') as f:
                    f.write(creds.to_json())
                self.logger.info("OAuth credentials saved")
            
            # Test the credentials
            if self.test_youtube_credentials(creds):
                print("✅ YouTube OAuth setup successful!")
                return True
            else:
                print("❌ YouTube API test failed")
                return False
                
        except Exception as e:
            self.logger.error(f"YouTube OAuth setup failed: {e}")
            print(f"❌ YouTube OAuth setup failed: {e}")
            return False
    
    def test_youtube_credentials(self, creds: Credentials) -> bool:
        """Test YouTube API credentials"""
        try:
            youtube = build('youtube', 'v3', credentials=creds)
            
            # Test with a simple API call
            request = youtube.channels().list(
                part="snippet",
                mine=True
            )
            response = request.execute()
            
            if 'items' in response:
                channel = response['items'][0]
                channel_name = channel['snippet']['title']
                self.logger.info(f"YouTube API test successful. Channel: {channel_name}")
                print(f"✅ Connected to YouTube channel: {channel_name}")
                return True
            else:
                self.logger.error("YouTube API test failed - no channels found")
                return False
                
        except HttpError as e:
            self.logger.error(f"YouTube API test failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"YouTube API test failed: {e}")
            return False
    
    def setup_api_keys(self) -> Dict[str, str]:
        """Set up API keys via user input"""
        api_keys = {}
        
        print("\n🔑 API Key Setup")
        print("Enter your API keys (press Enter to skip):")
        
        # YouTube API Key
        youtube_key = input("\nYouTube API Key (optional, OAuth preferred): ").strip()
        if youtube_key:
            api_keys['YOUTUBE_API_KEY'] = youtube_key
            print("✅ YouTube API key saved")
        
        # OpenAI API Key
        openai_key = input("OpenAI API Key: ").strip()
        if openai_key:
            api_keys['OPENAI_API_KEY'] = openai_key
            print("✅ OpenAI API key saved")
        
        # Tavily API Key
        tavily_key = input("Tavily API Key: ").strip()
        if tavily_key:
            api_keys['TAVILY_API_KEY'] = tavily_key
            print("✅ Tavily API key saved")
        
        return api_keys
    
    def save_api_keys_to_env_file(self, api_keys: Dict[str, str]) -> bool:
        """Save API keys to .env file"""
        try:
            env_file = self.base_path / ".env"
            env_content = []
            
            for key, value in api_keys.items():
                env_content.append(f"{key}={value}")
            
            with open(env_file, 'w') as f:
                f.write('\n'.join(env_content))
            
            self.logger.info(f"API keys saved to {env_file}")
            print(f"✅ API keys saved to {env_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save API keys: {e}")
            print(f"❌ Failed to save API keys: {e}")
            return False
    
    def update_config(self, settings: Dict) -> bool:
        """Update configuration file"""
        try:
            import yaml
            
            # Load existing config
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = yaml.safe_load(f) or {}
            
            # Update with new settings
            config.update(settings)
            
            # Save updated config
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            self.logger.info("Configuration updated")
            print("✅ Configuration updated")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update config: {e}")
            print(f"❌ Failed to update config: {e}")
            return False
    
    def run_wizard(self) -> bool:
        """Run the complete API setup wizard"""
        print("\n" + "="*60)
        print("🎯 TrendClip Desktop - API Setup Wizard")
        print("="*60)
        
        success = True
        
        # Check environment variables first
        env_keys = self.check_environment_variables()
        if env_keys:
            print("\n✅ Found API keys in environment variables:")
            for key in env_keys.keys():
                print(f"   - {key}")
        
        # YouTube OAuth setup
        print("\n📺 YouTube Integration Setup")
        youtube_oauth = self.setup_youtube_oauth()
        
        # API keys setup
        print("\n🔑 Additional API Keys Setup")
        api_keys = self.setup_api_keys()
        
        # Save API keys
        if api_keys:
            self.save_api_keys_to_env_file(api_keys)
        
        # Configuration setup
        print("\n⚙️ Configuration Setup")
        config_settings = {}
        
        # Region
        region = input("Default region (e.g., GB, US): ").strip() or "GB"
        config_settings['region'] = region
        
        # CPM
        try:
            cpm = float(input("Default CPM in GBP (e.g., 3.5): ").strip() or "3.5")
            config_settings['cpm_gbp'] = cpm
        except ValueError:
            config_settings['cpm_gbp'] = 3.5
        
        # Clip duration
        try:
            duration = int(input("Default clip duration in seconds (e.g., 60): ").strip() or "60")
            config_settings['clip_duration'] = duration
        except ValueError:
            config_settings['clip_duration'] = 60
        
        # Update config
        self.update_config(config_settings)
        
        # Summary
        print("\n" + "="*60)
        print("📋 Setup Summary")
        print("="*60)
        print(f"YouTube OAuth: {'✅ Ready' if youtube_oauth else '❌ Not configured'}")
        print(f"API Keys: {'✅ Configured' if api_keys else '❌ None set'}")
        print(f"Environment Keys: {'✅ Found' if env_keys else '❌ None found'}")
        print(f"Configuration: ✅ Updated")
        
        if youtube_oauth or api_keys or env_keys:
            print("\n🎉 Setup completed successfully!")
            print("You can now use TrendClip Desktop with API integration.")
            return True
        else:
            print("\n⚠️ Setup completed with warnings.")
            print("Some features may not work without API keys.")
            return False

def main():
    """Main entry point"""
    # Get base path
    base_path = os.environ.get('TRENDCLIP_BASE') or os.path.expanduser('~/TrendClipOne')
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run wizard
    wizard = APIWizard(base_path)
    success = wizard.run_wizard()
    
    if success:
        print("\n🚀 Ready to use TrendClip Desktop!")
        print("Run the main installer to start the application.")
    else:
        print("\n⚠️ Setup completed with issues.")
        print("Please check the configuration and try again.")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
