param(
  [Parameter(Mandatory = $true)][string]$WebUrl,
  [Parameter(Mandatory = $true)][string]$ApiUrl
)

$ErrorActionPreference = 'Stop'
$live = Invoke-RestMethod -Uri "$ApiUrl/health/live" -Method Get
if ($live.status -ne 'ok') { throw "API liveness check failed" }
$web = Invoke-WebRequest -Uri $WebUrl -Method Get
if ($web.StatusCode -ne 200 -or $web.Content -notmatch 'SpeakEasy') { throw "Web smoke check failed" }
Write-Output "Smoke checks passed: $WebUrl and $ApiUrl"
