# Script para actualizar el campus del usuario DireccionInnovaSalud
Write-Host "`n🔄 Actualizando campus del usuario..." -ForegroundColor Cyan

# Cargar variables de entorno
$env_data = Get-Content cres_pwd.json | ConvertFrom-Json
$env:COSMOS_ENDPOINT = $env_data.COSMOS_ENDPOINT
$env:COSMOS_KEY = $env_data.COSMOS_KEY
$env:COSMOS_DB = $env_data.COSMOS_DB
$env:COSMOS_CONTAINER = $env_data.COSMOS_CONTAINER
$env:JWT_SECRET_KEY = $env_data.JWT_SECRET_KEY

# Ejecutar script de migración
python migrate_user_campus.py

Write-Host "`n✅ Proceso completado" -ForegroundColor Green
