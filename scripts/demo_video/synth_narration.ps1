# Local, free, offline text-to-speech with the Windows SAPI voice named in narration.json.
param([string]$Json = "$PSScriptRoot\narration.json", [string]$OutDir = "$PSScriptRoot\..\..\artifacts\demo\work\audio")
Add-Type -AssemblyName System.Speech
$cfg = Get-Content $Json -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice($cfg.voice)
$synth.Rate = [int]$cfg.rate
foreach ($segment in $cfg.segments) {
  $path = Join-Path (Resolve-Path $OutDir) "$($segment.id).wav"
  $synth.SetOutputToWaveFile($path)
  $synth.Speak($segment.spoken)
  $synth.SetOutputToNull()
  Write-Output "$($segment.id) -> $path"
}
$synth.Dispose()
