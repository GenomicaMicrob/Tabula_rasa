# Build Guide for Tabula Rasa

## Mac Silicon (Apple Silicon) Build

### Prerequisites
- macOS 11.0+ (Big Sur or later)
- Python 3.9+ (installed via Homebrew recommended)
- Xcode Command Line Tools

### Installation Steps

1. **Install Python (if not already installed):**
   ```bash
   brew install python@3.11
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements_build.txt
   ```

4. **Build the application:**
   ```bash
   python build_mac.py
   ```

   Or use PyInstaller directly:
   ```bash
   pyinstaller Tabula_rasa.spec
   ```

### Build Output
- The built app will be located at: `dist/Tabula Rasa.app`
- Size: Approximately 50-80 MB
- Self-contained executable (no Python installation required)

### Testing the Build
1. Run the app directly:
   ```bash
   open "dist/Tabula Rasa.app"
   ```

2. Test all features:
   - Drawing tools
   - File operations
   - Zoom and pan
   - All assets load correctly

### Distribution
1. **Create a DMG (optional):**
   ```bash
   # Create a DMG for distribution
   hdiutil create -volname "Tabula Rasa" -srcfolder dist/Tabula\ Rasa.app -ov -format UDZO TabulaRasa.dmg
   ```

2. **Code Signing (for distribution):**
   ```bash
   # If you have a Developer ID
   codesign --force --verify --verbose --sign "Developer ID Application: Your Name" "dist/Tabula Rasa.app"
   ```

## Windows Build

### Prerequisites
- Windows 10/11
- Python 3.9+
- Microsoft Visual C++ Redistributable

### Build Steps
1. Install dependencies:
   ```cmd
   pip install -r requirements_build.txt
   ```

2. Build using PyInstaller:
   ```cmd
   pyinstaller --onefile --windowed --icon=assets\TabulaRasa.ico --add-data="assets;assets" Tabula_rasa.py
   ```

## Linux Ubuntu Build

### Prerequisites
- Ubuntu 20.04+
- Python 3.9+
- GTK development libraries

### Build Steps
1. Install system dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install python3-dev python3-pip python3-setuptools
   sudo apt-get install libqt6gui6 libqt6widgets6 libqt6core6
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements_build.txt
   ```

3. Build the application:
   ```bash
   pyinstaller --onefile --windowed --icon=assets/TabulaRasa.png --add-data="assets:assets" Tabula_rasa.py
   ```

## Troubleshooting

### Common Issues

1. **Assets not found:**
   - Ensure the `assets` folder is in the same directory as the executable
   - Check that all SVG files are present

2. **PyQt6 import errors:**
   - Install PyQt6 with: `pip install PyQt6==6.5.2`
   - For Mac Silicon, ensure you're using ARM64 Python

3. **Permission denied on Mac:**
   - Right-click the app and select "Open"
   - Go to System Preferences > Security & Privacy and allow the app

4. **Large file size:**
   - The size is normal for PyQt6 applications
   - UPX compression is enabled by default

### Performance Tips
- The app may take a few seconds to launch on first run
- Subsequent launches are faster
- Memory usage is typically 50-100 MB

## Version Information
- Current Version: 1.0.0
- Build Date: 2024
- Supported Platforms: macOS (Apple Silicon), Windows 10/11, Ubuntu 20.04+
