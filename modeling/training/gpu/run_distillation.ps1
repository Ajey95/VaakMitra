param(
    [string]$FeatureManifest = "REQUIRED_PATH",
    [string]$FeatureManifestSha256 = "REQUIRED_64_HEX",
    [string]$Python = "python",
    [string]$GpuTrainingCommand = ""
)

$ErrorActionPreference = "Stop"
if ($FeatureManifest -eq "REQUIRED_PATH" -or $FeatureManifestSha256 -eq "REQUIRED_64_HEX") {
    throw "Provide the local teacher-feature manifest and REQUIRED_64_HEX replacement."
}
if (-not (Test-Path -LiteralPath $FeatureManifest -PathType Leaf)) { throw "Teacher features are missing." }
$actual = (Get-FileHash -LiteralPath $FeatureManifest -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $FeatureManifestSha256) { throw "Teacher-feature manifest hash mismatch." }
$cuda = & $Python -c "import torch; print(str(torch.cuda.is_available()).lower())"
if ($LASTEXITCODE -ne 0 -or $cuda.Trim() -ne "true") { throw "torch.cuda.is_available is false" }
if ([string]::IsNullOrWhiteSpace($GpuTrainingCommand)) {
    throw "Provide the reviewed GPU student-training entrypoint."
}

foreach ($config in @(
    "modeling/training/gpu/student-conformer.yaml",
    "modeling/training/gpu/student-conv-bigru.yaml"
)) {
    & $Python $GpuTrainingCommand --config $config --teacher-features $FeatureManifest --resume
    if ($LASTEXITCODE -ne 0) { throw "Student training failed: $config" }
}
