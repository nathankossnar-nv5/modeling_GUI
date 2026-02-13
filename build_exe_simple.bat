@echo off
REM Simple batch script to build the executable

echo Building Modeling GUI Executable...
echo.

REM Check if PyInstaller is installed
echo Checking for PyInstaller...
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
    if %errorlevel% neq 0 (
        echo Failed to install PyInstaller
        pause
        exit /b 1
    )
)
echo PyInstaller is ready!
echo.

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo Clean complete!
echo.

REM Build the executable
echo Building executable with PyInstaller...
echo.
pyinstaller drag_drop.spec --clean

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Build completed successfully!
    echo ========================================
    echo.
    echo Your application folder is located at:
    echo   dist\ModelingGUI\
    echo.
    echo The folder contains:
    echo   - ModelingGUI.exe (your GUI application)
    echo   - python.exe (bundled Python interpreter)
    echo   - All required dependencies
    echo.
    echo TO DISTRIBUTE:
    echo   1. Zip the entire "dist\ModelingGUI" folder
    echo   2. Send to users
    echo   3. Users extract and run ModelingGUI.exe
    echo.
    echo The application is fully self-contained with bundled Python!
) else (
    echo.
    echo Build failed. Please check the errors above.
)

echo.
pause
