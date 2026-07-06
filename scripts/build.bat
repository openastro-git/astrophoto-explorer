@echo off
cd /d "%~dp0.."
setlocal EnableDelayedExpansion
REM ===================================
REM Astrophoto Explorer - Windows Build Script
REM ===================================
REM Enhanced build script with best practices
REM Creates a portable Windows application with auto-updater support

echo.
echo ========================================
echo Astrophoto Explorer - Build Script
echo ========================================
echo.

REM Enable ANSI color codes on Windows 10+
for /f "tokens=4 delims=." %%i in ('ver') do set WIN_MAJOR=%%i
if %WIN_MAJOR% geq 10 (
    call :EnableANSI
    if errorlevel 1 goto :NoColor
) else (
    goto :NoColor
)

:AfterANSI
REM Define color codes for ANSI-enabled terminals
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"
goto :AfterColorFunctions

:EnableANSI
REM Try to enable ANSI support via PowerShell
powershell -Command "$host.UI.RawUI.OutputEncoding = [System.Text.Encoding]::UTF8; Write-Host 'ANSI Enabled'" >nul 2>&1
exit /b 0

:NoColor
REM Fallback for older Windows or when ANSI can't be enabled
set "RED="
set "GREEN="
set "YELLOW="
set "BLUE="
set "RESET="
echo [INFO] ANSI colors disabled - running in basic mode

:AfterColorFunctions

REM Color output function
call :ColorOutput "%BLUE%" "Cleaning up previous builds..." "%RESET%"

REM Set variables
set "BUILD_DIR=build"
set "DIST_DIR=%BUILD_DIR%\dist"
set "VENV_DIR=.venv"
set "UI_DIR=%BUILD_DIR%\ui"
set "FINAL_DIR=%BUILD_DIR%\AstrophotoExplorer"
set "VERSION=1.0.0"

REM Check for administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    call :ColorOutput "%YELLOW%" "Running with administrator privileges" "%RESET%"
)

REM Create clean build directory
call :ColorOutput "%BLUE%" "Cleaning up previous builds..." "%RESET%"
if exist "%BUILD_DIR%" (
    REM Preserve config.json and cache from previous build before wiping
    if exist "%BUILD_DIR%\AstrophotoExplorer\config.json" (
        copy "%BUILD_DIR%\AstrophotoExplorer\config.json" "%TEMP%\astrophoto_config_backup.json" >nul
        call :ColorOutput "%YELLOW%" "Backed up existing config.json" "%RESET%"
    )
    if exist "%BUILD_DIR%\AstrophotoExplorer\.cache\favorites.json" (
        copy "%BUILD_DIR%\AstrophotoExplorer\.cache\favorites.json" "%TEMP%\astrophoto_favorites_backup.json" >nul
        call :ColorOutput "%YELLOW%" "Backed up existing favorites.json" "%RESET%"
    )
    rmdir /s /q "%BUILD_DIR%" 2>nul
)
mkdir "%BUILD_DIR%" 2>nul
mkdir "%DIST_DIR%" 2>nul
mkdir "%UI_DIR%" 2>nul

REM Check Python 3.11+ installation
call :ColorOutput "%BLUE%" "Checking Python installation..." "%RESET%"
python --version >nul 2>&1
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Python is not installed or not in PATH" "%RESET%"
    call :ColorOutput "%YELLOW%" "Please install Python 3.11+ from https://python.org" "%RESET%"
    pause
    exit /b 1
)

python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Python 3.11+ is required" "%RESET%"
    call :ColorOutput "%YELLOW%" "Please install Python 3.11+ from https://python.org" "%RESET%"
    pause
    exit /b 1
)

REM Check Node.js 18+ installation
call :ColorOutput "%BLUE%" "Checking Node.js installation..." "%RESET%"
node --version >nul 2>&1
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Node.js is not installed or not in PATH" "%RESET%"
    call :ColorOutput "%YELLOW%" "Please install Node.js from https://nodejs.org" "%RESET%"
    pause
    exit /b 1
)

node -e "process.exit(parseInt(process.version.slice(1).split('.')[0]) >= 18 ? 0 : 1)" >nul 2>&1
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Node.js 18+ is required" "%RESET%"
    call :ColorOutput "%YELLOW%" "Please install Node.js from https://nodejs.org" "%RESET%"
    pause
    exit /b 1
)

echo.
if not exist "%VENV_DIR%" (
    call :ColorOutput "%GREEN%" "[1/6] Setting up Python virtual environment..." "%RESET%"
    REM Create virtual environment with pip cache optimization
    python -m venv "%VENV_DIR%" --copies
    if errorlevel 1 (
        call :ColorOutput "%RED%" "ERROR: Failed to create virtual environment" "%RESET%"
        pause
        exit /b 1
    )
) else (
    call :ColorOutput "%GREEN%" "[1/6] Reusing existing Python virtual environment in %VENV_DIR%..." "%RESET%"
)

call "%VENV_DIR%\Scripts\activate.bat"

