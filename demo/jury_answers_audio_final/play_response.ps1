param([string]$Selection)

$ErrorActionPreference = 'Stop'
$choices = @('fr','en','ar','darija','fr-full','en-full','ar-full','darija-full')
if ($Selection -notin $choices -or $args.Count -gt 0) {
    Write-Output 'Usage: play_response.ps1 [fr|en|ar|darija|fr-full|en-full|ar-full|darija-full]'
    exit 1
}

$language = $Selection -replace '-full$', ''
$version = if ($Selection.EndsWith('-full')) { 'full' } else { 'demo' }
$audioPath = Join-Path $PSScriptRoot ($language + '_response_' + $version + '.wav')
if (-not (Test-Path -LiteralPath $audioPath -PathType Leaf)) {
    Write-Output "Audio unavailable: $audioPath"
    Write-Output 'See final_report.txt and generation_status.json in this folder.'
    exit 2
}

$player = New-Object System.Media.SoundPlayer
try {
    $player.SoundLocation = $audioPath
    $player.Load()
    $player.PlaySync()
} catch {
    Write-Output "Playback failed: $_"
    exit 3
} finally {
    $player.Dispose()
}
