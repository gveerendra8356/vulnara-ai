# run_local.ps1 - One-stop local Appium test runner for vulnara-mobile
#
# Usage:
#   .\run_local.ps1                                          # run ALL tests
#   .\run_local.ps1 -Test test_authentication                # run ONE module
#   .\run_local.ps1 -Test test_authentication,test_navigation  # run MULTIPLE
#   .\run_local.ps1 -SkipBuild                               # skip APK build
#   .\run_local.ps1 -SkipBackend                             # skip backend start
#   .\run_local.ps1 -SkipAppium                              # skip Appium start
#
# Prerequisites (checked automatically):
#   - Python 3.x       python --version
#   - Flutter          flutter --version
#   - Node.js          node --version
#   - Appium 3.6.0     installed automatically if missing
#   - Android emulator Pixel_6 AVD started automatically if not running

param(
    [string] $Test        = "",
    [switch] $SkipBuild   = $false,
    [switch] $SkipBackend = $false,
    [switch] $SkipAppium  = $false
)

Set-StrictMode -Off
# Do NOT use Stop - PowerShell throws a terminating error whenever any native
# command (like adb) writes to stderr, even daemon startup messages.
$ErrorActionPreference = "Continue"

$Root    = Split-Path $PSScriptRoot -Parent
$BEDir   = Join-Path $Root "backend"
$AppDir  = Join-Path $Root "vulnara_mobile_scaffold"
$TestDir = $PSScriptRoot
$APKPath = Join-Path $AppDir "build\app\outputs\flutter-apk\app-debug.apk"

