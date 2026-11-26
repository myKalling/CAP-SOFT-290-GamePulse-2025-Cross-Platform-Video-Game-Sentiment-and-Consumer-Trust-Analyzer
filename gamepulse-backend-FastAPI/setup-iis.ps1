param(
    [string]$SiteName = 'GamePulseApi',
    [int]$Port = 8080,
    [string]$ListenAddress = '127.0.0.1'
)
$ErrorActionPreference = 'Stop'
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from an elevated PowerShell window.'
}
$appcmd = Join-Path $env:windir 'System32\inetsrv\appcmd.exe'
if (-not (Test-Path -LiteralPath $appcmd)) { throw 'IIS appcmd.exe was not found. Enable IIS first.' }
$webConfig = Join-Path $PSScriptRoot 'web.config'
if (-not (Test-Path -LiteralPath $webConfig)) { throw 'The IIS web.config reverse-proxy rules are missing.' }
$modules = & $appcmd list modules
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect IIS modules.' }
if (($modules -join "`n") -notmatch 'RewriteModule') { throw 'Install IIS URL Rewrite before running this script.' }
if (($modules -join "`n") -notmatch 'ApplicationRequestRouting') { throw 'Install IIS Application Request Routing (ARR) before running this script.' }
$sites = & $appcmd list site
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect IIS sites.' }
if (($sites -join "`n") -match "(?m)^SITE `"$([regex]::Escape($SiteName))`"") { throw "IIS site '$SiteName' already exists; inspect it in IIS Manager before changing it." }
$pool = & $appcmd list apppool
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect IIS application pools.' }
if (($pool -join "`n") -notmatch "(?m)^APPPOOL `"$([regex]::Escape($SiteName))`"") {
    & $appcmd add apppool "/name:$SiteName" '/managedRuntimeVersion:'
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create the IIS application pool.' }
}
& $appcmd set config -section:system.webServer/proxy /enabled:true /preserveHostHeader:true /commit:apphost
if ($LASTEXITCODE -ne 0) { throw 'Failed to enable ARR proxying.' }
$physicalPath = (Resolve-Path -LiteralPath $PSScriptRoot).Path
& $appcmd add site "/name:$SiteName" "/bindings:http/$ListenAddress`:$Port`:" "/physicalPath:$physicalPath"
if ($LASTEXITCODE -ne 0) { throw "Failed to create IIS site '$SiteName'." }
& $appcmd set app "$SiteName/" "/applicationPool:$SiteName"
if ($LASTEXITCODE -ne 0) { throw 'Failed to assign the application pool.' }
& $appcmd start site "/site.name:$SiteName"
if ($LASTEXITCODE -ne 0) { throw "Failed to start IIS site '$SiteName'." }
Write-Host "IIS site '$SiteName' is configured on http://${ListenAddress}:$Port/."
Write-Host 'Start the API with .\run-api.ps1; confirm http://127.0.0.1:8000/health/db responds before testing IIS.'