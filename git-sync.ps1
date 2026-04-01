# Git Auto-Sync Script for Windows (PowerShell)
# This script monitors the local repository for changes and automatically commits and pushes them.

$intervalSeconds = 30
$remoteName = "origin"
$branchName = "main"

Write-Host "Starting Git Auto-Sync..." -ForegroundColor Cyan
Write-Host "Monitoring: $(Get-Location)"
Write-Host "Sync Interval: $intervalSeconds seconds"
Write-Host "Press Ctrl+C to stop."

while ($true) {
    # Check for changes (tracked and untracked)
    $status = git status --porcelain
    
    if ($status) {
        Write-Host ""
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Changes detected!" -ForegroundColor Yellow
        
        # Display detected changes
        $status | ForEach-Object { Write-Host "  $_" }
        
        # Wait a few seconds for file writes to complete (settle time)
        Write-Host "Waiting 5 seconds for settle..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 5
        
        # Sync process
        Write-Host "Adding changes..." -ForegroundColor Gray
        git add -A
        
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $commitMessage = "Auto-sync: $timestamp"
        
        Write-Host "Committing: $commitMessage" -ForegroundColor Gray
        git commit -m "$commitMessage"
        
        Write-Host "Pushing to $remoteName $branchName..." -ForegroundColor Gray
        git push $remoteName $branchName
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Done! All changes synced." -ForegroundColor Green
        } else {
            Write-Error "Push failed! You might need to pull manually if there are remote changes."
        }
    } else {
        # No changes, just wait
        # Write-Host "." -NoNewline
    }
    
    Start-Sleep -Seconds $intervalSeconds
}
