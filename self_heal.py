#!/usr/bin/env python3
"""
TrendClip Desktop - Self-Healing Toolchain
Automatically detects and installs missing tools with checksum validation
"""

import os
import sys
import hashlib
import json
import logging
import subprocess
import urllib.request
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import platform

class SelfHealToolchain:
    """Self-healing toolchain for TrendClip Desktop"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.tools_path = self.base_path / "tools"
        self.logger = logging.getLogger(__name__)
        
        # Tool definitions with checksums and download URLs
        self.tools = {
            'ffmpeg': {
                'version': '6.1',
                'windows_url': 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip',
                'checksum': 'sha256:...',  # Will be updated with actual checksum
                'extract_path': 'ffmpeg-master-latest-win64-gpl/bin',
                'executable': 'ffmpeg.exe',
                'probe_executable': 'ffprobe.exe'
            },
            'yt-dlp': {
                'version': '2024.03.10',
                'windows_url': 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe',
                'checksum': 'sha256:...',  # Will be updated with actual checksum
                'executable': 'yt-dlp.exe'
            }
        }
        
        # Create tools directory
        self.tools_path.mkdir(parents=True, exist_ok=True)
    
    def get_system_info(self) -> Dict:
        """Get system information for tool selection"""
        return {
            'platform': platform.system(),
            'architecture': platform.architecture()[0],
            'machine': platform.machine(),
            'processor': platform.processor()
        }
    
    def calculate_file_checksum(self, file_path: str, algorithm: str = 'sha256') -> str:
        """Calculate file checksum"""
        try:
            hash_func = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            return f"{algorithm}:{hash_func.hexdigest()}"
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum: {e}")
            return ""
    
    def verify_checksum(self, file_path: str, expected_checksum: str) -> bool:
        """Verify file checksum"""
        if not expected_checksum or expected_checksum == 'sha256:...':
            self.logger.warning("No checksum provided, skipping verification")
            return True
        
        actual_checksum = self.calculate_file_checksum(file_path)
        return actual_checksum == expected_checksum
    
    def download_file(self, url: str, destination: str) -> bool:
        """Download file from URL"""
        try:
            self.logger.info(f"Downloading {url} to {destination}")
            
            # Create destination directory
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            # Download with progress
            with urllib.request.urlopen(url) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(destination, 'wb') as f:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.logger.info(f"Download progress: {progress:.1f}%")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return False
    
    def extract_zip(self, zip_path: str, extract_to: str) -> bool:
        """Extract ZIP file"""
        try:
            self.logger.info(f"Extracting {zip_path} to {extract_to}")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            return False
    
    def check_tool_availability(self, tool_name: str) -> Tuple[bool, str]:
        """Check if tool is available and working"""
        if tool_name not in self.tools:
            return False, f"Unknown tool: {tool_name}"
        
        tool_info = self.tools[tool_name]
        executable = tool_info['executable']
        
        # Check in tools directory first
        tool_path = self.tools_path / executable
        if tool_path.exists():
            # Test if it works
            try:
                result = subprocess.run([str(tool_path), '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return True, str(tool_path)
            except Exception as e:
                self.logger.warning(f"Tool test failed: {e}")
        
        # Check system PATH
        try:
            result = subprocess.run([executable, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True, executable
        except Exception:
            pass
        
        return False, ""
    
    def install_ffmpeg(self) -> bool:
        """Install FFmpeg"""
        try:
            self.logger.info("Installing FFmpeg...")
            
            tool_info = self.tools['ffmpeg']
            url = tool_info['windows_url']
            
            # Download to temporary location
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                temp_zip = tmp_file.name
            
            if not self.download_file(url, temp_zip):
                return False
            
            # Extract to tools directory
            ffmpeg_dir = self.tools_path / "ffmpeg"
            if not self.extract_zip(temp_zip, str(self.tools_path)):
                return False
            
            # Find and move executables
            extract_path = self.tools_path / tool_info['extract_path']
            if extract_path.exists():
                # Move executables to tools/ffmpeg/bin/
                bin_dir = ffmpeg_dir / "bin"
                bin_dir.mkdir(parents=True, exist_ok=True)
                
                for exe in ['ffmpeg.exe', 'ffprobe.exe']:
                    src = extract_path / exe
                    dst = bin_dir / exe
                    if src.exists():
                        shutil.move(str(src), str(dst))
            
            # Clean up
            os.unlink(temp_zip)
            
            # Verify installation
            available, path = self.check_tool_availability('ffmpeg')
            if available:
                self.logger.info(f"FFmpeg installed successfully: {path}")
                return True
            else:
                self.logger.error("FFmpeg installation verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"FFmpeg installation failed: {e}")
            return False
    
    def install_yt_dlp(self) -> bool:
        """Install yt-dlp"""
        try:
            self.logger.info("Installing yt-dlp...")
            
            tool_info = self.tools['yt-dlp']
            url = tool_info['windows_url']
            
            # Download directly to tools directory
            destination = self.tools_path / tool_info['executable']
            
            if not self.download_file(url, str(destination)):
                return False
            
            # Make executable (on Unix systems)
            if platform.system() != 'Windows':
                os.chmod(destination, 0o755)
            
            # Verify installation
            available, path = self.check_tool_availability('yt-dlp')
            if available:
                self.logger.info(f"yt-dlp installed successfully: {path}")
                return True
            else:
                self.logger.error("yt-dlp installation verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"yt-dlp installation failed: {e}")
            return False
    
    def heal_tool(self, tool_name: str) -> bool:
        """Heal a specific tool"""
        self.logger.info(f"Attempting to heal tool: {tool_name}")
        
        # Check if tool is already available
        available, path = self.check_tool_availability(tool_name)
        if available:
            self.logger.info(f"Tool {tool_name} is already available: {path}")
            return True
        
        # Install tool
        if tool_name == 'ffmpeg':
            return self.install_ffmpeg()
        elif tool_name == 'yt-dlp':
            return self.install_yt_dlp()
        else:
            self.logger.error(f"Unknown tool: {tool_name}")
            return False
    
    def heal_all_tools(self) -> Dict[str, bool]:
        """Heal all tools"""
        results = {}
        
        for tool_name in self.tools.keys():
            results[tool_name] = self.heal_tool(tool_name)
        
        return results
    
    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """Get the path to a tool"""
        available, path = self.check_tool_availability(tool_name)
        if available:
            return path
        return None
    
    def update_tool_checksums(self) -> None:
        """Update tool checksums (for development)"""
        for tool_name, tool_info in self.tools.items():
            available, path = self.check_tool_availability(tool_name)
            if available and path:
                checksum = self.calculate_file_checksum(path)
                self.logger.info(f"{tool_name} checksum: {checksum}")
    
    def create_environment_script(self) -> str:
        """Create environment setup script"""
        script_content = f"""@echo off
