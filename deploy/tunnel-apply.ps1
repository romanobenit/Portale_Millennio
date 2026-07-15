# Ri-sincronizza lo stack col tunnel Cloudflare quando l'URL trycloudflare cambia.
# Rileva l'URL corrente dai log di cloudflared (o accetta -PublicHost) e ripunta:
#   - frontend/.env.local (NEXT_PUBLIC_*), rebuild
#   - Keycloak (KC_HOSTNAME) + backend (APP_URL, KEYCLOAK_URL/auth)
#   - redirect URIs + web origins del client
# Uso:  powershell -File .\deploy\tunnel-apply.ps1            (auto-detect URL)
#       powershell -File .\deploy\tunnel-apply.ps1 -PublicHost xxx.trycloudflare.com
param([string]$PublicHost = "")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$f = "docker-compose.yml"; $o = "docker-compose.override.yml"; $t = "docker-compose.tunnel.yml"

if (-not $PublicHost) {
  $logs = docker compose -f $f -f $o -f $t logs cloudflared 2>&1
  $m = ($logs | Select-String -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | Select-Object -Last 1)
  if ($m) { $PublicHost = [regex]::Match($m.ToString(), '([a-z0-9-]+\.trycloudflare\.com)').Value }
}
if (-not $PublicHost) { throw "Host pubblico non trovato. Avvia cloudflared o passa -PublicHost." }
$PUB = "https://$PublicHost"
Write-Host "==> Public URL: $PUB"

# 1) frontend/.env.local (backup una volta sola)
$p = ".\asd-millennio-frontend\.env.local"
if (-not (Test-Path ".\asd-millennio-frontend\.env.local.bak")) { Copy-Item $p ".\asd-millennio-frontend\.env.local.bak" -Force }
$c = Get-Content $p -Raw
$c = $c -replace 'NEXT_PUBLIC_KEYCLOAK_URL=.*', "NEXT_PUBLIC_KEYCLOAK_URL=$PUB/auth"
$c = $c -replace 'NEXT_PUBLIC_API_URL=.*',      "NEXT_PUBLIC_API_URL=$PUB/api/v1"
$c = $c -replace 'NEXT_PUBLIC_APP_URL=.*',       "NEXT_PUBLIC_APP_URL=$PUB"
Set-Content -Path $p -Value $c -Encoding UTF8 -NoNewline
Write-Host "==> .env.local aggiornato"

# 2) keycloak + backend con host pubblico
$env:PUBLIC_HOST = $PublicHost; $env:PUBLIC_URL = $PUB
docker compose -f $f -f $o -f $t up -d keycloak backend | Out-Null
Write-Host "==> attendo Keycloak (/auth)..."
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
  try { if ((Invoke-WebRequest "http://localhost:8080/auth/realms/millennio-asd/.well-known/openid-configuration" -UseBasicParsing -TimeoutSec 4).StatusCode -eq 200) { $ready = $true; break } } catch {}
  Start-Sleep -Seconds 3
}
if (-not $ready) { throw "Keycloak non pronto." }

# 3) client redirect URIs + web origins
$sh = @"
KC=/opt/keycloak/bin/kcadm.sh
`$KC config credentials --server http://localhost:8080/auth --realm master --user "`$KEYCLOAK_ADMIN" --password "`$KEYCLOAK_ADMIN_PASSWORD" >/dev/null
CID=`$(`$KC get clients -r millennio-asd -q clientId=millennio-frontend --fields id --format csv --noquotes | tr -d '\r\n')
`$KC update clients/`$CID -r millennio-asd -s 'redirectUris=["http://localhost:3000/*","$PUB/*"]' -s 'webOrigins=["http://localhost:3000","$PUB"]'
echo updated
"@
$tmp = Join-Path $env:TEMP "kc_apply.sh"
[System.IO.File]::WriteAllText($tmp, ($sh -replace "`r`n", "`n"))  # UTF8 senza BOM (kcadm non tollera il BOM)
$cid = docker compose -f $f -f $o -f $t ps -q keycloak
docker cp $tmp "${cid}:/tmp/kc_apply.sh" | Out-Null
docker compose -f $f -f $o -f $t exec -T keycloak sh /tmp/kc_apply.sh
Write-Host "==> client Keycloak aggiornato"

# 4) rebuild frontend con i nuovi URL
Write-Host "==> rebuild frontend (no-cache)..."
docker compose -f $f -f $o -f $t build --no-cache frontend | Out-Null
docker compose -f $f -f $o -f $t up -d frontend | Out-Null

Write-Host ""
Write-Host "OK. Demo su: $PUB"
