# Teardown del demo remoto: rimuove il tunnel e ripristina la config locale (localhost).
# Uso:  powershell -File .\deploy\tunnel-down.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$f = "docker-compose.yml"; $o = "docker-compose.override.yml"; $t = "docker-compose.tunnel.yml"

Write-Host "1) Rimuovo i container del tunnel (caddy, cloudflared)..."
docker compose -f $f -f $o -f $t rm -sf caddy cloudflared

Write-Host "2) Ripristino .env.local del frontend (URL localhost)..."
$bak = ".\asd-millennio-frontend\.env.local.bak"
if (Test-Path $bak) {
  Move-Item $bak ".\asd-millennio-frontend\.env.local" -Force
  Write-Host "   .env.local ripristinato dal backup"
} else {
  Write-Host "   ATTENZIONE: backup .env.local non trovato, verifica gli URL a mano"
}

Write-Host "3) Ricreo keycloak + backend con la config locale (senza override tunnel)..."
docker compose -f $f -f $o up -d keycloak backend

Write-Host "4) Ricostruisco il frontend per localhost..."
docker compose -f $f -f $o build --no-cache frontend
docker compose -f $f -f $o up -d frontend

Write-Host "Fatto. Stack tornato in locale su http://localhost:3000. Il tunnel e spento."
