param([string]$Api = "http://localhost:8000/api/v1")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
& "$Root/backend/.venv/Scripts/python.exe" "$Root/backend/scripts/load_demo.py" --api $Api --dataset "$Root/data/demo_knowledge.jsonl"

$seed = Invoke-RestMethod -Method Post -Uri "$Api/seeds" -ContentType "application/json" -Body (@{
    content = "What can ecological feedback teach distributed software about graceful overload control?"
    priority = 1.0
} | ConvertTo-Json)
$wander = Invoke-RestMethod -Method Post -Uri "$Api/wander" -ContentType "application/json" -Body (@{
    seed_id = $seed.id
} | ConvertTo-Json)

Write-Host "Session: $($wander.session.id)"
Write-Host "Status: $($wander.session.status)"
if ($wander.wonders.Count -gt 0) {
    Write-Host "Wonder: $($wander.wonders[0].statement)"
    Write-Host "Open: http://localhost:8080/#/wonders/$($wander.wonders[0].id)"
} else {
    Write-Host "No wonder crossed the threshold; inspect the session trace in the Wander view."
}
