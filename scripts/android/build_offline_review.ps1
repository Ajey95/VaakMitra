param(
    [string]$BuildRoot = 'D:\VaakMitraBuildTemp\learner-flow-20261114',
    [string]$ModelPath = 'E:\VaakMitraModelLab\20261112-phoneme-transfer\full-export-v2\phoneme.fp32.onnx',
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
# DEC079/UX014: keep source weights immutable; fresh installs need no PC provisioning.
$repository = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$taskRoot = [IO.Path]::GetFullPath($BuildRoot)
if (-not $taskRoot.StartsWith('D:\VaakMitraBuildTemp\', [StringComparison]::OrdinalIgnoreCase)) { throw 'BuildRoot must be under D:\VaakMitraBuildTemp' }
if ((Get-PSDrive C).Free -lt 512MB -or (Get-PSDrive D).Free -lt 8GB) { throw 'C: needs 512 MiB and D: needs 8 GiB free before staging/build' }
$sourceBundle = Join-Path $repository 'SpeakEasyAndroid\app\src\main\assets\vaakmitra\phoneme-ta-backbone-v1'
$bundle = Get-Content -LiteralPath (Join-Path $sourceBundle 'bundle.json') -Raw | ConvertFrom-Json
$expected = 'ff41636b23a41baa0ebb08e59f00fe684c9a054e40a9c41eb685542b5f5020cf'
if ($bundle.model_sha256 -ne $expected -or $bundle.model_bytes -ne 1262607977 -or $bundle.model_file -ne 'phoneme.fp32.onnx' -or $bundle.production_ready -or $bundle.approved_for_child_scoring) { throw 'Unexpected baseline bundle; no candidate promotion permitted' }
$source = Get-Item -LiteralPath $ModelPath
if ($source.Length -ne $bundle.model_bytes -or (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'Baseline model identity mismatch' }
$assetRoot = Join-Path $taskRoot 'generated-debug-assets'
$destination = Join-Path $assetRoot 'vaakmitra\phoneme-ta-backbone-v1'
New-Item -ItemType Directory -Force -Path $destination,(Join-Path $taskRoot 'tmp'),(Join-Path $taskRoot 'evidence') | Out-Null
$modelFile = Join-Path $destination 'phoneme.fp32.onnx'
if (-not (Test-Path -LiteralPath $modelFile)) { Copy-Item -LiteralPath $source.FullName -Destination $modelFile }
if ((Get-Item -LiteralPath $modelFile).Length -ne $bundle.model_bytes -or (Get-FileHash -LiteralPath $modelFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'Staged model identity mismatch' }
$vocabulary = Join-Path $sourceBundle 'vocabulary.json'
if ((Get-FileHash -LiteralPath $vocabulary -Algorithm SHA256).Hash.ToLowerInvariant() -ne $bundle.vocabulary_sha256) { throw 'Vocabulary identity mismatch' }
Copy-Item -LiteralPath $vocabulary -Destination (Join-Path $destination 'vocabulary.json')
$bundle.model_delivery = 'bundled_asset_and_authenticated_app_private_cache'
$bundle.review_install_requires_model_provisioning = $false
[IO.File]::WriteAllText((Join-Path $destination 'bundle.json'),($bundle | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
@{ requirement='DEC079/UX014'; model_source=$source.FullName; model_sha256=$expected; model_bytes=$source.Length; vocabulary_sha256=$bundle.vocabulary_sha256; generated_assets=$assetRoot; source_bundle_sha256=(Get-FileHash -LiteralPath (Join-Path $sourceBundle 'bundle.json') -Algorithm SHA256).Hash; child_scoring_enabled=$false; source_weights_modified=$false } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'evidence\asset-staging-proof.json') -Encoding utf8
if ($PrepareOnly) { Write-Output 'Pinned offline model assets staged and verified'; exit 0 }
$env:TEMP=Join-Path $taskRoot 'tmp'; $env:TMP=$env:TEMP
Push-Location (Join-Path $repository 'SpeakEasyAndroid')
try {
    & .\gradlew.bat --offline --no-daemon --no-build-cache --project-cache-dir (Join-Path $taskRoot 'project-cache') "-PvaakmitraBuildRoot=$taskRoot\android" "-PvaakmitraExtraAssets=$assetRoot" '-Dorg.gradle.jvmargs=-Xmx1536m -Dfile.encoding=UTF-8' "-Djava.io.tmpdir=$taskRoot\tmp" '-Pkotlin.compiler.execution.strategy=in-process' :app:testDebugUnitTest :app:lintDebug :app:assembleDebug :app:assembleDebugAndroidTest
    if ($LASTEXITCODE -ne 0) { throw "Offline Gradle checks failed with exit $LASTEXITCODE" }
} finally { Pop-Location }
