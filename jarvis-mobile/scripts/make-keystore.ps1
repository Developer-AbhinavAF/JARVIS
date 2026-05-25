param(
    [string]$Alias = "jarvis-mobile",
    [string]$Keystore = "jarvis-mobile-release.jks"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$keytool = Get-Command keytool -ErrorAction SilentlyContinue
if (-not $keytool) {
    throw "keytool was not found. Install a JDK first. Android Studio usually includes one."
}

$storePassword = Read-Host "Keystore password" -AsSecureString
$keyPassword = Read-Host "Key password (can be same)" -AsSecureString

$bstr1 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($storePassword)
$bstr2 = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($keyPassword)
try {
    $storePlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr1)
    $keyPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr2)

    & $keytool.Source -genkeypair `
        -v `
        -keystore $Keystore `
        -storepass $storePlain `
        -keypass $keyPlain `
        -alias $Alias `
        -keyalg RSA `
        -keysize 2048 `
        -validity 10000 `
        -dname "CN=JARVIS Mobile, OU=Personal, O=JARVIS, L=Local, S=Local, C=IN"

    @"
storeFile=$Keystore
storePassword=$storePlain
keyAlias=$Alias
keyPassword=$keyPlain
"@ | Set-Content -Path ".\keystore.properties" -Encoding UTF8

    Write-Host "Created $Keystore and keystore.properties"
} finally {
    if ($bstr1 -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr1) }
    if ($bstr2 -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr2) }
}
