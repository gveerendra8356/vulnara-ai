$adb = "C:\Users\volap\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$emu = "C:\Users\volap\AppData\Local\Android\Sdk\emulator\emulator.exe"
Start-Process -FilePath $emu -ArgumentList "-avd","Pixel_6","-no-audio","-no-boot-anim" -WindowStyle Minimized
Write-Host "Waiting for emulator to boot..."
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep 5
    $prop = & $adb shell getprop sys.boot_completed 2>$null
    if ($prop -match "^1") { break }
}
Start-Sleep 5
& $adb shell settings put secure enabled_accessibility_services "com.google.android.marvin.talkback/com.google.android.marvin.talkback.TalkBackService" 2>$null
& $adb shell settings put secure accessibility_enabled 1 2>$null

$env:ANDROID_HOME = "C:\Users\volap\AppData\Local\Android\Sdk"
$env:PATH += ";$env:ANDROID_HOME\platform-tools"

Start-Job -Name "Backend" -WorkingDirectory "..\backend" -ScriptBlock {
    $env:DATABASE_URL = "sqlite+aiosqlite:///vulnara.db"
    $env:VULNARA_SECRET_KEY = "dummy_secret_for_tests"
    $env:ENVIRONMENT = "development"
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} | Out-Null
Write-Host "Waiting for backend..."
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep 2
    try { Invoke-WebRequest "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop | Out-Null; break } catch {}
}

Start-Job -Name "Appium" -ScriptBlock {
    param($ah, $path)
    $env:ANDROID_HOME = $ah
    $env:PATH = $path
    & appium --log-level info
} -ArgumentList $env:ANDROID_HOME, $env:PATH | Out-Null
Write-Host "Waiting for Appium..."
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep 2
    try { Invoke-WebRequest "http://127.0.0.1:4723/status" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop | Out-Null; break } catch {}
}

& $adb logcat -c
Write-Host "Running pytest..."
cd C:\R\Work\Projects\PDD\vulnara\android-tests
python -m pytest -v -s tests/test_authentication.py::test_login_with_valid_credentials[admin]
$exitCode = $LASTEXITCODE

Write-Host "Dumping logcat..."
& $adb logcat -d > logcat_dump.txt

exit $exitCode