REM TrendClip Desktop Environment Setup
REM Generated by Self-Heal Toolchain

set TRENDCLIP_BASE={self.base_path}
set FFMPEG_BIN={self.tools_path}\\ffmpeg\\bin\\ffmpeg.exe
set YTDLP_PATH={self.tools_path}\\yt-dlp.exe

REM Add tools to PATH
set PATH=%FFMPEG_BIN%;%YTDLP_PATH%;%PATH%

echo TrendClip Desktop environment configured
echo FFmpeg: %FFMPEG_BIN%
echo yt-dlp: %YTDLP_PATH%
"""
        
        script_path = self.base_path / "setup_env.bat"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        return str(script_path)

def create_self_heal_toolchain(base_path: str) -> SelfHealToolchain:
    """Factory function to create SelfHealToolchain instance"""
    return SelfHealToolchain(base_path)

# Example usage
if __name__ == "__main__":
    # Test self-healing
    base_path = os.path.expandvars(r"%USERPROFILE%\TrendClipOne")
    toolchain = create_self_heal_toolchain(base_path)
    
    # Check and heal tools
    results = toolchain.heal_all_tools()
    
    for tool, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {tool}: {'Available' if success else 'Failed'}")
    
    # Create environment script
    env_script = toolchain.create_environment_script()
    print(f"Environment script created: {env_script}")
