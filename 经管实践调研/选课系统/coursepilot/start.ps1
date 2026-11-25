$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Join-Path $PSScriptRoot 'backend')
$candidates = @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", 'python')
foreach ($candidate in $candidates) {
    if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) { continue }
    & $candidate -c "import fastapi, uvicorn; from pydantic import BaseModel; assert hasattr(BaseModel, 'model_dump')" 2>$null
    if ($LASTEXITCODE -eq 0) {
        & $candidate -m uvicorn app.main:app --host 127.0.0.1 --port 8765
        exit $LASTEXITCODE
    }
}
throw 'Install dependencies with python -m pip install -r backend/requirements.txt'
