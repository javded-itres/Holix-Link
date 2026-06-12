#Requires -Version 5.1
$ErrorActionPreference = "Stop"

function Find-Python {
    foreach ($name in @("py -3.14", "py -3.13", "py -3.12", "python3", "python")) {
        try {
            $parts = $name -split " "
            if ($parts.Count -gt 1) {
                $ver = & $parts[0] $parts[1] -c "import sys; print(sys.version_info >= (3, 12))" 2>$null
            } else {
                $ver = & $parts[0] -c "import sys; print(sys.version_info >= (3, 12))" 2>$null
            }
            if ($ver -eq "True") { return $name }
        } catch {}
    }
    throw "Python 3.12+ is required."
}

$python = Find-Python
Write-Host "Using: $python"

if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "Installing pipx..."
    if ($python -match "^py ") {
        & py -3.12 -m pip install --user pipx
        & py -3.12 -m pipx ensurepath
    } else {
        & python -m pip install --user pipx
        & python -m pipx ensurepath
    }
}

pipx install Holix-Link 2>$null
if ($LASTEXITCODE -ne 0) { pipx upgrade Holix-Link }

Write-Host ""
Write-Host "Holix Link installed. Try:"
Write-Host "  holix-link --help"
Write-Host "  holix-link pair LINK-CODE --folder C:\Users\you\Projects"