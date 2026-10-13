param([string]$Language, [switch]$Demo)

$ErrorActionPreference = 'Stop'
if ($Language -notin @('fr','en','ar','darija') -or $args.Count -gt 0) {
    Write-Output 'Usage: play_response.ps1 [fr|en|ar|darija] [-Demo]'
    exit 1
}
$suffix = if ($Demo) { '_response_demo.wav' } else { '_response.wav' }
$audioPath = Join-Path $PSScriptRoot ($Language + $suffix)
$player = New-Object System.Media.SoundPlayer
try {
    if (-not (Test-Path -LiteralPath $audioPath -PathType Leaf)) {
        throw "Audio file missing: $audioPath"
    }
    $player.SoundLocation = $audioPath
    $player.Load()
    $player.PlaySync()
} finally {
    $player.Dispose()
}
