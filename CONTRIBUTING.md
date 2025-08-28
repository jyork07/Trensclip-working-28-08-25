# Contributing to TrendClip Desktop

Thank you for your interest in contributing to TrendClip Desktop! This document provides guidelines and instructions for contributors.

## 🚀 Quick Start

### Prerequisites
- Windows 10/11
- PowerShell 5.1+ or PowerShell Core 7+
- Git
- Python 3.8+ (optional - script can install)

### Development Setup

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/yourusername/TrendClip.git
   cd TrendClip
   ```

2. **Install for development**:
   ```powershell
   # Use system Python for development
   .\Install_TrendClip_Desktop.ps1 -UseSystemPython
   
   # Or rebuild components
   .\Install_TrendClip_Desktop.ps1 -RebuildDash
   ```

3. **Run in development mode**:
   ```powershell
   .\Install_TrendClip_Desktop.ps1 -Detached
   ```

## 🛠️ Development Guidelines

### Code Style

#### PowerShell
- Use **PascalCase** for function names: `Test-Dependencies`
- Use **camelCase** for variables: `$basePath`
- Use **UPPER_CASE** for constants: `$VERSION`
- Add comprehensive error handling with `try/catch`
- Use `Write-Log` for all output
- Include parameter validation

#### Python
- Follow PEP 8 style guidelines
- Use **snake_case** for functions and variables
- Use **PascalCase** for classes
- Add type hints where appropriate
- Include docstrings for all functions

### Error Handling

#### PowerShell Functions
```powershell
function Test-Example {
    param([string]$Path)
    
    try {
        if (-not (Test-Path $Path)) {
            throw "Path not found: $Path"
        }
        
        Write-Log "[OK] Path validated: $Path"
        return $true
    }
    catch {
        Write-Log "[ERROR] Test-Example failed: $($_.Exception.Message)"
        return $false
    }
}
```

#### Python Functions
```python
import logging
from typing import Optional

def test_example(path: str) -> bool:
    """
    Test if a path exists and is accessible.
    
    Args:
        path: Path to test
        
    Returns:
        True if path is valid, False otherwise
    """
    try:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path not found: {path}")
            
        logging.info(f"Path validated: {path}")
        return True
    except Exception as e:
        logging.error(f"test_example failed: {e}")
        return False
```

### Testing

#### PowerShell Testing
- Test on clean Windows installations
- Verify dependency detection and installation
- Test error scenarios and recovery
- Validate file operations and permissions

#### Python Testing
- Unit tests for core functions
- Integration tests for video processing
- Mock external dependencies (YouTube API, etc.)
- Test configuration loading and validation

### Documentation

#### Code Documentation
- Add comments for complex logic
- Document function parameters and return values
- Include usage examples
- Update README.md for new features

#### User Documentation
- Update installation instructions
- Document new command-line options
- Add troubleshooting guides
- Include screenshots for UI changes

## 🔧 Development Workflow

### 1. Feature Development

1. **Create a feature branch**:
   ```powershell
   git checkout -b feature/new-feature-name
   ```

2. **Make your changes**:
   - Follow coding guidelines
   - Add comprehensive error handling
   - Include logging for debugging

3. **Test thoroughly**:
   - Test on clean Windows installation
   - Verify all error scenarios
   - Test with different Python versions

4. **Update documentation**:
   - Update README.md if needed
   - Add to CHANGELOG.md
   - Update DESIGN.md for architectural changes

### 2. Testing Checklist

#### Installation Testing
- [ ] Clean Windows 10/11 installation
- [ ] No Python pre-installed
- [ ] Different PowerShell versions
- [ ] Various Windows editions (Home, Pro, Enterprise)

#### Functionality Testing
- [ ] Dependency detection and installation
- [ ] Video download and processing
- [ ] YouTube upload (if applicable)
- [ ] Error handling and recovery
- [ ] Configuration management

#### Performance Testing
- [ ] Large video files
- [ ] Multiple concurrent downloads
- [ ] Memory usage monitoring
- [ ] Disk space handling

### 3. Pull Request Process

1. **Prepare your PR**:
   - Clear, descriptive title
   - Detailed description of changes
   - Link to related issues
   - Include testing results

2. **Code Review**:
   - Address reviewer feedback
   - Ensure all tests pass
   - Update documentation as needed

3. **Merge**:
   - Squash commits if appropriate
   - Update version numbers
   - Tag releases

## 🐛 Bug Reports

### Reporting Issues

When reporting bugs, please include:

1. **Environment Details**:
   - Windows version and edition
   - PowerShell version
   - Python version (if applicable)
   - Available disk space and RAM

2. **Steps to Reproduce**:
   - Exact commands run
   - Input files or URLs
   - Expected vs actual behavior

3. **Logs and Error Messages**:
   - Full error output
   - Log files from `%USERPROFILE%\TrendClipOne\logs\`
   - Screenshots if UI-related

4. **Additional Context**:
   - When the issue started
   - Recent changes to system
   - Antivirus software

### Issue Templates

Use the provided issue templates:
- **Bug Report**: For unexpected behavior
- **Feature Request**: For new functionality
- **Documentation**: For documentation improvements

## 🚀 Feature Requests

### Suggesting Features

When suggesting new features:

1. **Describe the problem**:
   - What are you trying to accomplish?
   - What's currently difficult or impossible?

2. **Propose a solution**:
   - How should it work?
   - What would the user experience be?

3. **Consider implementation**:
   - Is it within the project scope?
   - What dependencies would it require?
   - How would it integrate with existing features?

### Feature Development

If you want to implement a feature:

1. **Discuss first**: Open an issue to discuss the approach
2. **Design**: Consider the architecture and user experience
3. **Implement**: Follow the development guidelines
4. **Test**: Ensure it works in various scenarios
5. **Document**: Update all relevant documentation

## 📋 Development Environment

### Recommended Tools

- **VS Code**: With PowerShell and Python extensions
- **Git**: For version control
- **PowerShell ISE**: For PowerShell development
- **Python IDLE**: For Python development

### Useful Commands

```powershell
# Check PowerShell version
$PSVersionTable.PSVersion

