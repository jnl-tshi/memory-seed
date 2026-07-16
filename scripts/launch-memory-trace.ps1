[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8770,
    [switch]$RebuildCache,
    [switch]$NoOpen
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$baseUrl = "http://127.0.0.1:$Port"
$vanillaUrl = "$baseUrl/"
$reactUrl = "$baseUrl/next"

function Open-TraceViews {
    Start-Process -FilePath $vanillaUrl
    Start-Process -FilePath $reactUrl
}

try {
    $health = Invoke-WebRequest -UseBasicParsing "$baseUrl/api/runtime" -TimeoutSec 2 -ErrorAction Stop
    if ($health.StatusCode -eq 200) {
        Write-Output "Memory Trace is already running."
        Write-Output "Vanilla: $vanillaUrl"
        Write-Output "React:   $reactUrl"
        if (-not $NoOpen) {
            Open-TraceViews
        }
        return
    }
} catch {
    # No healthy Trace server answered on this port. Start the local checkout below.
}

$previousPythonPath = $env:PYTHONPATH
$sourcePythonPath = "$repoRoot;$repoRoot\memory-trace"
if ($previousPythonPath) {
    $sourcePythonPath = "$sourcePythonPath;$previousPythonPath"
}

$arguments = @(
    "-m", "memory_trace.cli",
    "--cwd", $repoRoot,
    "--host", "127.0.0.1",
    "--port", $Port,
    "--static-root", $repoRoot
)
if ($RebuildCache) {
    $arguments += "--rebuild-cache"
}
if ($NoOpen) {
    $arguments += "--no-open"
} else {
    $arguments += "--open-both"
}

Write-Output "Starting Memory Trace."
Write-Output "Vanilla: $vanillaUrl"
Write-Output "React:   $reactUrl"

$exitCode = 0
try {
    $env:PYTHONPATH = $sourcePythonPath
    & python @arguments
    $exitCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $previousPythonPath
}

if ($exitCode -ne 0) {
    exit $exitCode
}
