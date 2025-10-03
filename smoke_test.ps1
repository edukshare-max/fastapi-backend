# Smoke Test para FastAPI Backend
# Ejecutar antes de cada release

$API_BASE = "https://fastapi-backend-o7ks.onrender.com"

Write-Host "🧪 SMOKE TEST - Backend API" -ForegroundColor Cyan
Write-Host "API Base: $API_BASE" -ForegroundColor Gray

# Test 1: Crear carnet
Write-Host "`n1️⃣ Crear carnet..." -ForegroundColor Yellow
$carnetResult = Invoke-WebRequest -Uri "$API_BASE/carnet" -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"matricula":"SMOKE001","nombreCompleto":"Test Smoke","edad":25}' | Select-Object StatusCode, Content
Write-Host "Status: $($carnetResult.StatusCode)" -ForegroundColor $(if($carnetResult.StatusCode -eq 200){"Green"}else{"Red"})

# Test 2: Crear nota  
Write-Host "`n2️⃣ Crear nota..." -ForegroundColor Yellow
$notaResult = Invoke-WebRequest -Uri "$API_BASE/notas" -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"matricula":"SMOKE001","departamento":"Test","cuerpo":"Smoke test note"}' | Select-Object StatusCode, Content
Write-Host "Status: $($notaResult.StatusCode)" -ForegroundColor $(if($notaResult.StatusCode -eq 200){"Green"}else{"Red"})

# Extraer IDs de las respuestas
$carnetId = ($carnetResult.Content | ConvertFrom-Json).id
$notaId = ($notaResult.Content | ConvertFrom-Json).id

Write-Host "Carnet ID: $carnetId" -ForegroundColor Gray
Write-Host "Nota ID: $notaId" -ForegroundColor Gray

# Test 3: Leer carnet por ID
Write-Host "`n3️⃣ Leer carnet por ID..." -ForegroundColor Yellow
$getCarnetById = Invoke-WebRequest -Uri "$API_BASE/carnet/$carnetId" -Method GET | Select-Object StatusCode, Content
Write-Host "Status: $($getCarnetById.StatusCode)" -ForegroundColor $(if($getCarnetById.StatusCode -eq 200){"Green"}else{"Red"})

# Test 4: Leer carnet por matrícula
Write-Host "`n4️⃣ Leer carnet por matrícula..." -ForegroundColor Yellow
$getCarnetByMatricula = Invoke-WebRequest -Uri "$API_BASE/carnet/SMOKE001" -Method GET | Select-Object StatusCode, Content
Write-Host "Status: $($getCarnetByMatricula.StatusCode)" -ForegroundColor $(if($getCarnetByMatricula.StatusCode -eq 200){"Green"}else{"Red"})

# Resumen
Write-Host "`n📊 RESUMEN:" -ForegroundColor Cyan
$tests = @($carnetResult.StatusCode, $notaResult.StatusCode, $getCarnetById.StatusCode, $getCarnetByMatricula.StatusCode)
$passed = ($tests | Where-Object { $_ -eq 200 }).Count
$total = $tests.Count

Write-Host "Pruebas pasadas: $passed/$total" -ForegroundColor $(if($passed -eq $total){"Green"}else{"Red"})

if($passed -eq $total) {
    Write-Host "✅ SMOKE TEST EXITOSO" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ SMOKE TEST FALLIDO" -ForegroundColor Red
    exit 1
}