# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os
from pathlib import Path

block_cipher = None

# Get the base directory
base_dir = Path(SPECPATH)

# Collect all data files
datas = [
    # Image files
    (str(base_dir / 'img'), 'img'),
    # YAML configuration files
    (str(base_dir / 'debuffer_placeholder_config.yml'), '.'),
    (str(base_dir / 'finetune_workflow.yml'), '.'),
    (str(base_dir / 'gdal_update_geotrans_config.yml'), '.'),
    (str(base_dir / 'wait_script_config.yml'), '.'),
    # Additional Python scripts that are called by subprocess
    (str(base_dir / 'debuffer_placeholder.py'), '.'),
    (str(base_dir / 'gdal_update_geotrans.py'), '.'),
    (str(base_dir / 'wait_script.py'), '.'),
    # JSON file
    (str(base_dir / 'run_history.json'), '.'),
]

# Collect CustomTkinter data files
datas += collect_data_files('customtkinter')

# Hidden imports for packages that PyInstaller might miss
hiddenimports = [
    'PIL._tkinter_finder',
    'tkinterdnd2',
    'customtkinter',
    'yaml',
]

# Collect all submodules for customtkinter
hiddenimports += collect_submodules('customtkinter')

a = Analysis(
    ['drag_drop.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ModelingGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(base_dir / 'img' / 'nv5.ico'),
)
