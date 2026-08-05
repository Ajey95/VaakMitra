param(
    [string]$Config = "modeling/training/gpu/full-reference.yaml",
    [string]$Python = "python",
    [switch]$AccessAuthorized,
    [string]$GpuTrainingCommand = ""
)

$ErrorActionPreference = "Stop"
$settings = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
if (-not $AccessAuthorized) { throw "Accept the gated model terms before GPU work." }
$requiredJson = $settings.required_inputs | ConvertTo-Json -Compress
if ($requiredJson.Contains("REQUIRED_PATH") -or $requiredJson.Contains("REQUIRED_64_HEX")) {
    throw "Replace every REQUIRED_PATH and REQUIRED_64_HEX value before training."
}
foreach ($name in @("reviewed_inventory", "frozen_corpus_index")) {
    $pathField = "${name}_path"
    $hashField = "${name}_sha256"
    $path = $settings.required_inputs.$pathField
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required input is missing: $name" }
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $settings.required_inputs.$hashField) { throw "Required input hash mismatch: $name" }
}
$cuda = & $Python -c "import torch; print(str(torch.cuda.is_available()).lower())"
if ($LASTEXITCODE -ne 0 -or $cuda.Trim() -ne "true") { throw "torch.cuda.is_available is false" }
if ([string]::IsNullOrWhiteSpace($GpuTrainingCommand)) {
    throw "Provide the reviewed GPU training entrypoint after the model adapter probe."
}

foreach ($stage in @("head_only", "top_encoder_blocks", "full_encoder")) {
    if ($stage -eq "full_encoder") {
        Write-Host "full_encoder runs only if validation PER improved by the configured gate."
    }
    & $Python $GpuTrainingCommand --config $Config --stage $stage --resume
    if ($LASTEXITCODE -ne 0) { throw "Training stage failed: $stage" }
}
