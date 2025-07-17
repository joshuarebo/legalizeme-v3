# Test Fixed Endpoints Script for Counsel AI
# Tests the 4 previously failed endpoints to verify fixes

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
            TimeoutSec = 10
        }
        
        if ($Body -and $Method -in @("POST", "PUT", "PATCH")) {
            $params.Body = ($Body | ConvertTo-Json -Depth 10)
        }
        
        $response = Invoke-WebRequest @params
        $statusCode = $response.StatusCode
        $content = $response.Content
        
        Write-Host "SUCCESS: $statusCode" -ForegroundColor Green
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
        Write-Host "FAILED: $statusCode - $errorMessage" -ForegroundColor Red
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

Write-Host "Testing Fixed Endpoints..." -ForegroundColor Cyan
Write-Host "Base URL: $baseUrl" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Test the 4 previously failed endpoints
Write-Host "`nTesting Previously Failed Endpoints:" -ForegroundColor Magenta

$results += Test-Endpoint "GET" "/api/v1/counsel/suggestions?query=employment`&limit=3" "Query suggestions (FIXED)"
$results += Test-Endpoint "POST" "/api/v1/agents/query" "Agent query (FIXED)" @{
    query = "What are the basic employment rights in Kenya?"
    model_preference = "claude-sonnet-4"
}
$results += Test-Endpoint "GET" "/api/v1/documents/1/analysis" "Document analysis (FIXED)"
$results += Test-Endpoint "GET" "/api/v1/models/config" "Model configuration (FIXED)"

# SUMMARY
Write-Host "`n" + "=" * 60 -ForegroundColor Cyan
Write-Host "FIXED ENDPOINTS TEST SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

$successCount = ($results | Where-Object { $_.Status -eq "SUCCESS" }).Count
$failedCount = ($results | Where-Object { $_.Status -eq "FAILED" }).Count
$totalCount = $results.Count

Write-Host "Total Fixed Endpoints Tested: $totalCount" -ForegroundColor White
Write-Host "Working: $successCount ($([math]::Round($successCount/$totalCount*100, 1))%)" -ForegroundColor Green
Write-Host "Still Broken: $failedCount ($([math]::Round($failedCount/$totalCount*100, 1))%)" -ForegroundColor Red

Write-Host "`nDETAILED RESULTS:" -ForegroundColor Yellow
foreach ($result in $results) {
    $status = if ($result.Status -eq "SUCCESS") { "[FIXED]" } else { "[STILL BROKEN]" }
    $statusCode = $result.StatusCode
    Write-Host "$status $($result.Method) $($result.Path) - $statusCode" -ForegroundColor $(if ($result.Status -eq "SUCCESS") { "Green" } else { "Red" })
    if ($result.Status -eq "FAILED" -and $result.Error) {
        Write-Host "   Error: $($result.Error)" -ForegroundColor DarkRed
    }
}

# Export results to JSON for further analysis
$results | ConvertTo-Json -Depth 10 | Out-File "fixed_endpoints_test_results.json" -Encoding UTF8
Write-Host "`nResults saved to: fixed_endpoints_test_results.json" -ForegroundColor Cyan
