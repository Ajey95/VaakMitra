param(
    [Parameter(Mandatory = $true)]
    [string]$PreparedDir,
    [Parameter(Mandatory = $true)]
    [string]$Destination,
    [string]$Revision = "1d6a78e02c6c21d8da30eb57dd4dc02b4ed765f5",
    [int]$TrainPerSpeaker = 30,
    [int]$EvalPerSpeaker = 10
)

$ErrorActionPreference = "Stop"
if ($TrainPerSpeaker -le 0 -or $EvalPerSpeaker -le 0) {
    throw "Per-speaker limits must be positive."
}
if (Test-Path -LiteralPath $Destination) {
    throw "Destination already exists: $Destination"
}

$prepared = (Resolve-Path -LiteralPath $PreparedDir).Path
$destinationParent = Split-Path -Parent $Destination
if (-not (Test-Path -LiteralPath $destinationParent)) {
    New-Item -ItemType Directory -Path $destinationParent | Out-Null
}
$destinationAbsolute = [IO.Path]::GetFullPath($Destination)

function Select-IndexPaths([string]$IndexPath, [int]$PerSpeaker) {
    Get-Content -LiteralPath $IndexPath |
        ForEach-Object { $_ | ConvertFrom-Json } |
        Group-Object speaker |
        ForEach-Object { $_.Group | Sort-Object audio_rel_path | Select-Object -First $PerSpeaker } |
        ForEach-Object { $_.audio_rel_path }
}

$trainPaths = @(Select-IndexPaths "$prepared\train.index.jsonl" $TrainPerSpeaker)
$validationPaths = @(Select-IndexPaths "$prepared\validation.index.jsonl" $EvalPerSpeaker)
$testPaths = @(Select-IndexPaths "$prepared\test.index.jsonl" $EvalPerSpeaker)
$audioPaths = @($trainPaths + $validationPaths + $testPaths)

try {
    $env:GIT_LFS_SKIP_SMUDGE = "1"
    git clone --no-checkout `
        https://huggingface.co/datasets/asishbala/tamil-tts-dataset.git `
        $destinationAbsolute
    if ($LASTEXITCODE -ne 0) { throw "Dataset metadata clone failed." }
    git -C $destinationAbsolute sparse-checkout init --no-cone
    $patterns = @("/README.md", "/train.csv", "/val.csv", "/test.csv") + @(
        $audioPaths | ForEach-Object { "/$_" }
    )
    $patterns | git -C $destinationAbsolute sparse-checkout set --no-cone --stdin
    git -C $destinationAbsolute checkout --detach $Revision
    if ($LASTEXITCODE -ne 0) { throw "Sparse revision checkout failed." }
}
finally {
    Remove-Item Env:GIT_LFS_SKIP_SMUDGE -ErrorAction SilentlyContinue
}

$include = $audioPaths -join ","
git -C $destinationAbsolute lfs pull --include=$include --exclude=""
if ($LASTEXITCODE -ne 0) { throw "Restricted LFS download failed." }

$materialized = @(Get-ChildItem -LiteralPath "$destinationAbsolute\wavs" -Recurse -Filter *.wav)
$pointerSized = @($materialized | Where-Object { $_.Length -lt 1024 })
if ($materialized.Count -ne $audioPaths.Count -or $pointerSized.Count -ne 0) {
    throw "Downloaded audio count or LFS materialization check failed."
}

[pscustomobject]@{
    Revision = $Revision
    AudioFiles = $materialized.Count
    AudioBytes = ($materialized | Measure-Object Length -Sum).Sum
    TrainPerSpeaker = $TrainPerSpeaker
    EvalPerSpeaker = $EvalPerSpeaker
    Destination = $destinationAbsolute
}