# Put Android SDK tools on PATH for this session.
# Hardcoded path is used as primary so this works even in a terminal that
# was opened before the permanent PATH change took effect.
$sdkRoot = "C:\Users\volap\AppData\Local\Android\Sdk"
if (-not (Test-Path $sdkRoot)) {
    # Fallback: try env var or username-derived path
    $sdkRoot = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } `
               else { "C:\Users\$env:USERNAME\AppData\Local\Android\Sdk" }
}
$env:ANDROID_HOME     = $sdkRoot
$env:ANDROID_SDK_ROOT = $sdkRoot
$platformTools = Join-Path $sdkRoot "platform-tools"
$emulatorBin   = Join-Path $sdkRoot "emulator"
foreach ($p in @($platformTools, $emulatorBin)) {
    if ((Test-Path $p) -and ($env:PATH -notlike "*$p*")) {
        $env:PATH = "$env:PATH;$p"
        Write-Host "    Added to PATH: $p" -ForegroundColor DarkGray
    }
}

function Write-Step { param($msg) Write-Host "" ; Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-OK   { param($msg) Write-Host "    OK: $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "    WARN: $msg" -ForegroundColor Yellow }
function Write-Fail {
    param($msg)
    Write-Host ""
    Write-Host "    FAIL: $msg" -ForegroundColor Red
    exit 1
}

# Run adb silently - suppresses daemon startup stderr that PowerShell
# would otherwise treat as a NativeCommandError even with 2>$null.
function Invoke-Adb {
    $out = & adb @args 2>&1
    return $out | Where-Object { $_ -notmatch "daemon not running|daemon started" }
}

# ---------------------------------------------------------------------------
# 0. Prerequisites
# ---------------------------------------------------------------------------
Write-Step "Checking prerequisites"

foreach ($cmd in @("python", "flutter", "node", "adb")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Fail "'$cmd' not found on PATH. Install it and open a new terminal."
    }
}
Write-OK "python, flutter, node, adb all found"

# ---------------------------------------------------------------------------
# Check / start emulator
# ---------------------------------------------------------------------------
$deviceList = Invoke-Adb devices
$runningEmu = $deviceList | Where-Object { $_ -match "emulator" -and $_ -match "device" }

if (-not $runningEmu) {
    Write-Warn "No running emulator - auto-starting Pixel_6 AVD"
    $emulatorExe = Join-Path $emulatorBin "emulator.exe"
    if (-not (Test-Path $emulatorExe)) {
        Write-Fail "emulator.exe not found at $emulatorExe"
    }
    Start-Process -FilePath $emulatorExe `
        -ArgumentList "-avd", "Pixel_6", "-no-audio", "-no-boot-anim" `
        -WindowStyle Minimized

    Write-Host "    Waiting for emulator to boot (1-3 min)..." -ForegroundColor DarkGray
    $booted = $false
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep 5
        try {
            $prop = Invoke-Adb shell getprop sys.boot_completed
            if ($prop -match "^1") {
                $booted = $true
                break
            }
        }
        catch { }
        Write-Host "    ... boot check $i/60" -ForegroundColor DarkGray
    }
    if (-not $booted) {
        Write-Fail "Emulator never fully booted. Start it manually from Android Studio AVD Manager."
    }
    Start-Sleep 5
    $deviceList = Invoke-Adb devices
    $runningEmu = $deviceList | Where-Object { $_ -match "emulator" -and $_ -match "device" }
}
Write-OK "Emulator: $($runningEmu | Select-Object -First 1)"

# ---------------------------------------------------------------------------
# Enable Android accessibility service so Flutter builds its semantics tree
# ---------------------------------------------------------------------------
# Flutter only populates the UiAutomator2-visible accessibility/semantics tree
# when an accessibility service is attached. Without this, all @text XPath
# searches return 404 even though the app renders correctly on screen.
# We enable the Appium stub service (installed with UiAutomator2) which is
# lighter than TalkBack and doesn't produce audio/vibration feedback.
Write-Step "Enabling accessibility service (required for Flutter semantics tree)"
$emuId = ($runningEmu | Select-Object -First 1) -replace "\s+.*$", ""
# Try Appium's own stub service first, fall back to TalkBack
$appiumA11y = "io.appium.uiautomator2.server/io.appium.uiautomator2.server.AppiumUiAutomator2Server"
$talkback   = "com.google.android.marvin.talkback/com.google.android.marvin.talkback.TalkBackService"
Invoke-Adb -s $emuId shell settings put secure enabled_accessibility_services $talkback | Out-Null
Invoke-Adb -s $emuId shell settings put secure accessibility_enabled 1 | Out-Null
Start-Sleep 3
Write-OK "Accessibility service enabled on $emuId"

# ---------------------------------------------------------------------------
# 1. Patch constants.dart
# ---------------------------------------------------------------------------
if (-not $SkipBuild) {
    Write-Step "Patching constants.dart -> http://10.0.2.2:8000"
    $constFile = Join-Path $AppDir "lib\core\constants.dart"
    if (-not (Test-Path $constFile)) {
        Write-Fail "constants.dart not found at: $constFile"
    }
    $orig    = Get-Content $constFile -Raw
    $patched = $orig -replace "https://[a-zA-Z0-9.\-]+\.onrender\.com", "http://10.0.2.2:8000"
    if ($patched -eq $orig) {
        Write-Warn "Render URL pattern not found or already patched"
    }
    else {
        Set-Content $constFile $patched
        Write-OK "constants.dart patched"
    }

    # -----------------------------------------------------------------------
    # 2. Build APK
    # -----------------------------------------------------------------------
    Write-Step "Building debug APK"
    Push-Location $AppDir
    try {
        & flutter pub get
        if ($LASTEXITCODE -ne 0) { Write-Fail "flutter pub get failed" }
        & flutter build apk --debug
        if ($LASTEXITCODE -ne 0) { Write-Fail "flutter build apk --debug failed" }
    }
    finally {
        Pop-Location
    }
    Write-OK "APK built: $APKPath"
}
else {
    Write-Warn "Skipping build (-SkipBuild). Using: $APKPath"
    if (-not (Test-Path $APKPath)) {
        Write-Fail "APK not found. Remove -SkipBuild or build manually."
    }
}

# ---------------------------------------------------------------------------
# 3. Python deps for the test suite
# ---------------------------------------------------------------------------
Write-Step "Installing android-tests Python dependencies"
Push-Location $TestDir
& python -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Fail "pip install failed for requirements.txt" }
Pop-Location
Write-OK "Test dependencies installed"

# ---------------------------------------------------------------------------
# 4. Backend
# ---------------------------------------------------------------------------
New-Item -ItemType Directory -Force -Path (Join-Path $TestDir "reports") | Out-Null
$backendLog = Join-Path $TestDir "reports\backend.log"
$appiumLog  = Join-Path $TestDir "reports\appium.log"

if (-not $SkipBackend) {
    Write-Step "Installing backend Python dependencies"
    Push-Location $BEDir
    & python -m pip install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Write-Fail "backend pip install failed" }
    Pop-Location

    $env:DATABASE_URL       = "sqlite+aiosqlite:///./vulnara_local_test.db"
    $env:VULNARA_SECRET_KEY = "local-test-secret-key"
    $env:ENVIRONMENT        = "development"
    $env:PYTHONPATH         = $BEDir

    Write-Step "Seeding database (schema + accounts + fixture data)"
    Push-Location $BEDir
    & python apply_migration.py
    if ($LASTEXITCODE -ne 0) { Write-Fail "apply_migration.py failed" }
    $seedA = Join-Path $Root "backend-tests\seed_test_accounts.py"
    $seedF = Join-Path $Root "backend-tests\seed_fixture_data.py"
    # PYTHONIOENCODING=utf-8 required on Windows - seed scripts print unicode
    # checkmarks (u2713) which crash the default cp1252 console encoding.
    $env:PYTHONIOENCODING = "utf-8"
    if (Test-Path $seedA) { & python $seedA } else { Write-Warn "seed_test_accounts.py not found" }
    if (Test-Path $seedF) { & python $seedF } else { Write-Warn "seed_fixture_data.py not found" }
    $env:PYTHONIOENCODING = ""
    Pop-Location

    Write-Step "Starting backend on :8000 (background job)"
    $dbUrl     = $env:DATABASE_URL
    $secretKey = $env:VULNARA_SECRET_KEY
    $envMode   = $env:ENVIRONMENT
    $pythonPath = $BEDir

    Start-Job -Name "VulnaraBackend" -ScriptBlock {
        param($dir, $db, $key, $mode, $pypath, $log)
        Set-Location $dir
        $env:DATABASE_URL       = $db
        $env:VULNARA_SECRET_KEY = $key
        $env:ENVIRONMENT        = $mode
        $env:PYTHONPATH         = $pypath
        & python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info *> $log
    } -ArgumentList $BEDir, $dbUrl, $secretKey, $envMode, $pythonPath, $backendLog | Out-Null

    Write-Host "    Waiting for backend /health..." -ForegroundColor DarkGray
    $up = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep 2
        try {
            $r = Invoke-WebRequest "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($r.StatusCode -eq 200) { $up = $true; break }
        }
        catch { }
        Write-Host "    ... backend $i/20" -ForegroundColor DarkGray
    }
    if (-not $up) {
        Write-Warn "Last backend log:"
        if (Test-Path $backendLog) { Get-Content $backendLog -Tail 30 }
        Write-Fail "Backend never became healthy at http://127.0.0.1:8000"
    }
    Write-OK "Backend is up at http://127.0.0.1:8000"
}
else {
    Write-Warn "Skipping backend (-SkipBackend). Make sure it's running on :8000"
}

# ---------------------------------------------------------------------------
# 5. Appium
# ---------------------------------------------------------------------------
if (-not $SkipAppium) {
    $appiumCheck = Get-Command appium -ErrorAction SilentlyContinue
    if (-not $appiumCheck) {
        Write-Step "Installing Appium 3.6.0 and UiAutomator2 driver"
        & npm install -g appium@3.6.0
        if ($LASTEXITCODE -ne 0) { Write-Fail "npm install appium failed" }
        & appium driver install uiautomator2@8.4.0
    }
    else {
        Write-OK "Appium found at: $($appiumCheck.Source)"
        $driverList = & appium driver list --installed 2>&1
        if ($driverList -notmatch "uiautomator2") {
            Write-Step "Installing UiAutomator2 driver"
            & appium driver install uiautomator2@8.4.0
        } else {
            Write-OK "UiAutomator2 driver already installed - skipping"
        }
    }

    Write-Step "Starting Appium on :4723 (background job)"
    Start-Job -Name "VulnaraAppium" -ScriptBlock {
        param($log, $ah, $path)
        $env:ANDROID_HOME = $ah
        $env:PATH = $path
        & appium --address 127.0.0.1 --port 4723 --relaxed-security *> $log
    } -ArgumentList $appiumLog, (Join-Path $env:LOCALAPPDATA "Android\Sdk"), $env:PATH | Out-Null

    Write-Host "    Waiting for Appium /status..." -ForegroundColor DarkGray
    $up = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep 2
        try {
            $r = Invoke-WebRequest "http://127.0.0.1:4723/status" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($r.StatusCode -eq 200) { $up = $true; break }
        }
        catch { }
        Write-Host "    ... appium $i/20" -ForegroundColor DarkGray
    }
    if (-not $up) {
        Write-Warn "Last Appium log:"
        if (Test-Path $appiumLog) { Get-Content $appiumLog -Tail 20 }
        Write-Fail "Appium never came up at http://127.0.0.1:4723"
    }
    Write-OK "Appium is up at http://127.0.0.1:4723"
}
else {
    Write-Warn "Skipping Appium (-SkipAppium). Make sure it's running on :4723"
}

# ---------------------------------------------------------------------------
# 6. Run pytest
# ---------------------------------------------------------------------------
$env:APK_PATH          = $APKPath
$env:APPIUM_SERVER_URL = "http://127.0.0.1:4723"
$env:BACKEND_BASE_URL  = "http://127.0.0.1:8000"

$allModules = @(
    "test_authentication",
    "test_authorization",
    "test_navigation",
    "test_scan_creation_forms",
    "test_scan_lifecycle_crud",
    "test_remediation_workflow",
    "test_notifications",
    "test_profile",
    "test_audit_log",
    "test_session_management",
    "test_input_validation",
    "test_error_handling",
    "test_accessibility",
    "test_responsive_orientation"
)

if ($Test -ne "") {
    $testPaths = ($Test -split ",") | ForEach-Object {
        $name = $_.Trim() -replace "\.py$", ""
        "tests/$name.py"
    }
}
else {
    $testPaths = $allModules | ForEach-Object { "tests/$_.py" }
}

Write-Step "Running tests: $($testPaths -join ', ')"
Write-Host "    Paths: $($testPaths -join ' | ')" -ForegroundColor DarkGray

Push-Location $TestDir
# Force $testPaths to a proper array so it expands correctly as arguments.
# Do NOT use @testPaths splat on a string -- it splits by characters on Windows.
[string[]]$pathArray  = @($testPaths)
$pytestArgs = @("-v", "--reruns", "2", "--reruns-delay", "3", "--tb=short", "-p", "no:cacheprovider") + $pathArray
Write-Host "    CMD: python -m pytest $pytestArgs" -ForegroundColor DarkGray
& python -m pytest @pytestArgs
$pytestExit = $LASTEXITCODE
Pop-Location

# ---------------------------------------------------------------------------
# 7. Reports
# ---------------------------------------------------------------------------
Write-Step "Generating HTML and Excel reports"
Push-Location $TestDir
& python reports\generate_reports.py
Pop-Location

$html = Join-Path $TestDir "reports\dashboard.html"
if (Test-Path $html) {
    Start-Process $html
}

Write-Host ""
if ($pytestExit -eq 0) {
    Write-Host "ALL TESTS PASSED" -ForegroundColor Green
}
else {
    Write-Host "SOME TESTS FAILED (exit $pytestExit) - see reports\dashboard.html" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Logs:" -ForegroundColor DarkGray
Write-Host "  Appium  -> $appiumLog" -ForegroundColor DarkGray
Write-Host "  Backend -> $backendLog" -ForegroundColor DarkGray
Write-Host "  Report  -> $html" -ForegroundColor DarkGray
