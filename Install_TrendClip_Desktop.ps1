
 File: Install_TrendClip_Desktop.ps1
 Purpose: Desktop (no external browser) TrendClip — wraps the Dash app in a native window via pywebview.
 Usage:
   .\Install_TrendClip_Desktop.ps1                      # install + run desktop app (venv)
   .\Install_TrendClip_Desktop.ps1 -UseSystemPython     # use system Python (no venv)
   .\Install_TrendClip_Desktop.ps1 -Reinstall           # rebuild venv
   .\Install_TrendClip_Desktop.ps1 -RebuildDash         # force-reinstall dash/plotly/pywebview
   .\Install_TrendClip_Desktop.ps1 -Detached            # start in background
   .\Install_TrendClip_Desktop.ps1 -Pack                # create distributable ZIP and exit
   .\Install_TrendClip_Desktop.ps1 -RunWizard           # also open CLI wizard console
   .\Install_TrendClip_Desktop.ps1 -Purge               # STOP processes & DELETE %USERPROFILE%\TrendClipOne
   .\Install_TrendClip_Desktop.ps1 -CheckDeps           # check dependencies only
 #>

param(
  [switch]$Detached,
  [switch]$RunWizard,
  [switch]$Pack,
  [switch]$Reinstall,
  [switch]$RebuildDash,
  [switch]$UseSystemPython,
  [switch]$Purge,
  [switch]$CheckDeps
)

$ErrorActionPreference = 'Stop'
$Version = '1.9.0-desktop'

