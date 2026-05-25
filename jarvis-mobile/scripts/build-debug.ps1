param(
    [switch]$Install
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (Test-Path ".\gradlew.bat") {
    $gradle = ".\gradlew.bat"
} else {
    $cmd = Get-Command gradle -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Gradle was not found. Open this folder in Android Studio or install Gradle, then run this script again."
    }
    $gradle = $cmd.Source
}

& $gradle ":app:assembleDebug"
if ($LASTEXITCODE -ne 0) {
    throw "Gradle debug build failed with exit code $LASTEXITCODE."
}

if ($Install) {
    $adb = Get-Command adb -ErrorAction SilentlyContinue
    if (-not $adb) {
        throw "adb was not found. Install Android platform-tools or use Android Studio's Device Manager."
    }
    & $adb.Source install -r ".\app\build\outputs\apk\debug\app-debug.apk"
    if ($LASTEXITCODE -ne 0) {
        throw "adb install failed with exit code $LASTEXITCODE."
    }
}
