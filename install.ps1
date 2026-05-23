$ErrorActionPreference = "Stop"

$RepoRaw = $env:STELLA_REPO_RAW
if ([string]::IsNullOrWhiteSpace($RepoRaw)) {
    $RepoRaw = "$RepoRaw = "https://raw.githubusercontent.com/a1x10/stella-ai-coder2/main"
}

$InstallDir = Join-Path $env:USERPROFILE ".stella-ai-coder"
$VenvDir = Join-Path $InstallDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$AgentFile = Join-Path $InstallDir "stella_ai_coder.py"
$ReqFile = Join-Path $InstallDir "requirements.txt"
$LauncherPs1 = Join-Path $InstallDir "stella.ps1"
$LauncherCmd = Join-Path $InstallDir "stella.cmd"
$Model = if ($env:STELLA_MODEL) { $env:STELLA_MODEL } else { "qwen2.5-coder:1.5b" }

Write-Host ""
Write-Host "=== Stella AI Agent 3.8 Enterprise Autopilot installer ===" -ForegroundColor Cyan
Write-Host "Install dir: $InstallDir" -ForegroundColor DarkGray
Write-Host "Model: $Model" -ForegroundColor DarkGray
Write-Host ""

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

function Test-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Download-File($Name, [bool]$Required = $true) {
    $Url = "$RepoRaw/$Name"
    $Out = Join-Path $InstallDir $Name
    Write-Host "Downloading $Name" -ForegroundColor Cyan
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Out
    } catch {
        if ($Required) { throw "Failed to download required file: $Name from $Url" }
        Write-Host "Optional file $Name was not downloaded." -ForegroundColor DarkYellow
    }
}

function Add-ToUserPath($Dir) {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($null -eq $userPath) { $userPath = "" }
    $parts = $userPath -split ";" | Where-Object { $_ -ne "" }
    if ($parts -notcontains $Dir) {
        $newPath = if ($userPath.Trim()) { "$userPath;$Dir" } else { $Dir }
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        $env:Path = "$env:Path;$Dir"
        Write-Host "Added Stella to user PATH. New terminals can run: stella" -ForegroundColor Green
    }
}

if (-not (Test-Command "py") -and -not (Test-Command "python")) {
    Write-Host "Python was not found." -ForegroundColor Yellow
    if (Test-Command "winget") {
        $ok = Read-Host "Install Python 3.12 with winget? Type Y to continue"
        if ($ok -match "^[Yy]$") {
            winget install -e --id Python.Python.3.12
            Refresh-Path
        } else {
            throw "Python is required. Install Python 3.10+ and run this command again."
        }
    } else {
        throw "Python is required. Install Python 3.10+ from https://python.org and run again."
    }
}

if (-not (Test-Command "ollama")) {
    Write-Host "Ollama was not found." -ForegroundColor Yellow
    if (Test-Command "winget") {
        $ok = Read-Host "Install Ollama with winget? Type Y to continue"
        if ($ok -match "^[Yy]$") {
            winget install -e --id Ollama.Ollama
            Refresh-Path
        } else {
            Write-Host "Ollama skipped. Stella can still use another provider if configured." -ForegroundColor DarkYellow
        }
    } else {
        Write-Host "Install Ollama from https://ollama.com/download if you want local models." -ForegroundColor DarkYellow
    }
}

$RequiredFiles = @(
    "stella_ai_coder.py",
    "stella_autopilot_tools.py",
    "stella_desktop_operator.py",
    "stella_gui_tools.py",
    "stella_status_window.py",
    "stella_security_tools.py",
    "stella_bot_sandbox.py",
    "requirements.txt"
)
foreach ($file in $RequiredFiles) { Download-File $file $true }
Download-File "README.md" $false
Download-File "PIXEL_AGENTS.md" $false

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating Python virtual environment" -ForegroundColor Cyan
    if (Test-Command "py") {
        py -3 -m venv $VenvDir
    } else {
        python -m venv $VenvDir
    }
}

Write-Host "Installing Python packages" -ForegroundColor Cyan
& $VenvPython -m pip install -U pip
& $VenvPython -m pip install -r $ReqFile

try {
    & $VenvPython -c "import tkinter" | Out-Null
} catch {
    Write-Host "Tkinter is not available in this Python build. Desktop status overlay may be disabled." -ForegroundColor DarkYellow
}

if (-not (Test-Command "adb")) {
    Write-Host "adb was not found. Phone-control tools will work after installing Android platform-tools." -ForegroundColor DarkYellow
}
if (-not (Test-Command "tesseract")) {
    Write-Host "Tesseract OCR was not found. Screen OCR will work after installing Tesseract and adding it to PATH." -ForegroundColor DarkYellow
}
Write-Host "Desktop Operator needs an unlocked interactive Windows desktop for mouse, keyboard, screenshot and app-control actions." -ForegroundColor DarkYellow
if (-not (Test-Command "git") -or -not (Test-Command "npm")) {
    Write-Host "Git and npm are recommended for optional Pixel Agents source setup." -ForegroundColor DarkYellow
}

if (Test-Command "ollama") {
    try {
        Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
    } catch {
        Write-Host "Starting Ollama in background" -ForegroundColor Cyan
        Start-Process -WindowStyle Hidden -FilePath "ollama" -ArgumentList "serve"
        Start-Sleep -Seconds 5
    }
    Write-Host "Pulling model: $Model" -ForegroundColor Cyan
    ollama pull $Model
}

$LauncherPs1Lines = @(
    "`$env:STELLA_MODEL = `"$Model`"",
    "& `"$VenvPython`" `"$AgentFile`" @args"
)
Set-Content -Path $LauncherPs1 -Value $LauncherPs1Lines -Encoding UTF8

$LauncherCmdLines = @(
    "@echo off",
    "set STELLA_MODEL=$Model",
    "`"$VenvPython`" `"$AgentFile`" %*"
)
Set-Content -Path $LauncherCmd -Value $LauncherCmdLines -Encoding ASCII

Add-ToUserPath $InstallDir

Write-Host ""
Write-Host "Stella AI Agent 3.8 Enterprise Autopilot + Desktop Operator is installed." -ForegroundColor Green
Write-Host "Run anytime:" -ForegroundColor Cyan
Write-Host "  stella" -ForegroundColor White
Write-Host ""
Write-Host "Version check:" -ForegroundColor Cyan
& $LauncherCmd --version
