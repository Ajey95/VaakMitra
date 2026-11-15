param([string]$ArtifactRoot = 'D:\VaakMitraData\artifacts\phoneme-ta19-v1')
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$bundleRoot = Join-Path $ArtifactRoot 'bundle'
$manifest = Get-Content -LiteralPath (Join-Path $bundleRoot 'bundle.json') -Raw | ConvertFrom-Json
$reserved=@('bundle_version','decoder','input_samples','approved_for_child_scoring','production_ready','model_file','model_sha256','vocabulary_sha256','tokens','frame_shift_ms','output_frames')
$names=@($manifest.PSObject.Properties.Name)
foreach($key in $names) {
    if ($reserved -contains $key -and $reserved -cnotcontains $key) { throw 'Invalid manifest key casing' }
}
foreach($key in @('bundle_version','input_samples','approved_for_child_scoring','production_ready','model_file','model_sha256','vocabulary_sha256','tokens')) {
    if ($names -cnotcontains $key) { throw 'Missing exact manifest key' }
}
if ($manifest.bundle_version -isnot [string] -or
    $manifest.bundle_version -cnotin @('phoneme-ta19-v1','phoneme-ta19-v2') -or
    ($manifest.input_samples -isnot [long] -and $manifest.input_samples -isnot [int]) -or
    ($manifest.tokens -isnot [long] -and $manifest.tokens -isnot [int]) -or
    $manifest.input_samples -ne 48000 -or $manifest.tokens -ne 61 -or
    $manifest.approved_for_child_scoring -isnot [bool] -or $manifest.production_ready -isnot [bool] -or
    $manifest.approved_for_child_scoring -ne $false -or $manifest.production_ready -ne $false) {
    throw 'Unexpected phoneme artifact contract'
}
# PHN-003 / DEC-035: validate the decoder before copying a versioned bundle.
$hasDecoder=$names -ccontains 'decoder'
if (-not $hasDecoder) {
    if ($manifest.bundle_version -cne 'phoneme-ta19-v1') { throw 'Missing explicit decoder' }
} elseif ($null -eq $manifest.decoder) { throw 'Invalid null decoder' }
elseif ($manifest.decoder.type -ceq 'greedy') {
    if (@($manifest.decoder.PSObject.Properties).Count -ne 1 -or @($manifest.decoder.PSObject.Properties.Name) -cnotcontains 'type') { throw 'Unexpected greedy parameters' }
} elseif ($manifest.decoder.type -ceq 'ctc_prefix_beam') {
    $keys=@($manifest.decoder.PSObject.Properties.Name)
    if ($manifest.bundle_version -cne 'phoneme-ta19-v2' -or
        @($manifest.decoder.PSObject.Properties).Count -ne 3 -or
        $keys -cnotcontains 'type' -or $keys -cnotcontains 'beam_width' -or $keys -cnotcontains 'nonblank_top_k' -or
        ($manifest.decoder.beam_width -isnot [long] -and $manifest.decoder.beam_width -isnot [int]) -or
        ($manifest.decoder.nonblank_top_k -isnot [long] -and $manifest.decoder.nonblank_top_k -isnot [int]) -or
        $manifest.decoder.beam_width -lt 1 -or $manifest.decoder.beam_width -gt 10 -or
        $manifest.decoder.nonblank_top_k -lt 1 -or $manifest.decoder.nonblank_top_k -ge $manifest.tokens -or
        $manifest.decoder.nonblank_top_k -gt 60) { throw 'Invalid beam decoder' }
} else { throw 'Unknown decoder' }
if ($manifest.model_file -isnot [string] -or $manifest.model_file -cnotin @('phoneme.fp32.onnx','phoneme.int8.onnx')) { throw 'Invalid model filename' }
foreach ($binding in @(
    @{ File=$manifest.model_file; Hash=$manifest.model_sha256 },
    @{ File='vocabulary.json'; Hash=$manifest.vocabulary_sha256 }
)) {
    if ($binding.Hash -isnot [string] -or $binding.Hash -cnotmatch '^[a-f0-9]{64}$') { throw 'Invalid exact lowercase hash' }
    $actual=(Get-FileHash -LiteralPath (Join-Path $bundleRoot $binding.File) -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -cne $binding.Hash) { throw "Bundle hash mismatch: $($binding.File)" }
}
$target=Join-Path $repoRoot 'SpeakEasyAndroid\app\src\main\assets\vaakmitra\phoneme-ta19-v1'
New-Item -ItemType Directory -Force -Path $target | Out-Null
foreach ($name in @('bundle.json','vocabulary.json','MODEL_CARD.txt',$manifest.model_file)) {
    Copy-Item -LiteralPath (Join-Path $bundleRoot $name) -Destination (Join-Path $target $name)
}
$fixtureTarget=Join-Path $repoRoot 'SpeakEasyAndroid\app\src\androidTest\assets\phoneme-fixtures'
New-Item -ItemType Directory -Force -Path $fixtureTarget | Out-Null
Get-ChildItem -LiteralPath (Join-Path $ArtifactRoot 'instrumentation-assets') -File | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $fixtureTarget $_.Name)
}
Write-Output "Verified phoneme bundle installed in app assets: $target"
