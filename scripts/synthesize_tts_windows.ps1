<#
Synthesise every clip in clips.csv with the Windows OneCore voices that Chrome
and Edge expose to speechSynthesis as local voices, so the audio matches what
the app speaks on Windows. Writes <AudioDir>/<voice>/<clip_id>.wav and
<ManifestDir>/synthesis_<voice>.csv with synthesis time and audio duration.

Usage:
  powershell -ExecutionPolicy Bypass -File scripts/synthesize_tts_windows.ps1 `
    -ManifestDir evaluation/tts/announcements-v2 -AudioDir .runtime/tts-eval/announcements-v2
#>
param(
  [Parameter(Mandatory)] [string] $ManifestDir,
  [Parameter(Mandatory)] [string] $AudioDir,
  [string[]] $Voices = @('Microsoft David', 'Microsoft Zira', 'Microsoft Mark'),
  # The app sets utterance.rate = .95; WinRT SpeakingRate uses the same 1.0 = normal scale.
  [double] $Rate = 0.95
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
} | Select-Object -First 1
function Wait-WinRT($operation, [Type] $type) {
  $task = $asTask.MakeGenericMethod($type).Invoke($null, @($operation))
  $null = $task.Wait(-1)
  $task.Result
}

$clips = Import-Csv (Join-Path $ManifestDir 'clips.csv')
$available = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices
foreach ($name in $Voices) {
  $voice = $available | Where-Object DisplayName -eq $name | Select-Object -First 1
  if (-not $voice) { Write-Warning "Voice not installed: $name"; continue }
  $synth = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::new()
  $synth.Voice = $voice
  $synth.Options.SpeakingRate = $Rate
  $slug = ($name -replace '^Microsoft ', '').ToLower()
  $folder = Join-Path $AudioDir $slug
  New-Item -ItemType Directory -Force $folder | Out-Null
  $log = foreach ($clip in $clips) {
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $stream = Wait-WinRT ($synth.SynthesizeTextToStreamAsync($clip.text)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
    $reader = [Windows.Storage.Streams.DataReader]::new($stream.GetInputStreamAt(0))
    $null = Wait-WinRT ($reader.LoadAsync([uint32] $stream.Size)) ([uint32])
    $bytes = New-Object byte[] $stream.Size
    $reader.ReadBytes($bytes)
    $watch.Stop()
    [IO.File]::WriteAllBytes((Join-Path (Resolve-Path $folder) "$($clip.clip_id).wav"), $bytes)
    $byteRate = [BitConverter]::ToUInt32($bytes, 28)
    [pscustomobject]@{
      clip_id = $clip.clip_id; voice = $voice.DisplayName; rate = $Rate
      synthesis_ms = [math]::Round($watch.Elapsed.TotalMilliseconds, 1)
      audio_ms = [math]::Round(1000 * ($bytes.Length - 44) / $byteRate, 0)
    }
    $stream.Dispose(); $reader.Dispose()
  }
  $log | Export-Csv (Join-Path $ManifestDir "synthesis_$slug.csv") -NoTypeInformation -Encoding UTF8
  "$name : $($log.Count) clips -> $folder"
}
