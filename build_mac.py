#!/usr/bin/env python3
"""
PyInstaller build script for Tabula Rasa on Mac Silicon
"""

import os
import sys
import subprocess
import shutil

def main():
    # Check if we're on Mac
    if sys.platform != "darwin":
        print("This build script is for macOS only!")
        sys.exit(1)
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Clean previous builds
    for dir_name in ["build", "dist"]:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Cleaned {dir_name} directory")
    
    # PyInstaller command for Mac Silicon
    pyinstaller_args = [
        "pyinstaller",
        "--windowed",  # No console window
        "--name=Tabula Rasa",  # App name
        "--icon=TabulaRasa.icns",  # App icon
        "--add-data=assets:assets",  # Include assets folder
        "--add-data=resource_path.py:.",  # Include resource path helper
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui", 
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageQt",
        "--osx-bundle-identifier=com.tabularasa.app",  # Bundle ID
        "Tabula_rasa.py"
    ]
    
    print("Building Tabula Rasa for Mac Silicon...")
    print(f"Command: {' '.join(pyinstaller_args)}")
    
    # Run PyInstaller
    try:
        subprocess.check_call(pyinstaller_args)
        print("\n✅ Build successful!")
        print(f"Executable created in: {os.path.abspath('dist/Tabula Rasa.app')}")
        
        # Additional checks
        app_path = "dist/Tabula Rasa.app"
        if os.path.exists(app_path):
            size_mb = shutil.disk_usage(app_path).free / (1024 * 1024)
            print(f"App bundle size: ~{size_mb:.1f} MB")
            
            # Check if assets are included
            assets_path = f"{app_path}/Contents/Resources/assets"
            if os.path.exists(assets_path):
                asset_count = len(os.listdir(assets_path))
                print(f"Assets included: {asset_count} files")
            else:
                print("⚠️  Warning: Assets folder not found in bundle")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)
    
    print("\nTo run the app:")
    print("  open 'dist/Tabula Rasa.app'")
    print("\nTo install the app:")
    print("  Copy 'dist/Tabula Rasa.app' to /Applications/")

if __name__ == "__main__":
    main()
