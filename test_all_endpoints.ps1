# Comprehensive Endpoint Testing Script for Counsel AI
# Tests all 28 documented endpoints to identify working vs broken ones

$baseUrl = "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com"
$results = @()

# Function to test an endpoint
function Test-Endpoint {
    param(
        [string]$Method,
        [string]$Path,
        [string]$Description,
        [hashtable]$Body = $null,
        [hashtable]$Headers = @{"Content-Type" = "application/json"}
    )
    
    $url = "$baseUrl$Path"
    Write-Host "Testing: $Method $Path - $Description" -ForegroundColor Yellow
    
    try {
        $params = @{
            Uri = $url
            Method = $Method
            Headers = $Headers
            TimeoutSec = 30
        }
        
        if ($Body -and $Method -in @("POST", "PUT", "PATCH")) {
            $params.Body = ($Body | ConvertTo-Json -Depth 10)
        }
        
        $response = Invoke-WebRequest @params
        $statusCode = $response.StatusCode
        $content = $response.Content
        
        Write-Host "✅ SUCCESS: $statusCode" -ForegroundColor Green
        return @{
            Method = $Method
            Path = $Path
            Description = $Description
            Status = "SUCCESS"
            StatusCode = $statusCode
            ResponseLength = $content.Length
        }
    }
    catch {
        $errorMessage = $_.Exception.Message
        $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode } else { "N/A" }
        Write-Host "❌ FAILED: $statusCode - $errorMessage" -ForegroundColor Red
        return @{
            Method = $Method
            Path = $Path
            Description = $Description
            Status = "FAILED"
            StatusCode = $statusCode
            Error = $errorMessage
        }
    }
}

Write-Host "Starting Comprehensive Endpoint Testing..." -ForegroundColor Cyan
Write-Host "Base URL: $baseUrl" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

# 1. HEALTH & MONITORING ENDPOINTS
Write-Host "`nHEALTH & MONITORING ENDPOINTS" -ForegroundColor Magenta
$results += Test-Endpoint "GET" "/" "Root endpoint"
$results += Test-Endpoint "GET" "/health" "Health check"
$results += Test-Endpoint "GET" "/health/ready" "Readiness check"
$results += Test-Endpoint "GET" "/health/live" "Liveness check"
$results += Test-Endpoint "GET" "/health/version" "Version info"
$results += Test-Endpoint "GET" "/metrics" "System metrics"
$results += Test-Endpoint "GET" "/docs" "API documentation"

# 2. LEGAL COUNSEL ENDPOINTS
Write-Host "`nLEGAL COUNSEL ENDPOINTS" -ForegroundColor Magenta
$results += Test-Endpoint "POST" "/api/v1/counsel/query" "Legal query" @{
    query = "What are the employment laws in Kenya?"
    use_enhanced_rag = $false
    agent_mode = $false
}
$results += Test-Endpoint "POST" "/api/v1/counsel/query-direct" "Direct query" @{
    query = "What is the Constitution of Kenya?"
}
$results += Test-Endpoint "GET" "/api/v1/counsel/suggestions?query=employment`&limit=3" "Query suggestions"
$results += Test-Endpoint "GET" "/api/v1/counsel/conversations" "List conversations"
$results += Test-Endpoint "POST" "/api/v1/counsel/conversations" "Create conversation" @{
    title = "Test Conversation"
    description = "Testing conversation creation"
}

# 3. SIMPLE AGENT ENDPOINTS
Write-Host "`nSIMPLE AGENT ENDPOINTS" -ForegroundColor Magenta
$results += Test-Endpoint "GET" "/api/v1/agents/health" "Agent health check"
$results += Test-Endpoint "POST" "/api/v1/agents/query" "Agent query" @{
    query = "What are the basic employment rights in Kenya?"
    model_preference = "claude-sonnet-4"
}

# 4. DOCUMENT ENDPOINTS
Write-Host "`nDOCUMENT ENDPOINTS" -ForegroundColor Magenta
$results += Test-Endpoint "POST" "/api/v1/documents/search" "Document search" @{
    query = "employment contract"
    limit = 5
}
$results += Test-Endpoint "GET" "/api/v1/documents/1/analysis" "Document analysis"

# 5. TOKEN TRACKING ENDPOINTS
Write-Host "`nTOKEN TRACKING ENDPOINTS" -ForegroundColor Magenta
$results += Test-Endpoint "GET" "/api/v1/tokens/health" "Token tracking health"
$results += Test-Endpoint "GET" "/api/v1/tokens/status/test-user" "Token status"
$results += Test-Endpoint "POST" "/api/v1/tokens/check" "Token check" @{
    userId = "test-user"
    estimatedTokens = 100
    requestType = "chat_completion"
}
$results += Test-Endpoint "POST" "/api/v1/tokens/track" "Token tracking" @{
    userId = "test-user"
    tokensUsed = 50
    requestType = "chat_completion"
}
$results += Test-Endpoint "GET" "/api/v1/tokens/history/test-user?limit=10" "Token history"

# 6. MODEL MANAGEMENT ENDPOINTS
Write-Host "`nMODEL MANAGEMENT ENDPOINTS" -ForegroundColor Magenta
$results += Test-Endpoint "GET" "/api/v1/models/config" "Model configuration"

# 7. MULTIMODAL ENDPOINTS
Write-Host "`nMULTIMODAL ENDPOINTS" -ForegroundColor Magenta
$results += Test-Endpoint "GET" "/api/v1/multimodal/health" "Multimodal health"
$results += Test-Endpoint "GET" "/api/v1/multimodal/capabilities" "Multimodal capabilities"

# SUMMARY
Write-Host "`n" + "=" * 80 -ForegroundColor Cyan
Write-Host "ENDPOINT TESTING SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

$successCount = ($results | Where-Object { $_.Status -eq "SUCCESS" }).Count
$failedCount = ($results | Where-Object { $_.Status -eq "FAILED" }).Count
$totalCount = $results.Count

Write-Host "Total Endpoints Tested: $totalCount" -ForegroundColor White
Write-Host "Working: $successCount ($([math]::Round($successCount/$totalCount*100, 1))%)" -ForegroundColor Green
Write-Host "Failed: $failedCount ($([math]::Round($failedCount/$totalCount*100, 1))%)" -ForegroundColor Red

Write-Host "`nDETAILED RESULTS:" -ForegroundColor Yellow
foreach ($result in $results) {
    $status = if ($result.Status -eq "SUCCESS") { "[OK]" } else { "[FAIL]" }
    $statusCode = $result.StatusCode
    Write-Host "$status $($result.Method) $($result.Path) - $statusCode" -ForegroundColor $(if ($result.Status -eq "SUCCESS") { "Green" } else { "Red" })
    if ($result.Status -eq "FAILED" -and $result.Error) {
        Write-Host "   Error: $($result.Error)" -ForegroundColor DarkRed
    }
}

# Export results to JSON for further analysis
$results | ConvertTo-Json -Depth 10 | Out-File "endpoint_test_results.json" -Encoding UTF8
Write-Host "`nResults saved to: endpoint_test_results.json" -ForegroundColor Cyan
