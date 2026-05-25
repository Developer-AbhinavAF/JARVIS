$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".\keystore.properties")) {
    throw "No keystore.properties found. Run .\scripts\make-keystore.ps1 first, or build debug APK with .\scripts\build-debug.ps1."
}

if (Test-Path ".\gradlew.bat") {
    $gradle = ".\gradlew.bat"
} else {
    $cmd = Get-Command gradle -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Gradle was not found. Open this folder in Android Studio or install Gradle, then run this script again."
    }
    $gradle = $cmd.Source
}

& $gradle ":app:assembleRelease"
if ($LASTEXITCODE -ne 0) {
    throw "Gradle release build failed with exit code $LASTEXITCODE."
}
Write-Host "Release APK: $root\app\build\outputs\apk\release\app-release.apk"