REM Configure pip for better performance
python -m pip config set global.timeout 60 >nul 2>&1
python -m pip config set global.retries 3 >nul 2>&1
python -m pip config set install.use-pep517 true >nul 2>&1

REM Upgrade pip and wheel first
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Failed to upgrade pip and setuptools" "%RESET%"
    pause
    exit /b 1
)

echo.
call :ColorOutput "%GREEN%" "[2/6] Installing Python dependencies..." "%RESET%"
REM Install packages directly into the virtual environment using pip
python -m pip install fastapi "uvicorn[standard]" websockets astropy numpy pillow scipy pyongc tifffile pywebview
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Failed to install Python dependencies" "%RESET%"
    pause
    exit /b 1
)

echo.
call :ColorOutput "%GREEN%" "[3/6] Building React frontend..." "%RESET%"

REM Check if frontend directory exists
if not exist "frontend" (
    call :ColorOutput "%RED%" "ERROR: Frontend directory not found" "%RESET%"
    echo Current directory: %CD%
    dir
    pause
    exit /b 1
)

REM Check if package.json exists (it's in the root, not frontend)
if not exist "package.json" (
    call :ColorOutput "%RED%" "ERROR: package.json not found" "%RESET%"
    echo Looking for: %CD%\package.json
    dir
    pause
    exit /b 1
)

REM Check if node_modules exists, install if not
if not exist "node_modules" (
    call :ColorOutput "%BLUE%" "Installing Node.js dependencies..." "%RESET%"
    call npm install --cache frontend/.npm-cache
    if errorlevel 1 (
        call :ColorOutput "%RED%" "ERROR: Failed to install Node.js dependencies" "%RESET%"
        pause
        exit /b 1
    )
)

REM Build production React app with optimization
call :ColorOutput "%BLUE%" "Building React application..." "%RESET%"
call npm run build
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Failed to build React application" "%RESET%"
    pause
    exit /b 1
)

REM Wait a moment for file system to catch up
timeout /t 1 /nobreak >nul

REM Verify dist directory was created with multiple checks
set "DIST_FOUND=0"
for /l %%i in (1,1,5) do (
    if exist "dist" (
        set "DIST_FOUND=1"
        goto :DistFound
    )
    timeout /t 1 /nobreak >nul
)

:DistFound
if %DIST_FOUND%==0 (
    call :ColorOutput "%RED%" "ERROR: React build completed but dist directory not created after 5 seconds" "%RESET%"
    echo Current directory: %CD%
    dir
    cd ..
    pause
    exit /b 1
)

REM Check if dist directory has files
set "HAS_FILES=0"
dir /b "dist" 2>nul | findstr . >nul && set "HAS_FILES=1"

if %HAS_FILES%==0 (
    call :ColorOutput "%YELLOW%" "Warning: dist directory exists but appears to be empty" "%RESET%"
    dir dist
) else (
    call :ColorOutput "%GREEN%" "[OK] React build created dist directory with files" "%RESET%"
    REM Show build summary
    if exist "dist\index.html" (
        call :ColorOutput "%BLUE%" "Build output: index.html created" "%RESET%"
    )
)

REM Copy built UI to build directory
call :ColorOutput "%BLUE%" "Copying UI files to build directory..." "%RESET%"
if exist "%UI_DIR%" (
    rmdir /s /q "%UI_DIR%" 2>nul
)

REM Create destination directory first
mkdir "%UI_DIR%" 2>nul

REM Copy with verbose output for debugging
xcopy /E /I /Y /Q "dist\*" "%UI_DIR%\"
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Failed to copy UI files to build directory" "%RESET%"
    echo Source: %CD%\dist
    echo Destination: %UI_DIR%\
    pause
    exit /b 1
)

REM Verify the copy worked
if exist "%UI_DIR%\index.html" (
    call :ColorOutput "%GREEN%" "[OK] UI files successfully copied to build directory" "%RESET%"
    REM Count files for verification
    set "FILE_COUNT=0"
    for /f %%a in ('dir /b /a-d "%UI_DIR%" 2^>nul ^| find /c /v ""') do set "FILE_COUNT=%%a"
    call :ColorOutput "%BLUE%" "Copied %FILE_COUNT% files to %UI_DIR%" "%RESET%"
) else (
    call :ColorOutput "%RED%" "ERROR: UI files not found in build directory after copy" "%RESET%"
    echo Looking for: %UI_DIR%\index.html
    dir "%UI_DIR%" 2>nul || echo Directory not found
    pause
    exit /b 1
)

echo.
call :ColorOutput "%GREEN%" "[4/6] Copying standalone API script..." "%RESET%"
REM Copy the permanent standalone script
call :ColorOutput "%BLUE%" "Copying standalone_api.py to build directory..." "%RESET%"
copy "standalone_api.py" "%BUILD_DIR%\" >nul
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Failed to copy standalone_api.py" "%RESET%"
    pause
    exit /b 1
)

