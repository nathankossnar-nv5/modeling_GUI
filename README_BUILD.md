# Building the Modeling GUI Executable

This document explains how to package the Modeling GUI application into a standalone `.exe` file.

## Prerequisites

- Python installed (with all dependencies from your project)
- PyInstaller (will be installed automatically if missing)

## Build Methods

### Method 1: Using PowerShell Script (Recommended)

Simply run the PowerShell script:

```powershell
.\build_exe.ps1
```

### Method 2: Using Batch File

Double-click `build_exe_simple.bat` or run from command prompt:

```cmd
build_exe_simple.bat
```

### Method 3: Manual PyInstaller Command

If you prefer to run PyInstaller manually:

```powershell
# Install PyInstaller if needed
pip install pyinstaller

# Build using the spec file
pyinstaller drag_drop.spec --clean
```

## Output

After building, you'll find:
- **Executable**: `dist\ModelingGUI.exe`
- **Build files**: `build\` folder (can be deleted)

## What's Included

The `.exe` file includes:
- The main GUI application (`drag_drop.py`)
- All helper scripts:
  - `debuffer_placeholder.py`
  - `gdal_update_geotrans.py`
  - `wait_script.py`
- All configuration files (`.yml` files)
- Images and logos (`img/` folder)
- All Python dependencies (customtkinter, tkinterdnd2, PyYAML, Pillow, etc.)

## Configuration Files Location

When running as an executable, configuration files and run history are stored in:
- **Windows**: `%APPDATA%\ModelingGUI\`
  - Typically: `C:\Users\<YourUsername>\AppData\Roaming\ModelingGUI\`

This allows the application to save your settings and history between runs. The bundled config files are automatically copied here on first run.

## Distribution

To distribute the application:
1. Copy `dist\ModelingGUI.exe` to any Windows computer
2. The executable is standalone and doesn't require Python to be installed
3. Users can simply double-click the `.exe` to run the application

## Customization

### Adding an Icon

To add a custom icon to your executable:

1. Create or obtain an `.ico` file
2. Edit `drag_drop.spec` and change the line:
   ```python
   icon=None,
   ```
   to:
   ```python
   icon='path/to/your/icon.ico',
   ```
3. Rebuild the executable

### Showing Console Window (for debugging)

If you want to see console output for debugging:

1. Edit `drag_drop.spec` and change:
   ```python
   console=False,
   ```
   to:
   ```python
   console=True,
   ```
2. Rebuild the executable

## Troubleshooting

### Build Fails

- Ensure all dependencies are installed: `pip install -r requirements.txt` (if you have one)
- Check that all files referenced in the spec file exist
- Look at the error messages for missing modules and add them to `hiddenimports`

### Executable Won't Run

- Try building with `console=True` to see error messages
- Ensure all data files (images, configs) are in the correct locations
- Check that the conda environments referenced in your app are available on the target machine

### Large File Size

The executable may be 100-200MB due to included libraries. This is normal for Python GUI applications.

To reduce size:
- Remove unused dependencies
- Use `upx=True` in the spec file (already enabled)
- Consider using a directory-based build instead of `--onefile`

## Notes for Conda Environments

**Important**: The executable will still need access to conda environments if your scripts use them. The GUI uses `subprocess` to call conda, so:
- Conda must be installed on the target machine
- The required conda environments must exist
- Alternatively, modify the app to use embedded Python interpreters

## Building for Multiple Platforms

PyInstaller creates platform-specific executables:
- Build on Windows → get a `.exe` file
- Build on macOS → get a `.app` bundle
- Build on Linux → get a Linux executable

You must build on each target platform separately.
