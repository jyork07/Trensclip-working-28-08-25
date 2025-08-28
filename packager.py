#!/usr/bin/env python3
"""
TrendClip Desktop - Packager Module
Creates distributable ZIP packages for TrendClip Desktop
"""

import os
import sys
import json
import logging
import zipfile
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import subprocess

class TrendClipPackager:
    """Packager for TrendClip Desktop distributions"""
    
    def __init__(self, base_path: str, version: str = "1.9.0-desktop"):
        self.base_path = Path(base_path)
        self.version = version
        self.logger = logging.getLogger(__name__)
        
        # Files to include in package
        self.include_patterns = [
            "*.py",
            "*.ps1",
            "*.bat",
            "*.json",
            "*.yaml",
            "*.txt",
            "*.md",
            "*.css",
            "*.html"
        ]
        
        # Directories to include
        self.include_dirs = [
            "assets",
            "scripts",
            "tools",
            "docs"
        ]
        
        # Files to exclude
        self.exclude_patterns = [
            "*.log",
            "*.tmp",
            "*.temp",
            "*.bak",
            "*.backup",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".git",
            ".vscode",
            ".idea",
            "node_modules",
            "venv",
            ".venv",
            "env",
            ".env"
        ]
        
        # Sensitive directories to exclude
        self.exclude_dirs = [
            ".secrets",
            "logs",
            "downloads",
            "processed",
            "clips",
            "stats",
            "data"
        ]
    
    def get_package_name(self) -> str:
        """Generate package name with version and date"""
        date_str = datetime.now().strftime("%Y%m%d")
        return f"TrendClipOne_{self.version}_{date_str}"
    
    def should_include_file(self, file_path: Path) -> bool:
        """Check if file should be included in package"""
        file_str = str(file_path)
        
        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if pattern in file_str:
                return False
        
        # Check if in exclude directories
        for exclude_dir in self.exclude_dirs:
            if exclude_dir in file_str:
                return False
        
        # Check include patterns
        for pattern in self.include_patterns:
            if file_path.match(pattern):
                return True
        
        # Check if in include directories
        for include_dir in self.include_dirs:
            if include_dir in file_str:
                return True
        
        # Include specific important files
        important_files = [
            "Install_TrendClip_Desktop.ps1",
            "README.md",
            "LICENSE",
            "CHANGELOG.md",
            "DESIGN.md",
            "CONTRIBUTING.md",
            "requirements.txt",
            "config.yaml"
        ]
        
        if file_path.name in important_files:
            return True
        
        return False
    
    def get_files_to_package(self) -> List[Path]:
        """Get list of files to include in package"""
        files = []
        
        def scan_directory(directory: Path):
            """Recursively scan directory for files"""
            try:
                for item in directory.iterdir():
                    if item.is_file():
                        if self.should_include_file(item):
                            files.append(item)
                    elif item.is_dir():
                        # Don't scan excluded directories
                        if not any(exclude_dir in str(item) for exclude_dir in self.exclude_dirs):
                            scan_directory(item)
            except PermissionError:
                self.logger.warning(f"Permission denied accessing: {directory}")
            except Exception as e:
                self.logger.error(f"Error scanning directory {directory}: {e}")
        
        scan_directory(self.base_path)
        return files
    
    def create_package_manifest(self, files: List[Path]) -> Dict:
        """Create package manifest"""
        manifest = {
            "version": self.version,
            "created": datetime.now().isoformat(),
            "base_path": str(self.base_path),
            "files": [],
            "directories": [],
            "total_size": 0
        }
        
        for file_path in files:
            try:
                stat = file_path.stat()
                relative_path = str(file_path.relative_to(self.base_path))
                
                file_info = {
                    "path": relative_path,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
                
                manifest["files"].append(file_info)
                manifest["total_size"] += stat.st_size
                
                # Track directories
                parent_dir = str(file_path.parent.relative_to(self.base_path))
                if parent_dir and parent_dir not in manifest["directories"]:
                    manifest["directories"].append(parent_dir)
                    
            except Exception as e:
                self.logger.error(f"Error processing file {file_path}: {e}")
        
        return manifest
    
    def create_installer_script(self, package_name: str) -> str:
        """Create installer script for the package"""
        script_content = f"""@echo off
REM TrendClip Desktop Installer
REM Package: {package_name}
REM Version: {self.version}

echo ========================================
echo TrendClip Desktop Installer
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as administrator
) else (
    echo Running as regular user
)

REM Set installation directory
set INSTALL_DIR=%USERPROFILE%\\TrendClipOne
echo Installing to: %INSTALL_DIR%

REM Create installation directory
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo Created installation directory
) else (
    echo Installation directory already exists
)

REM Extract package
echo.
echo Extracting package...
powershell -command "Expand-Archive -Path '%~dp0{package_name}.zip' -DestinationPath '%INSTALL_DIR%' -Force"

if %errorLevel% == 0 (
    echo Package extracted successfully
) else (
    echo Failed to extract package
    pause
    exit /b 1
)

REM Set up environment
echo.
echo Setting up environment...
call "%INSTALL_DIR%\\setup_env.bat"

REM Create desktop shortcuts
echo.
echo Creating desktop shortcuts...
powershell -command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\\Desktop\\TrendClip Desktop.lnk'); $Shortcut.TargetPath = 'powershell.exe'; $Shortcut.Arguments = '-ExecutionPolicy Bypass -File \"%INSTALL_DIR%\\Install_TrendClip_Desktop.ps1\"'; $Shortcut.Save()"

REM Create start menu shortcut
echo Creating start menu shortcut...
powershell -command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\TrendClip Desktop.lnk'); $Shortcut.TargetPath = 'powershell.exe'; $Shortcut.Arguments = '-ExecutionPolicy Bypass -File \"%INSTALL_DIR%\\Install_TrendClip_Desktop.ps1\"'; $Shortcut.Save()"

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo TrendClip Desktop has been installed to:
echo %INSTALL_DIR%
echo.
echo Desktop shortcuts have been created.
echo.
echo To start TrendClip Desktop:
echo 1. Double-click the desktop shortcut, or
echo 2. Run: powershell -ExecutionPolicy Bypass -File "%INSTALL_DIR%\\Install_TrendClip_Desktop.ps1"
echo.
pause
"""
        
        return script_content
    
    def create_package(self, output_dir: Optional[str] = None) -> str:
        """Create the complete package"""
        try:
            self.logger.info("Starting package creation...")
            
            # Determine output directory
            if output_dir is None:
                output_dir = os.path.expanduser("~/Desktop")
            
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Get files to package
            files = self.get_files_to_package()
            self.logger.info(f"Found {len(files)} files to package")
            
            # Create package name
            package_name = self.get_package_name()
            zip_path = output_path / f"{package_name}.zip"
            
            # Create ZIP file
            self.logger.info(f"Creating package: {zip_path}")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    try:
                        # Calculate relative path
                        relative_path = file_path.relative_to(self.base_path)
                        
                        # Add file to ZIP
                        zipf.write(file_path, relative_path)
                        self.logger.debug(f"Added: {relative_path}")
                        
                    except Exception as e:
                        self.logger.error(f"Error adding file {file_path}: {e}")
            
            # Create manifest
            manifest = self.create_package_manifest(files)
            manifest_path = output_path / f"{package_name}_manifest.json"
            
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Create installer script
            installer_script = self.create_installer_script(package_name)
            installer_path = output_path / f"install_{package_name}.bat"
            
            with open(installer_path, 'w') as f:
                f.write(installer_script)
            
            # Get package size
            package_size = zip_path.stat().st_size
            size_mb = package_size / (1024 * 1024)
            
            self.logger.info(f"Package created successfully:")
            self.logger.info(f"  Package: {zip_path}")
            self.logger.info(f"  Size: {size_mb:.1f} MB")
            self.logger.info(f"  Files: {len(files)}")
            self.logger.info(f"  Manifest: {manifest_path}")
            self.logger.info(f"  Installer: {installer_path}")
            
            return str(zip_path)
            
        except Exception as e:
            self.logger.error(f"Package creation failed: {e}")
            raise
    
    def validate_package(self, package_path: str) -> bool:
        """Validate the created package"""
        try:
            zip_path = Path(package_path)
            
            if not zip_path.exists():
                self.logger.error("Package file not found")
                return False
            
            # Check file size
            size_mb = zip_path.stat().st_size / (1024 * 1024)
            if size_mb > 500:  # 500MB limit
                self.logger.error(f"Package too large: {size_mb:.1f} MB")
                return False
            
            # Test ZIP integrity
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                if zipf.testzip() is not None:
                    self.logger.error("ZIP file is corrupted")
                    return False
                
                # Check for essential files
                essential_files = [
                    "Install_TrendClip_Desktop.ps1",
                    "README.md",
                    "LICENSE"
                ]
                
                file_list = zipf.namelist()
                for essential_file in essential_files:
                    if not any(essential_file in f for f in file_list):
                        self.logger.error(f"Missing essential file: {essential_file}")
                        return False
            
            self.logger.info("Package validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Package validation failed: {e}")
            return False
    
    def create_development_package(self) -> str:
        """Create a development package with source code"""
        try:
            self.logger.info("Creating development package...")
            
            # Temporarily modify include patterns for development
            original_patterns = self.include_patterns.copy()
            self.include_patterns.extend([
                "*.py",
                "*.ps1",
                "*.json",
                "*.yaml",
                "*.md",
                "*.txt"
            ])
            
            # Create package
            package_path = self.create_package()
            
            # Restore original patterns
            self.include_patterns = original_patterns
            
            return package_path
            
        except Exception as e:
            self.logger.error(f"Development package creation failed: {e}")
            raise

def create_packager(base_path: str, version: str = "1.9.0-desktop") -> TrendClipPackager:
    """Factory function to create TrendClipPackager instance"""
    return TrendClipPackager(base_path, version)

# Example usage
if __name__ == "__main__":
    # Test packager
    base_path = os.path.expandvars(r"%USERPROFILE%\TrendClipOne")
    packager = create_packager(base_path)
    
    try:
        # Create package
        package_path = packager.create_package()
        
        # Validate package
        if packager.validate_package(package_path):
            print(f"✓ Package created successfully: {package_path}")
        else:
            print("✗ Package validation failed")
            
    except Exception as e:
        print(f"✗ Package creation failed: {e}")
