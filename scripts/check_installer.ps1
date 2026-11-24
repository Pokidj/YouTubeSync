param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$Target
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$installerPath=(Resolve-Path -LiteralPath $Installer).Path
$targetPath=[IO.Path]::GetFullPath($Target)
$scratch=Join-Path $root 'work'
if (-not $targetPath.StartsWith($scratch+'\',[StringComparison]::OrdinalIgnoreCase)) {
    throw 'La instalación de prueba solo puede escribirse dentro de work.'
}
$registry='HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{82B9F3E3-6550-49FC-B744-A718EA4FC9C0}_is1'
if(Test-Path -LiteralPath $registry) { throw 'Ya existe una instalación. No se modifica el registro de una app del usuario.' }
[IO.Directory]::CreateDirectory($scratch) | Out-Null
$process=Start-Process -FilePath $installerPath -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/NOICONS',('/DIR="'+$targetPath+'"'),('/LOG="'+(Join-Path $scratch 'installer-test.log')+'"')) -WindowStyle Hidden -Wait -PassThru
if($process.ExitCode -ne 0) { throw "Instalación de prueba fallida: $($process.ExitCode)" }
try {
    $exe=Join-Path $targetPath 'YouTubeSync.exe'
    $fixture=Join-Path $root 'tests\fixtures\local-preview.mp4'
    foreach($language in @('es','en')) {
        $env:QT_QPA_PLATFORM='offscreen'
        $env:YOUTUBESYNC_SELF_TEST_LANGUAGE=$language
        $report=Join-Path $scratch ('installed-'+$language+'.json')
        $test=Start-Process -FilePath $exe -ArgumentList @('--self-test',('"'+$report+'"'),('"'+$fixture+'"')) -WindowStyle Hidden -Wait -PassThru
        if($test.ExitCode -ne 0) { throw 'El programa instalado no arranca.' }
        $data=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
        foreach($field in @('ok','ssl','icons','diagnostics','library','manual','media','playback','native','translations')) {
            if(-not $data.$field) { throw "Validación fallida: $field ($language)" }
        }
    }
    Write-Output 'Instalación y programa completos verificados en ES/EN.'
} finally {
    Remove-Item Env:YOUTUBESYNC_SELF_TEST_LANGUAGE -ErrorAction SilentlyContinue
    $uninstall=Join-Path $targetPath 'unins000.exe'
    if(Test-Path -LiteralPath $uninstall) {
        $process=Start-Process -FilePath $uninstall -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -WindowStyle Hidden -Wait -PassThru
        if($process.ExitCode -ne 0) { throw 'No se ha podido retirar la instalación de prueba.' }
    }
}
