# PyInstaller Build Checklist for Tabula Rasa

## ✅ Pre-Build Requirements

### Code Structure
- [x] Single entry point (Tabula_rasa.py)
- [x] Proper `if __name__ == "__main__":` block
- [x] Resource path handling implemented
- [x] All imports at top level
- [x] No dynamic imports that might be missed

### Dependencies
- [x] PyQt6==6.5.2 (stable version)
- [x] Pillow==10.0.0 (stable version)
- [x] PyInstaller>=6.0.0 (latest)

### Assets
- [x] All SVG files present in assets folder
- [x] Icon file (TabulaRasa.icns) for Mac
- [x] Assets properly referenced with resource_path()

## ✅ Build Configuration

### PyInstaller Options
- [x] `--onefile` for single executable
- [x] `--windowed` for GUI app (no console)
- [x] `--icon` specified for Mac
- [x] `--add-data` for assets folder
- [x] Hidden imports for PyQt6 modules
- [x] Bundle identifier set

### Mac Specific
- [x] ARM64 (Apple Silicon) compatible
- [x] Info.plist configured
- [x] Document types registered
- [x] High DPI support enabled

## ✅ Testing Checklist

### Functional Testing
- [ ] App launches without errors
- [ ] All drawing tools work
- [ ] File operations (open/save) work
- [ ] Assets (icons) load correctly
- [ ] Zoom and pan functionality works
- [ ] Undo/Redo works
- [ ] Color picker works
- [ ] Brush size adjustment works

### Platform Testing
- [ ] Tested on macOS (Apple Silicon)
- [ ] App icon displays correctly
- [ ] Dock icon shows correctly
- [ ] File associations work (optional)
- [ ] Permissions work correctly

### Performance
- [ ] Startup time acceptable (<5 seconds)
- [ ] Memory usage reasonable (<200MB)
- [ ] No memory leaks during extended use
- [ ] Responsive UI during drawing

## ✅ Distribution Preparation

### Code Signing (Optional)
- [ ] Developer certificate installed
- [ ] App signed with codesign
- [ ] Notarization for App Store (if needed)

### DMG Creation (Optional)
- [ ] DMG created with proper layout
- [ ] Background image added (optional)
- [ ] License file included
- [ ] EULA included (if needed)

## ⚠️ Known Issues & Solutions

### Issue: Assets not found in bundled app
**Solution**: Use resource_path() helper function

### Issue: PyQt6 import errors
**Solution**: Add hidden imports for PyQt6 modules

### Issue: Large app size
**Solution**: Expected for PyQt6 apps (~50-80MB)

### Issue: Slow startup on first run
**Solution**: Normal behavior, subsequent launches faster

## 🚀 Build Commands

### Development Build
```bash
python build_mac.py
```

### Direct PyInstaller
```bash
pyinstaller Tabula_rasa.spec
```

### Clean Build
```bash
rm -rf build dist
python build_mac.py
```

## 📦 Output Files

After successful build:
- `dist/Tabula Rasa.app` - Main application bundle
- `dist/Tabula Rasa.app/Contents/MacOS/Tabula Rasa` - Executable
- `dist/Tabula Rasa.app/Contents/Resources/assets` - Bundled assets

## 🔍 Debug Tips

If build fails:
1. Check PyInstaller version: `pyinstaller --version`
2. Verify all imports work in Python
3. Test with `--debug` flag: `pyinstaller --debug all Tabula_rasa.py`
4. Check the `.spec` file for missing datas

If app doesn't run:
1. Check Console.app for error messages
2. Run from terminal: `"dist/Tabula Rasa.app/Contents/MacOS/Tabula Rasa"`
3. Verify assets are in the bundle

## 📋 Final Verification

Before distribution:
- [ ] Build on clean machine
- [ ] Test on multiple macOS versions
- [ ] Verify all features work
- [ ] Check file size is reasonable
- [ ] Test installation process