# Test execution policy
Get-ExecutionPolicy

# Check Python installation
python --version

# Verify Git setup
git --version

# Test TrendClip installation
.\Install_TrendClip_Desktop.ps1 -CheckDeps
```

### Debugging Tips

#### PowerShell Debugging
```powershell
# Enable verbose output
$VerbosePreference = "Continue"

# Set breakpoints
Set-PSBreakpoint -Script Install_TrendClip_Desktop.ps1 -Line 100

# Debug specific function
Debug-Function -Name Test-Dependencies
```

#### Python Debugging
```python
import logging
import pdb

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Set breakpoint
pdb.set_trace()

# Use logging for debugging
logging.debug(f"Variable value: {variable}")
```

## 🏗️ Architecture Guidelines

### Module Design

- **Single Responsibility**: Each module should have one clear purpose
- **Loose Coupling**: Minimize dependencies between modules
- **High Cohesion**: Related functionality should be grouped together
- **Error Isolation**: Errors in one module shouldn't crash others

### Configuration Management

- **Environment Variables**: Prefer over file-based secrets
- **Validation**: Always validate configuration values
- **Defaults**: Provide sensible defaults for all settings
- **Documentation**: Document all configuration options

### Logging Strategy

- **Structured Logging**: Use consistent log formats
- **Log Levels**: Use appropriate levels (DEBUG, INFO, WARN, ERROR)
- **Rotation**: Implement log rotation to manage disk space
- **Security**: Never log sensitive information

## 📚 Resources

### Documentation
- [PowerShell Documentation](https://docs.microsoft.com/en-us/powershell/)
- [Python Documentation](https://docs.python.org/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)

### Best Practices
- [PowerShell Best Practices](https://docs.microsoft.com/en-us/powershell/scripting/developer/cmdlet/strongly-encouraged-development-guidelines)
- [Python Best Practices](https://docs.python-guide.org/)
- [Git Best Practices](https://git-scm.com/book/en/v2)

### Community
- [GitHub Issues](https://github.com/yourusername/TrendClip/issues)
- [Discussions](https://github.com/yourusername/TrendClip/discussions)
- [Wiki](https://github.com/yourusername/TrendClip/wiki)

## 📄 License

By contributing to TrendClip Desktop, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to TrendClip Desktop! Your help makes this project better for everyone.
