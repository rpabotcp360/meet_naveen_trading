$Root = Split-Path -Parent $PSScriptRoot
Push-Location "$Root\frontend"
npm run dev
