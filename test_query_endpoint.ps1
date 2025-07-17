# Test the specific /query endpoint with detailed debugging
$baseUrl = "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com"

Write-Host "Testing /query endpoint with detailed debugging..." -ForegroundColor Cyan

# Test with different timeout values
$timeouts = @(10, 30, 60)

foreach ($timeout in $timeouts) {
    Write-Host "`nTesting with $timeout second timeout..." -ForegroundColor Yellow
    
    try {
        $body = @{
            query = "What are employment laws in Kenya?"
            use_enhanced_rag = $false
            agent_mode = $false
        } | ConvertTo-Json
        
        $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/counsel/query" -Method POST -Body $body -ContentType "application/json" -TimeoutSec $timeout
        
        Write-Host "SUCCESS with $timeout second timeout: $($response.StatusCode)" -ForegroundColor Green
        Write-Host "Response length: $($response.Content.Length) characters" -ForegroundColor Green
        break
    }
    catch {
        Write-Host "FAILED with $timeout second timeout: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Compare with working query-direct endpoint
Write-Host "`nTesting working /query-direct endpoint for comparison..." -ForegroundColor Yellow

try {
    $directBody = @{
        query = "What are employment laws in Kenya?"
        model_preference = "claude-sonnet-4"
    } | ConvertTo-Json
    
    $directResponse = Invoke-WebRequest -Uri "$baseUrl/api/v1/counsel/query-direct" -Method POST -Body $directBody -ContentType "application/json" -TimeoutSec 10
    
    Write-Host "query-direct SUCCESS: $($directResponse.StatusCode)" -ForegroundColor Green
    Write-Host "Response length: $($directResponse.Content.Length) characters" -ForegroundColor Green
}
catch {
    Write-Host "query-direct FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test with minimal payload
Write-Host "`nTesting /query with minimal payload..." -ForegroundColor Yellow

try {
    $minimalBody = @{
        query = "Hello"
    } | ConvertTo-Json
    
    $minimalResponse = Invoke-WebRequest -Uri "$baseUrl/api/v1/counsel/query" -Method POST -Body $minimalBody -ContentType "application/json" -TimeoutSec 30
    
    Write-Host "Minimal query SUCCESS: $($minimalResponse.StatusCode)" -ForegroundColor Green
    Write-Host "Response length: $($minimalResponse.Content.Length) characters" -ForegroundColor Green
}
catch {
    Write-Host "Minimal query FAILED: $($_.Exception.Message)" -ForegroundColor Red
}
