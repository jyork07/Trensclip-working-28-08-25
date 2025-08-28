#!/usr/bin/env python3
"""
TrendClip Desktop - Feature Integration Script
Integrates new features into existing installation
"""

import os
import sys
import shutil
from pathlib import Path

def integrate_new_features():
    """Integrate new features into TrendClip installation"""
    
    # Get base path
    base_path = os.path.expandvars(r"%USERPROFILE%\TrendClipOne")
    base_dir = Path(base_path)
    
    if not base_dir.exists():
        print(f"TrendClip installation not found at: {base_path}")
        return False
    
    print(f"Integrating new features into: {base_path}")
    
    # Copy new modules
    new_modules = [
        "video_processor.py",
        "self_heal.py", 
        "packager.py"
    ]
    
    for module in new_modules:
        src = Path(module)
        dst = base_dir / module
        
        if src.exists():
            shutil.copy2(src, dst)
            print(f"✓ Copied {module}")
        else:
            print(f"✗ Module not found: {module}")
    
    # Update requirements.txt
    requirements_file = base_dir / "requirements.txt"
    new_requirements = [
        "opencv-python>=4.8.0",
        "pillow>=10.0.0",
        "numpy>=1.24.0"
    ]
    
    if requirements_file.exists():
        with open(requirements_file, 'r') as f:
            existing = f.read()
        
        # Add new requirements if not present
        for req in new_requirements:
            if req.split('>=')[0] not in existing:
                with open(requirements_file, 'a') as f:
                    f.write(f"\n{req}")
                print(f"✓ Added requirement: {req}")
    else:
        print("✗ requirements.txt not found")
    
    # Create enhanced config
    config_file = base_dir / "config.yaml"
    if config_file.exists():
        print("✓ Config file exists")
    else:
        # Create default config
        config_content = """# TrendClip Desktop Configuration
version: "1.9.0-desktop"
currency: "GBP"

app:
  port: 0  # Auto-assign
  bind: "127.0.0.1"
  title: "TrendClip Desktop"

paths:
  base: "%USERPROFILE%/TrendClipOne"
  downloads: "downloads"
  clips: "clips"
  logs: "logs"
  stats: "stats"
  tools: "tools"

youtube:
  scopes: ["https://www.googleapis.com/auth/youtube.upload"]
  privacy: "private"
  shorts_hashtag: "#Shorts"

autopilot:
  max_urls: 10
  duration: 60
  vertical_transform: true
  upload_enabled: false
  tags: ["trending", "viral", "shorts"]
"""
        
        with open(config_file, 'w') as f:
            f.write(config_content)
        print("✓ Created default config.yaml")
    
    print("\nFeature integration complete!")
    print("\nNew features available:")
    print("- 9:16 vertical video processing (video_processor.py)")
    print("- Self-healing toolchain (self_heal.py)")
    print("- Enhanced packager (packager.py)")
    
    return True

if __name__ == "__main__":
    success = integrate_new_features()
    if success:
        print("\n✓ Integration successful!")
    else:
        print("\n✗ Integration failed!")
        sys.exit(1)
