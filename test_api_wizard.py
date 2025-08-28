#!/usr/bin/env python3
"""
Test script for API Wizard functionality
"""

import os
import sys
from pathlib import Path

def test_api_wizard():
    """Test the API wizard functionality"""
    print("🧪 Testing API Wizard...")
    
    # Test imports
    try:
        from api_wizard import APIWizard
        print("✅ API Wizard import successful")
    except ImportError as e:
        print(f"❌ API Wizard import failed: {e}")
        return False
    
    # Test initialization
    try:
        base_path = os.environ.get('TRENDCLIP_BASE', os.path.expanduser('~/TrendClipOne'))
        wizard = APIWizard(base_path)
        print("✅ API Wizard initialization successful")
    except Exception as e:
        print(f"❌ API Wizard initialization failed: {e}")
        return False
    
    # Test environment variable check
    try:
        env_keys = wizard.check_environment_variables()
        print(f"✅ Environment check: {len(env_keys)} keys found")
    except Exception as e:
        print(f"❌ Environment check failed: {e}")
        return False
    
    # Test configuration
    try:
        config_settings = {
            'region': 'GB',
            'cpm_gbp': 3.5,
            'clip_duration': 60
        }
        success = wizard.update_config(config_settings)
        if success:
            print("✅ Configuration update successful")
        else:
            print("❌ Configuration update failed")
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    
    print("🎉 API Wizard test completed successfully!")
    return True

def test_dashboard():
    """Test the dashboard functionality"""
    print("\n🧪 Testing Dashboard...")
    
    # Test imports
    try:
        from TrendClipDashboard_Standalone import TrendClipDashboard
        print("✅ Dashboard import successful")
    except ImportError as e:
        print(f"❌ Dashboard import failed: {e}")
        return False
    
    # Test initialization
    try:
        dashboard = TrendClipDashboard()
        print("✅ Dashboard initialization successful")
    except Exception as e:
        print(f"❌ Dashboard initialization failed: {e}")
        return False
    
    print("🎉 Dashboard test completed successfully!")
    return True

def test_desktop():
    """Test the desktop launcher"""
    print("\n🧪 Testing Desktop Launcher...")
    
    # Test imports
    try:
        from TrendClipDesktop import TrendClipDesktop
        print("✅ Desktop launcher import successful")
    except ImportError as e:
        print(f"❌ Desktop launcher import failed: {e}")
        return False
    
    # Test initialization
    try:
        desktop = TrendClipDesktop()
        print("✅ Desktop launcher initialization successful")
    except Exception as e:
        print(f"❌ Desktop launcher initialization failed: {e}")
        return False
    
    print("🎉 Desktop launcher test completed successfully!")
    return True

def main():
    """Run all tests"""
    print("🚀 TrendClip Desktop - Component Tests")
    print("=" * 50)
    
    results = []
    
    # Test API Wizard
    results.append(test_api_wizard())
    
    # Test Dashboard
    results.append(test_dashboard())
    
    # Test Desktop Launcher
    results.append(test_desktop())
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! TrendClip Desktop is ready to use.")
        print("\nNext steps:")
        print("1. Run the main installer: .\\Install_TrendClip_Desktop.ps1")
        print("2. Use the API Setup tab in the dashboard to configure YouTube OAuth")
        print("3. Set up your API keys for full functionality")
    else:
        print("⚠️ Some tests failed. Please check the error messages above.")
        print("\nTroubleshooting:")
        print("1. Make sure all dependencies are installed")
        print("2. Check that Python modules are available")
        print("3. Verify the installation directory structure")

if __name__ == "__main__":
    main()
