# VidDropper - Start Script
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "   VidDropper Video Downloader" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Installing required packages..." -ForegroundColor Yellow
pip install flask flask-cors yt-dlp

Write-Host ""
Write-Host "✅ Ready! Starting server..." -ForegroundColor Green
Write-Host "🌐 Open browser at: http://localhost:5000" -ForegroundColor Green
Write-Host "   Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

python server.py
