# PowerShell script to build the executable

Write-Host "Building Modeling GUI Executable..." -ForegroundColor Green
Write-Host ""

# Check if PyInstaller is installed
Write-Host "Checking for PyInstaller..." -ForegroundColor Yellow
$pyinstallerInstalled = python -m pip show pyinstaller 2>$null
if (-not $pyinstallerInstalled) {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Yellow
    python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install PyInstaller" -ForegroundColor Red
        exit 1
    }
}
Write-Host "PyInstaller is ready!" -ForegroundColor Green
Write-Host ""

# Clean previous builds
Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
}
Write-Host "Clean complete!" -ForegroundColor Green
Write-Host ""

# Build the executable using the spec file
Write-Host "Building executable with PyInstaller..." -ForegroundColor Yellow
Write-Host ""
pyinstaller drag_drop.spec --clean

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Build completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your executable is located at:" -ForegroundColor Cyan
    Write-Host "  dist\ModelingGUI.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You can now run the application by double-clicking the .exe file" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Build failed. Please check the errors above." -ForegroundColor Red
    exit 1
}
