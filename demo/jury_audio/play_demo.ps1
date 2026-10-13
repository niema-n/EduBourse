param([string]$Language)

$ErrorActionPreference = 'Stop'
$files = @{
    fr = 'jury_fr_action_vs_obligation.wav'
    en = 'jury_en_ipo.wav'
    ar = 'jury_ar_investment_risks.wav'
    darija = 'jury_darija_dividend.wav'
}

if (-not $Language -or -not $files.ContainsKey($Language) -or $args.Count -gt 0) {
    Write-Output 'Usage: play_demo.ps1 [fr|en|ar|darija]'
    exit 1
}

$audioPath = Join-Path -Path $PSScriptRoot -ChildPath $files[$Language]
$player = New-Object System.Media.SoundPlayer
try {
    if (-not (Test-Path -LiteralPath $audioPath -PathType Leaf)) {
        throw "Audio file missing: $audioPath"
    }
    $player.SoundLocation = $audioPath
    $player.Load()
    $player.PlaySync()
} catch {
    Write-Error "Unable to play jury audio: $_"
    exit 1
} finally {
    $player.Dispose()
}
