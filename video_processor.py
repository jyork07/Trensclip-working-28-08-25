#!/usr/bin/env python3
"""
TrendClip Desktop - Video Processing Module
Implements 9:16 vertical transform with smart framing and audio processing
"""

import os
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile
import shutil

class VideoProcessor:
    """Handles video processing including 9:16 vertical transform"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.ffmpeg_path = self._get_ffmpeg_path()
        self.logger = logging.getLogger(__name__)
        
    def _get_ffmpeg_path(self) -> str:
        """Get FFmpeg path from config or environment"""
        # Check config first
        if 'ffmpeg_path' in self.config:
            return self.config['ffmpeg_path']
        
        # Check environment variable
        ffmpeg_env = os.environ.get('FFMPEG_BIN')
        if ffmpeg_env:
            return ffmpeg_env
            
        # Check common locations
        common_paths = [
            r"%USERPROFILE%\TrendClipOne\tools\ffmpeg\bin\ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
            "ffmpeg"  # System PATH
        ]
        
        for path in common_paths:
            expanded_path = os.path.expandvars(path)
            if os.path.exists(expanded_path):
                return expanded_path
                
        raise FileNotFoundError("FFmpeg not found. Please install FFmpeg or set FFMPEG_BIN environment variable.")
    
    def get_video_info(self, input_path: str) -> Dict:
        """Get video information using FFprobe"""
        try:
            cmd = [
                self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe'),
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                input_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFprobe failed: {e}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse FFprobe output: {e}")
            raise
    
    def detect_aspect_ratio(self, video_info: Dict) -> Tuple[int, int]:
        """Detect video aspect ratio from streams"""
        for stream in video_info.get('streams', []):
            if stream.get('codec_type') == 'video':
                width = int(stream.get('width', 0))
                height = int(stream.get('height', 0))
                if width and height:
                    return width, height
        return 16, 9  # Default fallback
    
    def calculate_crop_parameters(self, input_path: str, target_aspect: str = "9:16") -> Dict:
        """Calculate smart crop parameters for 9:16 transform"""
        try:
            video_info = self.get_video_info(input_path)
            width, height = self.detect_aspect_ratio(video_info)
            
            # Parse target aspect ratio
            target_w, target_h = map(int, target_aspect.split(':'))
            target_ratio = target_w / target_h
            
            # Calculate crop parameters
            current_ratio = width / height
            
            if current_ratio > target_ratio:
                # Video is wider than target - crop sides
                new_width = int(height * target_ratio)
                crop_x = (width - new_width) // 2
                crop_y = 0
                crop_width = new_width
                crop_height = height
            else:
                # Video is taller than target - crop top/bottom
                new_height = int(width / target_ratio)
                crop_x = 0
                crop_y = (height - new_height) // 2
                crop_width = width
                crop_height = new_height
            
            return {
                'crop_x': crop_x,
                'crop_y': crop_y,
                'crop_width': crop_width,
                'crop_height': crop_height,
                'original_width': width,
                'original_height': height,
                'target_width': int(crop_width),
                'target_height': int(crop_height)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate crop parameters: {e}")
            # Fallback to center crop
            return {
                'crop_x': 0,
                'crop_y': 0,
                'crop_width': 'iw',
                'crop_height': 'ih',
                'target_width': 1080,
                'target_height': 1920
            }
    
    def process_to_9_16(self, input_path: str, output_path: str, duration: int = 60) -> bool:
        """
        Process video to 9:16 vertical format with smart framing
        
        Args:
            input_path: Input video file path
            output_path: Output video file path
            duration: Target duration in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Processing {input_path} to 9:16 format")
            
            # Calculate crop parameters
            crop_params = self.calculate_crop_parameters(input_path)
            
            # Build FFmpeg command for 9:16 transform
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-t', str(duration),  # Limit duration
                '-vf', f"crop={crop_params['crop_width']}:{crop_params['crop_height']}:{crop_params['crop_x']}:{crop_params['crop_y']},scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-ar', '48000',
                '-ac', '2',
                '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',  # Audio normalization
                '-movflags', '+faststart',
                '-y',  # Overwrite output
                output_path
            ]
            
            self.logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                self.logger.info(f"Successfully created {output_path} ({file_size} bytes)")
                return True
            else:
                self.logger.error("Output file not created")
                return False
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg failed: {e}")
            self.logger.error(f"FFmpeg stderr: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Video processing failed: {e}")
            return False
    
    def create_thumbnail(self, input_path: str, output_path: str, time: str = "00:00:05") -> bool:
        """Create thumbnail from video"""
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-ss', time,
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if os.path.exists(output_path):
                self.logger.info(f"Created thumbnail: {output_path}")
                return True
            else:
                self.logger.error("Thumbnail not created")
                return False
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Thumbnail creation failed: {e}")
            return False
    
    def extract_audio(self, input_path: str, output_path: str) -> bool:
        """Extract audio from video"""
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-vn',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if os.path.exists(output_path):
                self.logger.info(f"Extracted audio: {output_path}")
                return True
            else:
                self.logger.error("Audio extraction failed")
                return False
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Audio extraction failed: {e}")
            return False
    
    def get_video_duration(self, input_path: str) -> float:
        """Get video duration in seconds"""
        try:
            video_info = self.get_video_info(input_path)
            duration_str = video_info.get('format', {}).get('duration', '0')
            return float(duration_str)
        except Exception as e:
            self.logger.error(f"Failed to get video duration: {e}")
            return 0.0
    
    def validate_output(self, output_path: str) -> bool:
        """Validate output video file"""
        try:
            if not os.path.exists(output_path):
                return False
            
            # Check file size
            file_size = os.path.getsize(output_path)
            if file_size < 1024:  # Less than 1KB
                return False
            
            # Try to get video info
            video_info = self.get_video_info(output_path)
            
            # Check if it has video stream
            has_video = any(stream.get('codec_type') == 'video' for stream in video_info.get('streams', []))
            
            return has_video
            
        except Exception as e:
            self.logger.error(f"Output validation failed: {e}")
            return False

def create_video_processor(config: Dict) -> VideoProcessor:
    """Factory function to create VideoProcessor instance"""
    return VideoProcessor(config)

# Example usage
if __name__ == "__main__":
    # Test configuration
    test_config = {
        'ffmpeg_path': r'%USERPROFILE%\TrendClipOne\tools\ffmpeg\bin\ffmpeg.exe',
        'clip': {
            'seconds': 60,
            'target_aspect': '9:16',
            'preset': 'veryfast',
            'crf': 23
        }
    }
    
    processor = create_video_processor(test_config)
    print("Video processor initialized successfully")
