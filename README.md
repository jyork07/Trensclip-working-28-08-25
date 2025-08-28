# TrendClip Desktop

**One-click, fully local Windows toolkit** for automated video processing and YouTube Shorts creation.

## 🎯 Overview

TrendClip Desktop is a comprehensive Windows application that automates the entire video processing pipeline:
- **Discover** trending videos
- **Download** via yt-dlp
- **Process** into 9:16 vertical shorts
- **Upload** to YouTube (optional)
- **Track** analytics and income in GBP

## ✨ Features

### 🚀 **Core Features**
- **Desktop App**: Native window via pywebview (no external browser)
- **Self-Healing**: Auto-installs missing dependencies (Python, FFmpeg, yt-dlp)
- **Portable**: Everything under `%USERPROFILE%\TrendClipOne`
- **Zero-Friction**: Guided wizards, sensible defaults, desktop shortcuts

### 🛠️ **Tools & Automation**
- **Content Wizard**: CLI-based content selection and filtering
- **API Wizard**: OAuth setup for YouTube uploads
- **Autopilot**: Automated download → process → upload pipeline
- **Packager**: Create distributable ZIP packages

### 📊 **Dashboard Features**
- **Overview**: System status and configuration
- **Self-Test**: Comprehensive system diagnostics
- **YouTube Upload**: Drag & drop video uploads
- **Analytics**: Track views, income, and performance
- **Job Queue**: Manage video processing tasks

## 🚀 Quick Start

### Prerequisites
- Windows 10/11
- Internet connection
- 2GB+ free disk space
- 4GB+ RAM

### Installation

1. **Download the script**:
   ```powershell
   # Clone or download Install_TrendClip_Desktop.ps1
   ```

2. **Run the installer**:
   ```powershell
   # Set execution policy (one-time)
   Set-ExecutionPolicy Bypass -Scope Process -Force
   
   # Install and launch
   .\Install_TrendClip_Desktop.ps1
   ```

3. **Follow the setup wizard**:
   - The script will auto-install Python, FFmpeg, and dependencies
   - Creates desktop shortcuts
   - Launches the desktop application

## 📋 Usage Options

```powershell
# Standard installation
.\Install_TrendClip_Desktop.ps1

# Check dependencies only
.\Install_TrendClip_Desktop.ps1 -CheckDeps

# Use system Python (no virtual environment)
.\Install_TrendClip_Desktop.ps1 -UseSystemPython

# Rebuild virtual environment
.\Install_TrendClip_Desktop.ps1 -Reinstall

# Force reinstall Dash components
.\Install_TrendClip_Desktop.ps1 -RebuildDash

# Start in background
.\Install_TrendClip_Desktop.ps1 -Detached

# Create distributable ZIP
.\Install_TrendClip_Desktop.ps1 -Pack

# Launch with wizards
.\Install_TrendClip_Desktop.ps1 -RunWizard

# Complete reset (removes all data)
.\Install_TrendClip_Desktop.ps1 -Purge
```

## 🏗️ Architecture

### Directory Structure
```
%USERPROFILE%\TrendClipOne\
├── assets/           # CSS and static files
├── .secrets/         # OAuth credentials and tokens
├── scripts/          # PowerShell helper scripts
├── dist/            # Processed videos and uploads
├── logs/            # Application and autopilot logs
├── data/            # Job configurations and data
├── .venv/           # Python virtual environment
└── tools/           # Portable tools (FFmpeg, etc.)
```

### Key Components
- **TrendClipDesktop.py**: Main desktop wrapper (pywebview)
- **TrendClipDashboard_Standalone.py**: Dash web application
- **autopilot.py**: Video processing pipeline
- **youtube_uploader.py**: YouTube API integration
- **wizard.py**: Content selection wizard
- **api_wizard.py**: OAuth setup wizard

## 🔧 Configuration

### Environment Variables
- `TRENDCLIP_PORT`: Web server port (default: auto-assigned)
- `TRENDCLIP_BIND`: Bind address (default: 127.0.0.1)
- `TRENDCLIP_BASE`: Installation directory
- `FFMPEG_BIN`: Custom FFmpeg path (optional)

### Configuration File
`config.yaml` contains:
- App settings (port, bind address)
- YouTube upload preferences
- Autopilot settings (max URLs, duration, tags)
- Path configurations

## 🎥 Video Processing Pipeline

### Autopilot Workflow
1. **URL Queue**: Read URLs from `urls.txt`
2. **Download**: Use yt-dlp to fetch videos
3. **Process**: Convert to 9:16 vertical format
4. **Enhance**: Apply filters, effects, and optimizations
5. **Upload**: Optional YouTube upload with metadata
6. **Track**: Log analytics and performance metrics

### Supported Formats
- **Input**: YouTube, TikTok, Instagram, and more (via yt-dlp)
- **Output**: MP4 (H.264/AAC) optimized for mobile
- **Resolution**: 1080x1920 (9:16 vertical)
- **Duration**: Configurable (default: 30 seconds)

## 🔐 YouTube Integration

### OAuth Setup
1. Create Google Cloud Project
2. Enable YouTube Data API v3
3. Create OAuth 2.0 Desktop Application
4. Download `client_secret.json`
5. Run API Wizard: `.\Install_TrendClip_Desktop.ps1 -RunWizard`

### Upload Features
- **Privacy Control**: Private, unlisted, or public
- **Metadata**: Title, description, tags
- **Shorts Optimization**: Automatic #Shorts hashtag
- **Batch Processing**: Queue multiple videos

## 📊 Analytics & Income Tracking

### Metrics Tracked
- **Views**: Per-video view counts
- **Income**: GBP revenue based on CPM
- **Performance**: Processing time and success rates
- **Trends**: Historical data and patterns

### Income Calculation
```
Revenue = (Views / 1000) × CPM (GBP)
```

## 🛠️ Development

### Local Development
```powershell
# Clone repository
git clone https://github.com/yourusername/TrendClip.git
cd TrendClip

# Install dependencies
.\Install_TrendClip_Desktop.ps1 -UseSystemPython

# Run in development mode
.\Install_TrendClip_Desktop.ps1 -RebuildDash
```

### Project Structure
```
TrendClip/
├── Install_TrendClip_Desktop.ps1    # Main installer
├── README.md                        # This file
├── LICENSE                          # License information
├── .gitignore                       # Git ignore rules
└── docs/                           # Documentation
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Development Guidelines
- Follow PowerShell best practices
- Add comprehensive error handling
- Update documentation for new features
- Test on clean Windows installations

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues
- **Python not found**: Install Python 3.8+ from python.org
- **FFmpeg errors**: Script auto-installs portable version
- **OAuth issues**: Run API wizard for step-by-step setup
- **Upload failures**: Check YouTube API quotas and permissions

### Getting Help
- Check the logs in `%USERPROFILE%\TrendClipOne\logs\`
- Run self-test: `.\Install_TrendClip_Desktop.ps1 -CheckDeps`
- Review the dashboard's Self-Test tab

## 🔄 Version History

### v1.9.0-desktop
- Enhanced dependency checking and auto-installation
- Improved OAuth wizard and YouTube integration
- Better error handling and logging
- Comprehensive self-test functionality
- Portable tool installation (FFmpeg, yt-dlp)

### v1.5.0
- Initial desktop application release
- Basic video processing pipeline
- YouTube upload functionality
- Dashboard interface

---

**TrendClip Desktop** - Transform your video workflow with automated processing and YouTube integration.
