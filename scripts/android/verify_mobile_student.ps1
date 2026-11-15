[CmdletBinding()]
param(
    [string]$PythonExe = "python",
    [string]$WslDistribution = "Ubuntu-24.04",
    [string]$WslPython = "~/.local/share/vaakmitra/venv-py310/bin/python",
    [switch]$SkipDevice
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$androidRoot = Join-Path $repoRoot "SpeakEasyAndroid"
$backendRoot = Join-Path $repoRoot "backend"
$bundleRoot = Join-Path $androidRoot "app\src\main\assets\vaakmitra\mobile-student-ta19-v0"
$evidenceRoot = Join-Path $repoRoot "docs\evidence\mobile-student-ta19-v0"

function Invoke-Checked([string]$Label, [scriptblock]$Action) {
    Write-Host "==> $Label"
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE" }
}

# DEC-028/MST-006: independently verify every declared runtime byte before testing.
$manifest = Get-Content (Join-Path $bundleRoot "bundle.json") -Raw | ConvertFrom-Json
foreach ($entry in $manifest.files.PSObject.Properties) {
    $path = Join-Path $bundleRoot $entry.Name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing bundle file: $($entry.Name)" }
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne [string]$entry.Value) { throw "Bundle hash mismatch: $($entry.Name)" }
}
if ($manifest.approved_for_child_scoring -ne $false -or $manifest.release_build_enabled -ne $false) {
    throw "Development bundle policy flags are invalid"
}

Push-Location $backendRoot
try {
    Invoke-Checked "Windows backend suite except ONNX-only module" {
        & $PythonExe -m pytest -q --ignore=tests/vaakmitra_word/test_mobile_student_export.py
    }
} finally { Pop-Location }

$driveLetter = $backendRoot.Substring(0, 1).ToLowerInvariant()
$wslBackend = "/mnt/$driveLetter/" + $backendRoot.Substring(3).Replace("\", "/")
Invoke-Checked "WSL ONNX export/quantization tests" {
    & wsl -d $WslDistribution -- bash -lc "cd '$wslBackend' && $WslPython -m pytest tests/vaakmitra_word/test_mobile_student_export.py -q"
}

Push-Location $androidRoot
$device = $null
$abi = $null
$deviceSdk = $null
$deviceMemoryKb = $null
$wifiStatus = $null
$mobileData = $null
try {
    Invoke-Checked "Android unit, lint and ABI-split APK build" {
        & .\gradlew.bat :app:testDebugUnitTest :app:lintDebug :app:assembleDebug --offline --console=plain
    }

    $adb = Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe"
    if (-not $SkipDevice -and (Test-Path -LiteralPath $adb)) {
        $device = (& $adb devices | Select-String "\sdevice$").Line | Select-Object -First 1
    }
    if ($device) {
        $initialWifiStatus = (& $adb shell cmd wifi status | Select-Object -First 1).Trim()
        $initialMobileData = (& $adb shell settings get global mobile_data).Trim()
        try {
            # DEC-028/MST-010: prove that native inference and launch do not depend on a network path.
            Invoke-Checked "Disable device Wi-Fi for offline verification" { & $adb shell svc wifi disable }
            Invoke-Checked "Disable device mobile data for offline verification" { & $adb shell svc data disable }
            $wifiStatus = (& $adb shell cmd wifi status | Select-Object -First 1).Trim()
            $mobileData = (& $adb shell settings get global mobile_data).Trim()
            if ($wifiStatus -notmatch "disabled" -or $mobileData -ne "0") {
                throw "Unable to establish offline device state (Wi-Fi='$wifiStatus', mobile_data='$mobileData')"
            }

            Invoke-Checked "Android native bundle/runtime tests (offline device)" {
                & .\gradlew.bat :app:connectedDebugAndroidTest --offline --console=plain
            }
            $abi = (& $adb shell getprop ro.product.cpu.abi).Trim()
            $deviceSdk = [int](& $adb shell getprop ro.build.version.sdk)
            $deviceMemoryKb = [int]((& $adb shell cat /proc/meminfo | Select-String '^MemTotal:' | ForEach-Object { ($_ -split '\s+')[1] }))
            $apkName = if ($abi -eq "arm64-v8a") { "app-arm64-v8a-debug.apk" } elseif ($abi -eq "x86_64") { "app-x86_64-debug.apk" } else { throw "Unsupported test ABI: $abi" }
            $apk = Join-Path $androidRoot "app\build\outputs\apk\debug\$apkName"
            Invoke-Checked "Install $apkName (offline device)" { & $adb install -r $apk }
            Invoke-Checked "Cold launch main activity (offline device)" { & $adb shell am start -W -n com.team96.speakeasy/.MainActivity }
        } finally {
            if ($initialWifiStatus -match "enabled") { & $adb shell svc wifi enable | Out-Null }
            if ($initialMobileData -eq "1") { & $adb shell svc data enable | Out-Null }
        }
    }
} finally { Pop-Location }

$arm64Apk = Join-Path $androidRoot "app\build\outputs\apk\debug\app-arm64-v8a-debug.apk"
if (-not (Test-Path -LiteralPath $arm64Apk)) { throw "ARM64 APK missing" }
New-Item -ItemType Directory -Path $evidenceRoot -Force | Out-Null
$result = [ordered]@{
    schema_version = "vaakmitra-mobile-verification-1"
    requirements = @("DEC-028", "MST-005", "MST-006", "MST-008", "MST-009", "MST-010")
    verified_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    bundle_version = $manifest.bundle_version
    official_child_scoring = $false
    arm64_apk = $arm64Apk
    arm64_apk_bytes = (Get-Item -LiteralPath $arm64Apk).Length
    arm64_apk_sha256 = (Get-FileHash -LiteralPath $arm64Apk -Algorithm SHA256).Hash.ToLowerInvariant()
    device_checked = [bool]$device
    device_abi = $abi
    device_sdk = $deviceSdk
    device_memory_kb = $deviceMemoryKb
    wifi_status_during_test = $wifiStatus
    mobile_data_during_test = $mobileData
}
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $evidenceRoot "verification-latest.json") -Encoding UTF8
$result | ConvertTo-Json -Depth 5
