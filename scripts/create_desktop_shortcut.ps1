# Создаёт ярлык на рабочем столе для start_tic.bat (лежит в корне проекта).
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$bat = Join-Path $projectRoot "start_tic.bat"
if (-not (Test-Path $bat)) {
    Write-Error "Не найден start_tic.bat: $bat"
}
$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "Классификатор текстов.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnkPath)
$shortcut.TargetPath = $bat
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = "Запуск информационной системы классификации текстов"
$shortcut.WindowStyle = 1
$shortcut.Save()
Write-Host "Ярлык создан: $lnkPath"
