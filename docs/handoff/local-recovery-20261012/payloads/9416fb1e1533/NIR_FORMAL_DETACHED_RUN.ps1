$ErrorActionPreference = 'Stop'
$Repo = 'D:\Project\厚粲杯\08_算法\01_Attention-Analysis_nvidia-cuda'
$Launcher = Join-Path $Repo 'runtime\nir-formal\run_nvidia_final_topology.ps1'
$Config = Join-Path $Repo 'runtime\nir-formal\config.yaml'
$LogDir = 'D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR\_runtime_logs'
$Log = Join-Path $LogDir ('detached_formal_queue_{0}.log' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Location $Repo
& pwsh.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $Launcher -Config $Config -Device 0 *>> $Log
exit $LASTEXITCODE
