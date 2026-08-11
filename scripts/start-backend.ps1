$Root = Split-Path -Parent $PSScriptRoot
Push-Location "$Root\backend"
& .\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "$Root\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
