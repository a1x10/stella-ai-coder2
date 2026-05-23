$ErrorActionPreference = "Stop"
$RepoRaw = "https://raw.githubusercontent.com/a1x10/stella-ai-coder2/main"
$InstallDir = Join-Path $env:USERPROFILE ".stella-ai-coder"
$VenvDir = Join-Path $InstallDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$AgentFile = Join-Path $InstallDir "stella_ai_coder.py"
$ReqFile = Join-Path $InstallDir "requirements.txt"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

function Download-File($Name) {
    $Url = "$RepoRaw/$Name"
    $Out = Join-Path $InstallDir $Name
    Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Out
}

$RequiredFiles = @("stella_ai_coder.py", "stella_autopilot_tools.py", "stella_desktop_operator.py", "stella_gui_tools.py", "stella_status_window.py", "stella_security_tools.py", "stella_bot_sandbox.py", "requirements.txt")

foreach ($file in $RequiredFiles) { Download-File $file }

if (-not (Test-Path $VenvPython)) {
    python -m venv $VenvDir
}
& $VenvPython -m pip install -r $ReqFile

Write-Host "Stella AI installed successfully!" -ForegroundColor Green
