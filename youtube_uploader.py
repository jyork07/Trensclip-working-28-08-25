#!/usr/bin/env python3
"""
TrendClip Desktop - YouTube Uploader
Handles video uploads to YouTube with OAuth authentication
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
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
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class YouTubeUploader:
    """Handles YouTube video uploads with OAuth authentication"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.secrets_dir = self.base_path / ".secrets"
        self.secrets_dir.mkdir(exist_ok=True)
        
        # OAuth scopes
        self.SCOPES = [
            'https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/youtube.readonly'
        ]
        
        # File paths
        self.client_secret_file = self.secrets_dir / "client_secret.json"
        self.token_file = self.secrets_dir / "token.json"
        
        # YouTube API service
        self.youtube = None
        
    def authenticate(self, installed_app_port: int = 0) -> bool:
        """Authenticate with YouTube API using OAuth"""
        try:
            logger.info("Authenticating with YouTube API...")
            
            # Check if client_secret.json exists
            if not self.client_secret_file.exists():
                logger.error("client_secret.json not found")
                raise FileNotFoundError("client_secret.json not found. Please set up OAuth credentials first.")
            
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
                    logger.info("Running OAuth flow...")
                    # Run the OAuth flow
                    creds = flow.run_local_server(port=installed_app_port)
                
                # Save credentials
                with open(self.token_file, 'w') as f:
                    f.write(creds.to_json())
                logger.info("OAuth credentials saved")
            
            # Build YouTube service
            self.youtube = build('youtube', 'v3', credentials=creds)
            logger.info("YouTube API service initialized")
            return True
            
        except Exception as e:
            logger.error(f"YouTube authentication failed: {e}")
            raise
    
    def test_connection(self) -> Dict:
        """Test YouTube API connection"""
        try:
            if not self.youtube:
                self.authenticate()
            
            # Test with a simple API call
            request = self.youtube.channels().list(
                part="snippet",
                mine=True
            )
            response = request.execute()
            
            if 'items' in response and response['items']:
                channel = response['items'][0]
                return {
                    'success': True,
                    'channel_name': channel['snippet']['title'],
                    'channel_id': channel['id']
                }
            else:
                return {
                    'success': False,
                    'error': 'No channels found'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def upload_video(self, 
                    video_path: str, 
                    title: str = "", 
                    description: str = "", 
                    tags: List[str] = None, 
                    privacy_status: str = "private",
                    category_id: str = "22",  # People & Blogs
                    is_short: bool = True) -> Dict:
        """Upload a video to YouTube"""
        try:
            if not self.youtube:
                self.authenticate()
            
            video_path = Path(video_path)
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Prepare metadata
            body = {
                'snippet': {
                    'title': title or video_path.stem,
                    'description': description,
                    'tags': tags or [],
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Add #Shorts hashtag if it's a short video
            if is_short and '#Shorts' not in body['snippet']['title']:
                body['snippet']['title'] = f"{body['snippet']['title']} #Shorts"
            
            # Create media upload
            media = MediaFileUpload(
                str(video_path), 
                chunksize=1024*1024, 
                resumable=True
            )
            
            logger.info(f"Uploading video: {video_path.name}")
            
            # Upload the video
            request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Execute the upload
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Uploaded {int(status.progress() * 100)}%")
            
            logger.info(f"Upload completed: {response['id']}")
            
            return {
                'success': True,
                'video_id': response['id'],
                'title': response['snippet']['title'],
                'url': f"https://www.youtube.com/watch?v={response['id']}"
            }
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_upload_status(self, video_id: str) -> Dict:
        """Get the status of an uploaded video"""
        try:
            if not self.youtube:
                self.authenticate()
            
            request = self.youtube.videos().list(
                part="status,snippet",
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                video = response['items'][0]
                return {
                    'success': True,
                    'video_id': video_id,
                    'status': video['status']['uploadStatus'],
                    'privacy_status': video['status']['privacyStatus'],
                    'title': video['snippet']['title'],
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                }
            else:
                return {
                    'success': False,
                    'error': 'Video not found'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Global functions for easy integration
def authenticate(installed_app_port: int = 0) -> bool:
    """Global authentication function"""
    base_path = os.environ.get('TRENDCLIP_BASE', os.path.expanduser('~/TrendClipOne'))
    uploader = YouTubeUploader(base_path)
    return uploader.authenticate(installed_app_port)

def upload_video(video_path: str, 
                title: str = "", 
                description: str = "", 
                tags: List[str] = None, 
                privacy_status: str = "private") -> Dict:
    """Global upload function"""
    base_path = os.environ.get('TRENDCLIP_BASE', os.path.expanduser('~/TrendClipOne'))
    uploader = YouTubeUploader(base_path)
    return uploader.upload_video(video_path, title, description, tags, privacy_status)

def test_connection() -> Dict:
    """Global test function"""
    base_path = os.environ.get('TRENDCLIP_BASE', os.path.expanduser('~/TrendClipOne'))
    uploader = YouTubeUploader(base_path)
    return uploader.test_connection()

def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Video Uploader")
    parser.add_argument("video_path", help="Path to video file")
    parser.add_argument("--title", help="Video title")
    parser.add_argument("--description", help="Video description")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private", help="Privacy status")
    parser.add_argument("--test", action="store_true", help="Test connection only")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        base_path = os.environ.get('TRENDCLIP_BASE', os.path.expanduser('~/TrendClipOne'))
        uploader = YouTubeUploader(base_path)
        
        if args.test:
            result = uploader.test_connection()
            if result['success']:
                print(f"✅ Connection successful: {result['channel_name']}")
            else:
                print(f"❌ Connection failed: {result['error']}")
        else:
            # Parse tags
            tags = [tag.strip() for tag in args.tags.split(',')] if args.tags else None
            
            # Upload video
            result = uploader.upload_video(
                args.video_path,
                title=args.title,
                description=args.description,
                tags=tags,
                privacy_status=args.privacy
            )
            
            if result['success']:
                print(f"✅ Upload successful!")
                print(f"Video ID: {result['video_id']}")
                print(f"Title: {result['title']}")
                print(f"URL: {result['url']}")
            else:
                print(f"❌ Upload failed: {result['error']}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
