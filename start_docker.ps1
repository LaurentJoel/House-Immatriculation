$logFile = "C:\Users\laure\Desktop\ImmatriculationDomicile\docker_result.txt"
"=== Docker compose up ===" | Out-File $logFile -Encoding utf8
try {
    $output = & docker compose -f docker-compose.dev.yml up -d 2>&1
    $output | Out-File $logFile -Append -Encoding utf8
    "" | Out-File $logFile -Append -Encoding utf8
    "=== Docker ps ===" | Out-File $logFile -Append -Encoding utf8
    $ps = & docker ps -a 2>&1
    $ps | Out-File $logFile -Append -Encoding utf8
    "" | Out-File $logFile -Append -Encoding utf8
    "=== Exit code: $LASTEXITCODE ===" | Out-File $logFile -Append -Encoding utf8
} catch {
    "ERROR: $_" | Out-File $logFile -Append -Encoding utf8
}
Write-Host "Done - see docker_result.txt"
