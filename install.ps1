Write-Host "Запуск обновленного установщика Stella AI 2..." -ForegroundColor Cyan

# Эта команда скачает и сразу запустит новый установщик из твоего второго репозитория
irm https://raw.githubusercontent.com/a1x10/stella-ai2-coder/main/install.ps1 | iex
