# Quick test script for LM Studio
Write-Host "`n=== Testing LM Studio Connection ===" -ForegroundColor Cyan

# Test 1: Check models endpoint
Write-Host "`n1. Checking /models endpoint..." -ForegroundColor Yellow
try {
    $models = Invoke-WebRequest -Uri "http://localhost:1234/v1/models" -UseBasicParsing -TimeoutSec 5
    Write-Host "   [OK] Models endpoint responding" -ForegroundColor Green
    $modelsData = $models.Content | ConvertFrom-Json
    Write-Host "   Available models:" -ForegroundColor Gray
    $modelsData.data | ForEach-Object { Write-Host "     - $($_.id)" -ForegroundColor Gray }
} catch {
    Write-Host "   [FAIL] Cannot reach LM Studio: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Try simple inference
Write-Host "`n2. Testing inference (chat completion)..." -ForegroundColor Yellow
Write-Host "   Sending test message (timeout: 15s)..." -ForegroundColor Gray
try {
    $body = @{
        model = "mixtral-8x7b-instruct-v0.1"
        messages = @(
            @{
                role = "user"
                content = "Say 'OK' if you can read this."
            }
        )
        max_tokens = 10
        temperature = 0.7
    } | ConvertTo-Json -Depth 3

    $response = Invoke-WebRequest -Uri "http://localhost:1234/v1/chat/completions" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 15
    
    $result = $response.Content | ConvertFrom-Json
    $reply = $result.choices[0].message.content
    
    Write-Host "   [OK] LM Studio responded!" -ForegroundColor Green
    Write-Host "   Response: $reply" -ForegroundColor Cyan
    Write-Host "`n=== LM Studio is working correctly! ===" -ForegroundColor Green
    
} catch {
    Write-Host "   [FAIL] Inference request failed!" -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Red
    Write-Host "`n=== ISSUE DETECTED ===" -ForegroundColor Yellow
    Write-Host "The model is listed but not loaded into memory." -ForegroundColor Yellow
    Write-Host "`nFIX:" -ForegroundColor Cyan
    Write-Host "1. Open LM Studio" -ForegroundColor White
    Write-Host "2. Go to 'Local Server' tab" -ForegroundColor White
    Write-Host "3. Select 'mixtral-8x7b-instruct-v0.1' from dropdown" -ForegroundColor White
    Write-Host "4. Wait for it to load (30-60 seconds)" -ForegroundColor White
    Write-Host "5. Server status should show 'Model loaded'" -ForegroundColor White
    Write-Host "`nThen run this script again to verify.`n" -ForegroundColor Gray
    exit 1
}