REM Copy backend files
if exist "backend" (
    xcopy /E /I /Y /Q "backend\*" "%BUILD_DIR%\backend\" >nul
    call :ColorOutput "%GREEN%" "[OK] Backend files copied to build directory" "%RESET%"
) else (
    call :ColorOutput "%RED%" "ERROR: Backend directory not found" "%RESET%"
    pause
    exit /b 1
)

REM Copy permanent PyInstaller configuration
call :ColorOutput "%BLUE%" "Copying PyInstaller configuration..." "%RESET%"
copy "standalone_api.spec" "%BUILD_DIR%\" >nul
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Failed to copy standalone_api.spec" "%RESET%"
    pause
    exit /b 1
)

REM Install PyInstaller if not present
call :ColorOutput "%BLUE%" "Installing PyInstaller..." "%RESET%"
python -m pip install pyinstaller
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Failed to install PyInstaller" "%RESET%"
    pause
    exit /b 1
)

REM Copy pyongc database into build directory so PyInstaller can bundle it
call :ColorOutput "%BLUE%" "Locating pyongc database..." "%RESET%"
for /f "delims=" %%p in ('python -c "import pyongc, os; print(os.path.dirname(pyongc.__file__))"') do set "PYONGC_DIR=%%p"
if exist "%PYONGC_DIR%\ongc.db" (
    mkdir "%BUILD_DIR%\pyongc_data" 2>nul
    copy "%PYONGC_DIR%\ongc.db" "%BUILD_DIR%\pyongc_data\" >nul
    call :ColorOutput "%GREEN%" "[OK] pyongc database found and staged" "%RESET%"
) else (
    call :ColorOutput "%RED%" "ERROR: pyongc ongc.db not found at %PYONGC_DIR%" "%RESET%"
    pause
    exit /b 1
)

REM Copy icon file if it exists
if exist "icon.ico" (
    copy "icon.ico" "%BUILD_DIR%\" >nul
    call :ColorOutput "%GREEN%" "[OK] Icon file found and staged" "%RESET%"
) else (
    call :ColorOutput "%YELLOW%" "Warning: icon.ico not found - executable will use default icon" "%RESET%"
)

REM Copy splash screen if it exists
if exist "splash_screen.png" (
    copy "splash_screen.png" "%BUILD_DIR%\" >nul
    call :ColorOutput "%GREEN%" "[OK] Splash screen image found and staged" "%RESET%"
) else (
    call :ColorOutput "%YELLOW%" "Warning: splash_screen.png not found" "%RESET%"
)

REM Run PyInstaller with optimizations
call :ColorOutput "%BLUE%" "Running PyInstaller with optimizations..." "%RESET%"
cd "%BUILD_DIR%"
pyinstaller standalone_api.spec --clean --noconfirm --log-level INFO
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: PyInstaller failed to create executable" "%RESET%"
    cd ..
    pause
    exit /b 1
)
cd ..

set "EXE_PATH=%BUILD_DIR%\dist\astrophoto-explorer.exe"
if not exist "!EXE_PATH!" (
    set "EXE_PATH=%BUILD_DIR%\dist\astrophoto-explorer\astrophoto-explorer.exe"
)
if not exist "!EXE_PATH!" (
    call :ColorOutput "%RED%" "ERROR: PyInstaller failed to create executable" "%RESET%"
    pause
    exit /b 1
)

call :ColorOutput "%GREEN%" "[OK] API executable created successfully" "%RESET%"

echo.
call :ColorOutput "%GREEN%" "[5/6] Creating final package..." "%RESET%"
REM Create the final directory structure - put everything in root
mkdir "%FINAL_DIR%" 2>nul

REM Copy API executable directly from PyInstaller output to final package
call :ColorOutput "%GREEN%" "[5/6] Creating final package..." "%RESET%"
python scripts/package_app.py
if errorlevel 1 (
    call :ColorOutput "%RED%" "ERROR: Failed to run package_app.py" "%RESET%"
    pause
    exit /b 1
)

echo.
call :ColorOutput "%GREEN%" "========================================" "%RESET%"
call :ColorOutput "%GREEN%" "Build completed successfully!" "%RESET%"
call :ColorOutput "%GREEN%" "========================================" "%RESET%"
echo.
call :ColorOutput "%BLUE%" "The standalone application is ready in:" "%RESET%"
call :ColorOutput "%YELLOW%" "%FINAL_DIR%" "%RESET%"
echo.
call :ColorOutput "%BLUE%" "To run the application:" "%RESET%"
call :ColorOutput "%YELLOW%" "1. Navigate to: %FINAL_DIR%" "%RESET%"
call :ColorOutput "%YELLOW%" "2. Double-click: start.bat" "%RESET%"
echo.
call :ColorOutput "%GREEN%" "✨ You can distribute this folder to other Windows machines!" "%RESET%"
call :ColorOutput "%GREEN%" "✨ The application is completely self-contained!" "%RESET%"
echo.
pause

REM Exit script
exit /b 0

:ColorOutput
REM Function to output colored text
REM Usage: call :ColorOutput "%COLOR%" "Text" "%RESET%"
if "%~2"=="" (
    echo.
) else (
    echo %~2
)
exit /b