function Write-Log { param([string]$Message)
  $ts = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  if (-not $script:LogFile) { $script:LogFile = Join-Path $env:USERPROFILE 'TrendClipOne\logs\install.log' }
  $logDir = Split-Path -Parent $script:LogFile
  if (-not (Test-Path -LiteralPath $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
  Add-Content -LiteralPath $script:LogFile -Value "[$ts] $Message"
  Write-Host $Message
}

function Ensure-Dir { param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null }
}

function Write-TextFileUtf8 { 
  param([Parameter(Mandatory=$true)][string]$Path,[Parameter(Mandatory=$true)][string]$Content)
  $dir = Split-Path -Parent $Path; Ensure-Dir $dir
  [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
}

function Get-FreePort { param([int]$Start=8700,[int]$End=8999)
  for ($p=$Start; $p -le $End; $p++) {
    try { $l=[System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$p); $l.Start(); $l.Stop(); return $p } catch {}
  }
  throw "No free TCP port in $Start..$End"
}

function Stop-TrendClipProcesses {
  Write-Log "Scanning for running TrendClip processes..."
  try {
    $procs = Get-CimInstance Win32_Process | Where-Object {
      ($_.Name -match 'python\.exe' -and $_.CommandLine -match 'TrendClipDesktop\.py|TrendClipDashboard_Standalone\.py') -or
      ($_.Name -match 'TrendClipDesktop\.exe')
    }
    foreach ($p in $procs) {
      Write-Log "Stopping PID $($p.ProcessId): $($p.Name)"
      Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
  } catch {
    Write-Log "Process scan/stop failed (non-fatal): $_"
  }
}

function Test-Command { param([string]$Command)
  try { Get-Command $Command -ErrorAction Stop | Out-Null; return $true } catch { return $false }
}

function Test-PythonVersion { param([string]$PythonCmd)
  try {
    $version = & $PythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
    if ($version -and [version]$version -ge [version]"3.8") { return $true }
    return $false
  } catch { return $false }
}

function Test-Dependencies {
  Write-Log "Checking system dependencies..."
  $issues = @()
  $fixes = @()

  # Check Python
  $pythonFound = $false
  $pythonCmd = $null
  
  if (Test-Command "py") {
    if (Test-PythonVersion "py -3") {
      $pythonFound = $true
      $pythonCmd = "py -3"
      Write-Log "[OK] Python found via 'py -3'"
    }
  } elseif (Test-Command "python") {
    if (Test-PythonVersion "python") {
      $pythonFound = $true
      $pythonCmd = "python"
      Write-Log "[OK] Python found via 'python'"
    }
  } elseif (Test-Command "python3") {
    if (Test-PythonVersion "python3") {
      $pythonFound = $true
      $pythonCmd = "python3"
      Write-Log "[OK] Python found via 'python3'"
    }
  }

  if (-not $pythonFound) {
    $issues += "Python 3.8+ not found"
    $fixes += "Install Python 3.x"
  }

  # Check FFmpeg
  if (Test-Command "ffmpeg") {
    Write-Log "[OK] FFmpeg found"
  } else {
    $issues += "FFmpeg not found"
    $fixes += "Install FFmpeg"
  }

  # Check pip
  if ($pythonFound) {
    try {
      $pipVersion = & $pythonCmd -m pip --version 2>$null
      if ($pipVersion) {
        Write-Log "[OK] pip found"
      } else {
        $issues += "pip not available"
        $fixes += "Upgrade pip"
      }
    } catch {
      $issues += "pip not available"
      $fixes += "Upgrade pip"
    }
  }

  # Check Git (optional but useful)
  if (Test-Command "git") {
    Write-Log "[OK] Git found"
  } else {
    Write-Log "[WARN] Git not found (optional)"
  }

  return @{
    Issues = $issues
    Fixes = $fixes
    PythonCmd = $pythonCmd
    PythonFound = $pythonFound
  }
}

function Install-Chocolatey {
  Write-Log "Installing Chocolatey package manager..."
  try {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Write-Log "[OK] Chocolatey installed"
    return $true
  } catch {
    Write-Log "[ERROR] Failed to install Chocolatey: $_"
    return $false
  }
}

function Install-Python {
  Write-Log "Installing Python via Chocolatey..."
  try {
    if (-not (Test-Command "choco")) {
      if (-not (Install-Chocolatey)) {
        return $false
      }
    }
    choco install python -y
    Write-Log "[OK] Python installed"
    return $true
  } catch {
    Write-Log "[ERROR] Failed to install Python: $_"
    return $false
  }
}

function Install-FFmpeg {
  Write-Log "Installing FFmpeg via Chocolatey..."
  try {
    if (-not (Test-Command "choco")) {
      if (-not (Install-Chocolatey)) {
        return $false
      }
    }
    choco install ffmpeg -y
    Write-Log "[OK] FFmpeg installed"
    return $true
  } catch {
    Write-Log "[ERROR] Failed to install FFmpeg: $_"
    return $false
  }
}

function Install-MissingDependencies {
  Write-Log "Installing missing dependencies..."
  $deps = Test-Dependencies
  
  if ($deps.Issues.Count -eq 0) {
    Write-Log "[OK] All dependencies are satisfied"
    return $true
  }

  Write-Log "Found issues: $($deps.Issues -join ', ')"
  
  foreach ($issue in $deps.Issues) {
    switch ($issue) {
      "Python 3.8+ not found" {
        Write-Log "Installing Python..."
        if (Install-Python) {
          Write-Log "[OK] Python installed successfully"
        } else {
          Write-Log "[ERROR] Failed to install Python automatically"
          return $false
        }
      }
      "FFmpeg not found" {
        Write-Log "Installing FFmpeg..."
        if (Install-FFmpeg) {
          Write-Log "[OK] FFmpeg installed successfully"
        } else {
          Write-Log "[ERROR] Failed to install FFmpeg automatically"
          return $false
        }
      }
      "pip not available" {
        Write-Log "Upgrading pip..."
        try {
          & $deps.PythonCmd -m ensurepip --upgrade
          Write-Log "[OK] pip upgraded"
        } catch {
          Write-Log "[ERROR] Failed to upgrade pip: $_"
          return $false
        }
      }
    }
  }
  
  return $true
}

function Test-TrendClipRequirements {
  Write-Log "=== TRENDCLIP REQUIREMENTS TEST ==="
  $results = @{
    Overall = "PASS"
    Details = @()
    Warnings = @()
    Errors = @()
  }
  
  # Test 1: Tool versions
  Write-Log "Testing tool versions..."
  try {
    if (Test-Command "ffmpeg") {
      $ffmpegVersion = & ffmpeg -version 2>&1 | Select-Object -First 1
      Write-Log "[OK] FFmpeg: $ffmpegVersion"
      $results.Details += "FFmpeg: Available"
    } else {
      $results.Errors += "FFmpeg: Not found"
      $results.Overall = "FAIL"
    }
  } catch {
    $results.Errors += "FFmpeg: Version check failed"
    $results.Overall = "FAIL"
  }
  
  # Test 2: File operations
  Write-Log "Testing file operations..."
  try {
    $testFile = Join-Path $BASE "test_write.txt"
    "TrendClip test write" | Out-File -FilePath $testFile -Encoding UTF8
    $readContent = Get-Content $testFile -Raw
    if ($readContent.Trim() -eq "TrendClip test write") {
      Write-Log "[OK] File operations: Read/write working"
      $results.Details += "File operations: Working"
      Remove-Item $testFile -Force
    } else {
      $results.Errors += "File operations: Read/write mismatch"
      $results.Overall = "FAIL"
    }
  } catch {
    $results.Errors += "File operations: Failed"
    $results.Overall = "FAIL"
  }
  
  # Test 3: Python package availability
  Write-Log "Testing Python packages..."
  $requiredPackages = @("dash", "plotly", "requests", "pandas", "yaml", "moviepy", "pywebview", "yt_dlp")
  $missingPackages = @()
  
  foreach ($pkg in $requiredPackages) {
    try {
      $testResult = & $VENV_PY -c "import $pkg; print('OK')" 2>$null
      if ($testResult -eq "OK") {
        Write-Log "[OK] $pkg: Available"
        $results.Details += "$pkg: Available"
      } else {
        $missingPackages += $pkg
      }
    } catch {
      $missingPackages += $pkg
    }
  }
  
  if ($missingPackages.Count -gt 0) {
    $results.Warnings += "Missing packages: $($missingPackages -join ', ')"
    Write-Log "[WARN] Missing packages: $($missingPackages -join ', ')"
  }
  
  # Test 4: Synthetic clip creation (if FFmpeg available)
  if (Test-Command "ffmpeg") {
    Write-Log "Testing synthetic clip creation..."
    try {
      $testClipDir = Join-Path $BASE "test_clips"
      Ensure-Dir $testClipDir
      $testClipPath = Join-Path $testClipDir "test_5sec.mp4"
      
      # Create a 5-second test video
      $ffmpegCmd = "ffmpeg -f lavfi -i testsrc=duration=5:size=1280x720:rate=30 -f lavfi -i sine=frequency=1000:duration=5 -c:v libx264 -c:a aac -pix_fmt yuv420p -y `"$testClipPath`""
      $ffmpegResult = Invoke-Expression $ffmpegCmd 2>&1
      
      if (Test-Path $testClipPath) {
        $fileSize = (Get-Item $testClipPath).Length
        if ($fileSize -gt 1000) {  # At least 1KB
          Write-Log "[OK] Synthetic clip: Created successfully ($([math]::Round($fileSize/1KB, 2))KB)"
          $results.Details += "Synthetic clip: Created successfully"
          Remove-Item $testClipPath -Force
        } else {
          $results.Warnings += "Synthetic clip: File too small"
          Write-Log "[WARN] Synthetic clip: File too small"
        }
      } else {
        $results.Warnings += "Synthetic clip: Creation failed"
        Write-Log "[WARN] Synthetic clip: Creation failed"
      }
      
      # Cleanup
      if (Test-Path $testClipDir) {
        Remove-Item $testClipDir -Recurse -Force
      }
    } catch {
      $results.Warnings += "Synthetic clip: Test failed"
      Write-Log "[WARN] Synthetic clip: Test failed"
    }
  }
  
  # Test 5: Log and path verification
  Write-Log "Testing log and path verification..."
  try {
    $logTestPath = Join-Path $LOGS "test.log"
    "Test log entry" | Out-File -FilePath $logTestPath -Encoding UTF8
    if (Test-Path $logTestPath) {
      Write-Log "[OK] Log paths: Working"
      $results.Details += "Log paths: Working"
      Remove-Item $logTestPath -Force
    } else {
      $results.Errors += "Log paths: Failed"
      $results.Overall = "FAIL"
    }
  } catch {
    $results.Errors += "Log paths: Test failed"
    $results.Overall = "FAIL"
  }
  
  # Test 6: Network connectivity (basic)
  Write-Log "Testing network connectivity..."
  try {
    $webClient = New-Object System.Net.WebClient
    $webClient.Timeout = 5000  # 5 seconds
    $testResponse = $webClient.DownloadString("https://httpbin.org/get")
    if ($testResponse -and $testResponse.Length -gt 0) {
      Write-Log "[OK] Network: Basic connectivity working"
      $results.Details += "Network: Basic connectivity working"
    } else {
      $results.Warnings += "Network: No response"
      Write-Log "[WARN] Network: No response"
    }
  } catch {
    $results.Warnings += "Network: Connectivity test failed"
    Write-Log "[WARN] Network: Connectivity test failed"
  }
  
  # Test 7: Memory and disk space
  Write-Log "Testing system resources..."
  try {
    $drive = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='$($env:SystemDrive)'"
    $freeGB = [math]::Round($drive.FreeSpace / 1GB, 2)
    if ($freeGB -ge 2) {
      Write-Log "[OK] Disk space: $freeGB GB free (sufficient)"
      $results.Details += "Disk space: $freeGB GB free"
    } else {
      $results.Warnings += "Disk space: Only $freeGB GB free (need 2GB+)"
      Write-Log "[WARN] Disk space: Only $freeGB GB free"
    }
    
    $ram = Get-WmiObject -Class Win32_ComputerSystem
    $ramGB = [math]::Round($ram.TotalPhysicalMemory / 1GB, 2)
    if ($ramGB -ge 4) {
      Write-Log "[OK] RAM: $ramGB GB total (sufficient)"
      $results.Details += "RAM: $ramGB GB total"
    } else {
      $results.Warnings += "RAM: Only $ramGB GB total (need 4GB+)"
      Write-Log "[WARN] RAM: Only $ramGB GB total"
    }
  } catch {
    $results.Warnings += "System resources: Check failed"
    Write-Log "[WARN] System resources: Check failed"
  }
  
  # Summary
  Write-Log "=== TRENDCLIP REQUIREMENTS SUMMARY ==="
  Write-Log "Overall Status: $($results.Overall)"
  Write-Log "Details: $($results.Details.Count) passed"
  Write-Log "Warnings: $($results.Warnings.Count)"
  Write-Log "Errors: $($results.Errors.Count)"
  
  if ($results.Errors.Count -gt 0) {
    Write-Log "Errors: $($results.Errors -join '; ')"
  }
  
  if ($results.Warnings.Count -gt 0) {
    Write-Log "Warnings: $($results.Warnings -join '; ')"
  }
  
  return $results
}

function Install-TrendClipTools {
  Write-Log "=== INSTALLING TRENDCLIP TOOLS ==="
  
  # Create tools directory
  $toolsDir = Join-Path $BASE "tools"
  Ensure-Dir $toolsDir
  
  # Download portable FFmpeg if not available
  if (-not (Test-Command "ffmpeg")) {
    Write-Log "Downloading portable FFmpeg..."
    try {
      $ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
      $ffmpegZip = Join-Path $toolsDir "ffmpeg.zip"
      $ffmpegExtract = Join-Path $toolsDir "ffmpeg"
      
      # Download FFmpeg
      $webClient = New-Object System.Net.WebClient
      $webClient.DownloadFile($ffmpegUrl, $ffmpegZip)
      
      # Extract
      Expand-Archive -Path $ffmpegZip -DestinationPath $ffmpegExtract -Force
      
      # Find ffmpeg.exe in the extracted folder
      $ffmpegExe = Get-ChildItem -Path $ffmpegExtract -Recurse -Name "ffmpeg.exe" | Select-Object -First 1
      if ($ffmpegExe) {
        $ffmpegPath = Join-Path $ffmpegExtract $ffmpegExe
        # Add to PATH for this session
        $env:PATH = "$(Split-Path $ffmpegPath -Parent);$env:PATH"
        Write-Log "[OK] FFmpeg installed to: $ffmpegPath"
      }
      
      # Cleanup
      Remove-Item $ffmpegZip -Force
    } catch {
      Write-Log "[ERROR] Failed to download FFmpeg: $_"
    }
  }
  
  # Download yt-dlp if not available
  if (-not (Test-Command "yt-dlp")) {
    Write-Log "Installing yt-dlp..."
    try {
      & $VENV_PY -m pip install yt-dlp
      Write-Log "[OK] yt-dlp installed"
    } catch {
      Write-Log "[ERROR] Failed to install yt-dlp: $_"
    }
  }
}

function Create-TrendClipShortcuts {
  Write-Log "=== CREATING TRENDCLIP SHORTCUTS ==="
  
  try {
    # Desktop shortcut
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop "TrendClip Desktop.lnk"
    
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$PSScriptRoot\Install_TrendClip_Desktop.ps1`""
    $Shortcut.WorkingDirectory = $PSScriptRoot
    $Shortcut.Description = "Launch TrendClip Desktop"
    $Shortcut.IconLocation = "powershell.exe,0"
    $Shortcut.Save()
    
    Write-Log "[OK] Desktop shortcut created: $shortcutPath"
    
    # Start Menu shortcut
    $startMenu = [Environment]::GetFolderPath("StartMenu")
    $startMenuDir = Join-Path $startMenu "Programs\TrendClip"
    Ensure-Dir $startMenuDir
    
    $startMenuShortcut = Join-Path $startMenuDir "TrendClip Desktop.lnk"
    $Shortcut2 = $WshShell.CreateShortcut($startMenuShortcut)
    $Shortcut2.TargetPath = "powershell.exe"
    $Shortcut2.Arguments = "-ExecutionPolicy Bypass -File `"$PSScriptRoot\Install_TrendClip_Desktop.ps1`""
    $Shortcut2.WorkingDirectory = $PSScriptRoot
    $Shortcut2.Description = "Launch TrendClip Desktop"
    $Shortcut2.IconLocation = "powershell.exe,0"
    $Shortcut2.Save()
    
    Write-Log "[OK] Start Menu shortcut created: $startMenuShortcut"
    
  } catch {
    Write-Log "[ERROR] Failed to create shortcuts: $_"
  }
}

# Base paths
$BASE   = Join-Path $env:USERPROFILE 'TrendClipOne'
$ASSETS = Join-Path $BASE 'assets'
$SECRETS= Join-Path $BASE '.secrets'
$SCRIPTS= Join-Path $BASE 'scripts'
$DIST   = Join-Path $BASE 'dist'
$LOGS   = Join-Path $BASE 'logs'
$VENV   = Join-Path $BASE '.venv'

# Dependency check only mode
if ($CheckDeps) {
  Write-Log "=== DEPENDENCY CHECK ONLY ==="
  $deps = Test-Dependencies
  Write-Log "Dependency Check Results:"
  Write-Log "Python Found: $($deps.PythonFound)"
  Write-Log "Python Command: $($deps.PythonCmd)"
  Write-Log "Issues: $($deps.Issues.Count)"
  if ($deps.Issues.Count -gt 0) {
    Write-Log "Issues: $($deps.Issues -join ', ')"
    Write-Log "Suggested fixes: $($deps.Fixes -join ', ')"
  }
  return
}

# Purge (optional full reset)
if ($Purge) {
  Write-Host "[WARN] PURGE MODE: This will delete $BASE completely (including .secrets). CTRL+C to abort." -ForegroundColor Yellow
  Start-Sleep -Seconds 2
  Stop-TrendClipProcesses
  if (Test-Path -LiteralPath $BASE) {
    Write-Log "Removing $BASE ..."
    try {
      # First attempt
      Remove-Item -LiteralPath $BASE -Recurse -Force -ErrorAction Stop
    } catch {
      Write-Log "Direct removal failed, retrying with CMD rmdir: $_"
      # Retry via cmd (sometimes handles locked junctions better)
      & cmd /c "rmdir /s /q `"$BASE`"" | Out-Null
      Start-Sleep -Milliseconds 500
      if (Test-Path -LiteralPath $BASE) {
        Write-Log "Purge failed. Close any running apps using TrendClipOne and re-run with -Purge."
        throw
      }
    }
  } else {
    Write-Log "Nothing to purge; $BASE does not exist."
  }
}

# Create fresh structure
Ensure-Dir $BASE; Ensure-Dir $ASSETS; Ensure-Dir $SECRETS; Ensure-Dir $SCRIPTS; Ensure-Dir $DIST; Ensure-Dir $LOGS
$script:LogFile = Join-Path $LOGS 'install.log'
Write-Log "TrendClip Desktop v$Version — Installing to $BASE"

# Enhanced dependency checking and installation
Write-Log "=== ENHANCED TRENDCLIP INSTALLATION ==="

# Check dependencies first
$deps = Test-Dependencies
if ($deps.Issues.Count -gt 0) {
  Write-Log "Missing dependencies detected: $($deps.Issues -join ', ')"
  Write-Log "Attempting to install missing dependencies..."
  
  # Install missing dependencies
  foreach ($issue in $deps.Issues) {
    switch ($issue) {
      "Python 3.8+ not found" {
        Write-Log "Python not found. Please install Python 3.8+ manually from https://python.org/"
        throw "Python 3.8+ required but not found"
      }
      "FFmpeg not found" {
        Write-Log "FFmpeg not found. Will attempt to install portable version..."
      }
      "pip not available" {
        Write-Log "pip not available. Will attempt to upgrade..."
      }
    }
  }
}

# Install TrendClip tools (FFmpeg, yt-dlp)
Install-TrendClipTools

# Version & env
Write-TextFileUtf8 -Path (Join-Path $BASE 'VERSION') -Content $Version
$port = Get-FreePort -Start 8700 -End 8999
$env:TRENDCLIP_PORT = "$port"
$env:TRENDCLIP_BIND = '127.0.0.1'
$env:TRENDCLIP_BASE = $BASE
Write-Log "Selected port: $env:TRENDCLIP_PORT"

# requirements.txt
$requirements = @'
dash>=2.16
plotly>=5.22
requests>=2.32
pandas>=2.2
PyYAML>=6.0
tenacity>=8.3
google-api-python-client>=2.153
google-auth>=2.33
google-auth-oauthlib>=1.2
google-auth-httplib2>=0.2
moviepy>=1.0.3
pywebview>=4.4
yt-dlp>=2025.1.1
'@
Write-TextFileUtf8 -Path (Join-Path $BASE 'requirements.txt') -Content $requirements

# config.yaml
$config = @"
version: $Version
currency: GBP
app:
  port_env: TRENDCLIP_PORT
  bind_env: TRENDCLIP_BIND
  open_browser: false
paths:
  base: .
  assets: assets
  secrets: .secrets
  dist: dist
  logs: logs
youtube:
  scopes:
    - https://www.googleapis.com/auth/youtube.upload
  default_privacy: private
  add_shorts_hashtag: true
keys:
  prefer_env: true
"@
Write-TextFileUtf8 -Path (Join-Path $BASE 'config.yaml') -Content $config

# CSS
$css = @'
:root { --gap: 12px; --radius: 14px; }
body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; background:#0b0f17; color:#e8eef9; }
.container { max-width: 1200px; margin: auto; padding: 24px; }
.card { background:#121826; padding:16px; border-radius:var(--radius); box-shadow:0 2px 24px rgba(0,0,0,.25); }
button, .btn { border:none; border-radius:12px; padding:10px 14px; font-weight:600; cursor:pointer; }
.link { color:#8cc6ff; text-decoration:none; }
pre { background:#0d1320; border-radius:12px; padding:12px; overflow:auto; }
input, select, textarea { background:#0d1320; color:#e8eef9; border:1px solid #1e293b; border-radius:10px; padding:10px; width:100%; }
.grid { display:grid; gap:var(--gap); }
.grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
@media (max-width:900px){ .grid-2,.grid-3{ grid-template-columns: 1fr; } }
'@
Write-TextFileUtf8 -Path (Join-Path $ASSETS 'style.css') -Content $css

# venv / Python
$VENV_PY = $null
if ($UseSystemPython) {
  Write-Log 'Using system Python (no venv).'
  if (Get-Command py -ErrorAction SilentlyContinue) { $VENV_PY = (& py -3 -c "import sys; print(sys.executable)").Trim() }
  elseif (Get-Command python -ErrorAction SilentlyContinue) { $VENV_PY = (Get-Command python).Source }
  else { throw 'Python not found. Install Python 3.x and re-run.' }
} else {
  $pythonCmd = if (Get-Command py -ErrorAction SilentlyContinue) { 'py -3' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { throw 'Python not found. Install Python 3.x and re-run.' }
  if ($Reinstall -and (Test-Path -LiteralPath $VENV)) { Write-Log 'Removing existing venv...'; Remove-Item -Recurse -Force $VENV }
  if (-not (Test-Path -LiteralPath $VENV)) { iex "$pythonCmd -m venv `"$VENV`"" }
  $VENV_PY = Join-Path $VENV 'Scripts\python.exe'
}
$env:TRENDCLIP_VENV_PY = $VENV_PY
Write-Log "Python: $VENV_PY"

# Run comprehensive requirements test
$testResults = Test-TrendClipRequirements
if ($testResults.Overall -eq "FAIL") {
  Write-Log "[ERROR] Critical requirements test failed. Please check the errors above."
  Write-Log "Errors: $($testResults.Errors -join '; ')"
  throw "Requirements test failed"
}

if ($testResults.Warnings.Count -gt 0) {
  Write-Log "[WARN] Some warnings detected but continuing: $($testResults.Warnings -join '; ')"
}

# Create shortcuts
Create-TrendClipShortcuts

# pip & deps
& $VENV_PY -m pip install --upgrade pip
if ($RebuildDash) { & $VENV_PY -m pip install --upgrade --force-reinstall dash plotly pywebview yt-dlp }
& $VENV_PY -m pip install -r (Join-Path $BASE 'requirements.txt')

# Pack only?
if ($Pack) {
  Write-Log 'Creating distributable ZIP (headless)'
  $packPy = @'
import os, pathlib, zipfile, datetime, shutil
BASE = pathlib.Path(os.environ.get("TRENDCLIP_BASE") or pathlib.Path.cwd())
DIST = BASE / "dist"; DIST.mkdir(parents=True, exist_ok=True)
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
zip_path = DIST / f"TrendClipDesktop_{ts}.zip"
include = ["TrendClipDesktop.py","TrendClipDashboard_Standalone.py","wizard.py","video_helpers.py","youtube_uploader.py","autopilot.py","jobs.py","requirements.txt","config.yaml","assets","data"]
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for item in include:
        p = BASE / item
        if p.is_dir():
            for root, _, files in os.walk(p):
                for f in files:
                    fp = pathlib.Path(root) / f
                    z.write(fp, fp.relative_to(BASE))
        elif p.exists():
            z.write(p, p.relative_to(BASE))
try:
    desktop = pathlib.Path.home() / "Desktop"
    shutil.copy2(zip_path, desktop)
except Exception:
    pass
print(zip_path)
'@
  $tmp = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), 'trendclip_pack.py')
  [System.IO.File]::WriteAllText($tmp, $packPy, [System.Text.UTF8Encoding]::new($false))
  & $VENV_PY $tmp
  Remove-Item $tmp -Force -ErrorAction SilentlyContinue
  Write-Log 'ZIP created.'
  return
}

# Launch desktop app
Write-Log "Launching TrendClip Desktop (no external browser) on http://$($env:TRENDCLIP_BIND):$($env:TRENDCLIP_PORT)/"
if ($Detached) {
  Start-Process -FilePath $VENV_PY -ArgumentList (Join-Path $BASE 'TrendClipDesktop.py') -WorkingDirectory $BASE | Out-Null
  Write-Log "Started in background."
} else {
  & $VENV_PY (Join-Path $BASE 'TrendClipDesktop.py')
}

# Optional wizard
if ($RunWizard) {
  $launchWizard = @'
param([string]$Base)
$py = Join-Path $Base ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "py -3" }
Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", "$py `"$Base\wizard.py`"") -WorkingDirectory $Base
'@
  Write-TextFileUtf8 -Path (Join-Path $SCRIPTS 'launch_wizard.ps1') -Content $launchWizard
  Start-Process powershell -ArgumentList @('-NoExit','-ExecutionPolicy','Bypass','-File', (Join-Path $SCRIPTS 'launch_wizard.ps1'), '-Base', $BASE)
}
