param([Parameter(ValueFromRemainingArguments=$true)][string[]]$BlenderArguments)
$ErrorActionPreference = 'Stop'
$blenderPath = $env:PULSE_BLENDER_PATH
if (-not $blenderPath) {
    $command = Get-Command blender -ErrorAction SilentlyContinue
    if ($command) { $blenderPath = $command.Source }
}
if (-not $blenderPath) {
    $installRoot = Join-Path $env:ProgramFiles 'Blender Foundation'
    $candidates = Get-ChildItem -LiteralPath $installRoot -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName 'blender.exe' }
    $blenderPath = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
if (-not $blenderPath -or -not (Test-Path -LiteralPath $blenderPath -PathType Leaf)) {
    throw 'Blender not found. Install official Blender or set PULSE_BLENDER_PATH to blender.exe.'
}
& $blenderPath @BlenderArguments
if ($LASTEXITCODE -ne 0) { throw "Blender exited with code $LASTEXITCODE" }
