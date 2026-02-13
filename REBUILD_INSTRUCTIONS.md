# IMPORTANT: Rebuild Required for Bundled Python Mode

## Current Issue

If you're seeing this error when using "Bundled Python" mode:
```
Python was not found; run without arguments to install from the Microsoft Store...
Script exited with error code 9009
```

This means the exe was built in **onefile mode** which doesn't include a usable Python interpreter for running external scripts.

## Solution: Rebuild in Onedir Mode

The `drag_drop.spec` file has already been updated to use **onedir mode**. You just need to rebuild:

### Step 1: Clean Previous Build
```powershell
# Remove old build artifacts
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
```

### Step 2: Activate Your Environment
```powershell
# Activate your conda environment with all dependencies
conda activate your_env_name

# Verify Python version (should be 3.x)
python --version
```

### Step 3: Install Dependencies (if needed)
```powershell
# Make sure all packages your scripts need are installed
conda install customtkinter tkinterdnd2 pillow pyyaml
# Add any other packages your scripts use
```

### Step 4: Rebuild
```powershell
# Build using the updated spec file
pyinstaller drag_drop.spec
```

### Step 5: Test
```powershell
# The output will be in: dist/ModelingGUI/
cd dist\ModelingGUI
.\ModelingGUI.exe

# Verify python.exe exists in the same folder as ModelingGUI.exe
ls python.exe
```

## What You'll Get

After rebuilding in onedir mode:

```
dist/
└── ModelingGUI/              ← Distribute this entire folder
    ├── ModelingGUI.exe       ← Your GUI application
    ├── python.exe            ← Bundled Python interpreter (NEW!)
    ├── python311.dll         ← Python runtime
    ├── _internal/            ← All packages and dependencies
    │   ├── customtkinter/
    │   ├── PIL/
    │   ├── yaml/
    │   └── ...
    └── ... (other files)
```

## Distribution

**Important:** You must distribute the **entire ModelingGUI folder**, not just the .exe file!

1. Zip the entire `dist/ModelingGUI` folder
2. Send the zip to users
3. Users extract anywhere and run `ModelingGUI.exe`
4. "Bundled Python" mode will now work without requiring Python installation!

## File Size

The folder will be larger (typically 50-200MB depending on dependencies) but it will be truly self-contained and portable.

## Testing

To verify bundled Python mode works:
1. Run ModelingGUI.exe on a machine **without Python installed**
2. Select "Bundled Python" mode
3. Run a script - it should work without errors!

## Alternative: Use Conda Environment Mode

If you can't rebuild right now, users can:
1. Install Python 3.x or Miniconda on their system
2. Switch to "Conda Environment" mode in the GUI
3. Select their conda environment
4. Scripts will run using the system Python instead
