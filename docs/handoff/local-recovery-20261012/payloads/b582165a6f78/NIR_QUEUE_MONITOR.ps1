$OutputRoot = $null
$FinalRoot = $null
$TargetPython = 'D:\CondaEnvs\nir-nvidia\python.exe'
$Host.UI.RawUI.WindowTitle = 'NIR Formal Queue Monitor (read-only)'

function Format-Duration([timespan]$Value) {
    '{0:00}:{1:00}:{2:00}' -f [int]$Value.TotalHours, $Value.Minutes, $Value.Seconds
}

function Get-ActiveProcesses {
    @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match 'run_ritnet_fullclass_(batch|extension)\.py' -and $_.CommandLine -match [regex]::Escape($TargetPython) })
}

function Get-CurrentRun([object[]]$Processes) {
    $extension = $Processes | Where-Object { $_.CommandLine -match 'run_ritnet_fullclass_extension\.py' } | Select-Object -First 1
    if (-not $extension) { return $null }
    $runMatch = [regex]::Match($extension.CommandLine, '--run-dir\s+(?:"([^"]+)"|(\S+))')
    $runDir = if ($runMatch.Success) { if ($runMatch.Groups[1].Success) { $runMatch.Groups[1].Value } else { $runMatch.Groups[2].Value } }
    $subjectMatch = [regex]::Match($runDir, '(sub-\d+)')
    $subject = if ($subjectMatch.Success) { $subjectMatch.Groups[1].Value } else { 'unknown' }
    $start = $null
    try { $start = (Get-Process -Id ([int]$extension.ProcessId) -ErrorAction Stop).StartTime } catch {}
    if (-not $start -and $runDir -and (Test-Path -LiteralPath $runDir)) {
        try { $start = (Get-Item -LiteralPath $runDir -ErrorAction Stop).CreationTime } catch {}
    }
    [pscustomobject]@{ Subject=$subject; Start=$start; ExtensionPid=$extension.ProcessId }
}

while ($true) {
    Clear-Host
    Write-Host '=== NIR FORMAL QUEUE MONITOR (READ-ONLY; NO TASK START) ===' -ForegroundColor Cyan
    Write-Host (Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')
    Write-Host ''

    $procs = Get-ActiveProcesses
    $batch = $procs | Where-Object { $_.CommandLine -match 'run_ritnet_fullclass_batch\.py' } | Select-Object -First 1
    $current = Get-CurrentRun $procs
    if ($batch) {
        $outputMatch = [regex]::Match($batch.CommandLine, '--output\s+(?:"([^"]+)"|(\S+))')
        if ($outputMatch.Success) {
            $OutputRoot = if ($outputMatch.Groups[1].Success) { $outputMatch.Groups[1].Value } else { $outputMatch.Groups[2].Value }
            $FinalRoot = Join-Path $OutputRoot 'ritnet-fullclass-final'
        }
    }
    $queueCount = '0'
    if ($batch) { $queueCount = '1' }
    Write-Host ('GPU queue: {0} (one effective parent-child chain)' -f $queueCount) -ForegroundColor Green
    if ($batch) { Write-Host ('Fixed env: {0}; child processes in same chain: {1}' -f $TargetPython, (($procs.ProcessId -join ', '))) -ForegroundColor DarkGreen }

    if ($current) {
        $elapsedText = 'reading'
        if ($current.Start) { $elapsedText = Format-Duration ((Get-Date) - $current.Start) }
        Write-Host ('Current subject: {0}; elapsed: {1}; extension PID={2}' -f $current.Subject, $elapsedText, $current.ExtensionPid) -ForegroundColor Yellow
    } else { Write-Host 'Current subject: none (queue may be switching)' -ForegroundColor Yellow }

    $latestLog = Get-ChildItem 'D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR\_runtime_logs\conda_formal_queue_*.out.log' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestLog) {
        $rateLine = Get-Content -LiteralPath $latestLog.FullName -Tail 300 -ErrorAction SilentlyContinue | Where-Object { $_ -match '\[FULLCLASS\].*rate=[0-9.]+ eyes/s' } | Select-Object -Last 1
        if ($rateLine) { Write-Host ('Latest throughput: ' + $rateLine.Trim()) -ForegroundColor Yellow }
    }

    $cpu = 0.0; $mem = 0.0
    foreach ($p in $procs) { try { $gp = Get-Process -Id ([int]$p.ProcessId) -ErrorAction Stop; $cpu += [double]$gp.CPU; $mem += [double]$gp.WorkingSet64 / 1MB } catch {} }
    Write-Host ('Process performance: CPU cumulative {0:N1}s   memory {1:N0} MB' -f $cpu, $mem)
    try {
        $gpu = & nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Host ('GPU performance: {0}' -f ($gpu -join ' | ')) }
    } catch { Write-Host 'GPU performance: nvidia-smi unavailable' }
    Write-Host ''
    Write-Host 'Completed subjects (duration = observed wall time from output dir creation to completion.json write)' -ForegroundColor Cyan
    $rows = @()
    if (Test-Path -LiteralPath $FinalRoot) {
        foreach ($dir in Get-ChildItem -LiteralPath $FinalRoot -Directory | Sort-Object Name) {
            $completion = Join-Path $dir.FullName 'completion.json'
            if (-not (Test-Path -LiteralPath $completion)) { continue }
            try {
                $j = Get-Content -LiteralPath $completion -Raw | ConvertFrom-Json
                $end = (Get-Item -LiteralPath $completion).LastWriteTime
                $start = $dir.CreationTime
                $rows += [pscustomobject]@{Subject=$j.subject; Status=$j.status; StartTime=$start.ToString('HH:mm:ss'); EndTime=$end.ToString('HH:mm:ss'); Duration=(Format-Duration ($end-$start)); EyeRows=$j.eye_metric_row_count; FrameRows=$j.frame_coverage_row_count; QC=$j.qc_saved_image_count; Pixel=$j.qc_pixel_evidence_saved_count}
            } catch {}
        }
    }
    if ($rows) { $rows | Format-Table -AutoSize } else { Write-Host 'No completed subjects' }
    Write-Host 'Refreshes every 30 seconds; closing this window does not affect the formal queue.' -ForegroundColor DarkGray
    Start-Sleep -Seconds 30
}
