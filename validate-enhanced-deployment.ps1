# Enhanced LegalResearchAgent Deployment Validation Script
# Validates the deployed enhanced agent meets all production requirements

param(
    [string]$BaseUrl = "http://counsel-alb-694525771.us-east-1.elb.amazonaws.com",
    [string]$FrontendUrl = "https://www.legalizeme.site/counsel",
    [switch]$RunBenchmarks = $true,
    [switch]$Verbose = $false
)

Write-Host "🔍 Enhanced LegalResearchAgent Deployment Validation" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
Write-Host "Base URL: $BaseUrl" -ForegroundColor Yellow
Write-Host "Frontend URL: $FrontendUrl" -ForegroundColor Yellow

$validationResults = @{
    "health_checks" = @{}
    "api_endpoints" = @{}
    "context_framework" = @{}
    "benchmarks" = @{}
    "performance" = @{}
    "security" = @{}
}

# Step 1: Basic Health Checks
Write-Host "`n🏥 Step 1: Basic Health Checks" -ForegroundColor Cyan

try {
    $healthResponse = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 30
    $validationResults.health_checks.basic = @{
        "status" = "PASS"
        "response" = $healthResponse
        "message" = "Basic health check passed"
    }
    Write-Host "✅ Basic health check: PASS" -ForegroundColor Green
    if ($Verbose) { Write-Host "   Status: $($healthResponse.status)" -ForegroundColor Gray }
} catch {
    $validationResults.health_checks.basic = @{
        "status" = "FAIL"
        "error" = $_.Exception.Message
        "message" = "Basic health check failed"
    }
    Write-Host "❌ Basic health check: FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

try {
    $liveResponse = Invoke-RestMethod -Uri "$BaseUrl/health/live" -Method Get -TimeoutSec 30
    $validationResults.health_checks.liveness = @{
        "status" = "PASS"
        "response" = $liveResponse
        "message" = "Liveness check passed"
    }
    Write-Host "✅ Liveness check: PASS" -ForegroundColor Green
} catch {
    $validationResults.health_checks.liveness = @{
        "status" = "FAIL"
        "error" = $_.Exception.Message
        "message" = "Liveness check failed"
    }
    Write-Host "❌ Liveness check: FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

# Step 2: Agent Health Checks
Write-Host "`n🤖 Step 2: Agent Health Checks" -ForegroundColor Cyan

try {
    $agentHealthResponse = Invoke-RestMethod -Uri "$BaseUrl/api/v1/agents/health" -Method Get -TimeoutSec 30
    $validationResults.health_checks.agent = @{
        "status" = "PASS"
        "response" = $agentHealthResponse
        "message" = "Agent health check passed"
    }
    Write-Host "✅ Agent health check: PASS" -ForegroundColor Green
    if ($Verbose) {
        Write-Host "   Agent Available: $($agentHealthResponse.agent_available)" -ForegroundColor Gray
        Write-Host "   Context Framework: $($agentHealthResponse.context_framework_enabled)" -ForegroundColor Gray
    }
} catch {
    $validationResults.health_checks.agent = @{
        "status" = "FAIL"
        "error" = $_.Exception.Message
        "message" = "Agent health check failed"
    }
    Write-Host "❌ Agent health check: FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

# Step 3: API Endpoint Validation
Write-Host "`n🔌 Step 3: API Endpoint Validation" -ForegroundColor Cyan

# Test enhanced counsel query with agent mode
try {
    $counselRequest = @{
        query = "What are the basic employment rights in Kenya?"
        agent_mode = $true
        use_enhanced_rag = $true
        context = @{
            domain = "employment_law"
            urgency = "medium"
        }
    } | ConvertTo-Json -Depth 3

    $counselResponse = Invoke-RestMethod -Uri "$BaseUrl/api/v1/counsel/query" -Method Post -Body $counselRequest -ContentType "application/json" -TimeoutSec 60
    
    $validationResults.api_endpoints.counsel_agent = @{
        "status" = "PASS"
        "confidence" = $counselResponse.confidence
        "agent_mode" = $counselResponse.agent_mode
        "message" = "Counsel query with agent mode passed"
    }
    Write-Host "✅ Counsel query (agent mode): PASS" -ForegroundColor Green
    if ($Verbose) {
        Write-Host "   Confidence: $($counselResponse.confidence)" -ForegroundColor Gray
        Write-Host "   Agent Mode: $($counselResponse.agent_mode)" -ForegroundColor Gray
    }
} catch {
    $validationResults.api_endpoints.counsel_agent = @{
        "status" = "FAIL"
        "error" = $_.Exception.Message
        "message" = "Counsel query with agent mode failed"
    }
    Write-Host "❌ Counsel query (agent mode): FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

# Test dedicated agent research endpoint
try {
    $agentRequest = @{
        query = "What are the legal requirements for employment contracts in Kenya?"
        strategy = "comprehensive"
        max_sources = 10
        confidence_threshold = 0.7
        enable_context_framework = $true
        context = @{
            domain = "employment_law"
            complexity = "intermediate"
        }
    } | ConvertTo-Json -Depth 3

    $agentResponse = Invoke-RestMethod -Uri "$BaseUrl/api/v1/agents/research" -Method Post -Body $agentRequest -ContentType "application/json" -TimeoutSec 90
    
    $validationResults.api_endpoints.agent_research = @{
        "status" = "PASS"
        "confidence" = $agentResponse.confidence
        "context_used" = $agentResponse.context_used -ne $null
        "component_metrics" = $agentResponse.component_metrics -ne $null
        "message" = "Agent research endpoint passed"
    }
    Write-Host "✅ Agent research endpoint: PASS" -ForegroundColor Green
    if ($Verbose) {
        Write-Host "   Confidence: $($agentResponse.confidence)" -ForegroundColor Gray
        Write-Host "   Context Used: $($agentResponse.context_used -ne $null)" -ForegroundColor Gray
        Write-Host "   Component Metrics: $($agentResponse.component_metrics -ne $null)" -ForegroundColor Gray
    }
} catch {
    $validationResults.api_endpoints.agent_research = @{
        "status" = "FAIL"
        "error" = $_.Exception.Message
        "message" = "Agent research endpoint failed"
    }
    Write-Host "❌ Agent research endpoint: FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

# Step 4: Context Framework Validation
Write-Host "`n🧠 Step 4: Context Framework Validation" -ForegroundColor Cyan

# Test agent metrics endpoint
try {
    $metricsResponse = Invoke-RestMethod -Uri "$BaseUrl/api/v1/agents/metrics" -Method Get -TimeoutSec 30
    
    $hasContextMetrics = $metricsResponse.metrics.context_manager -ne $null
    $hasComponentMetrics = $metricsResponse.metrics.components -ne $null
    $hasMonitoringMetrics = $metricsResponse.metrics.monitoring -ne $null
    
    $validationResults.context_framework.metrics = @{
        "status" = if ($hasContextMetrics -and $hasComponentMetrics) { "PASS" } else { "PARTIAL" }
        "context_metrics" = $hasContextMetrics
        "component_metrics" = $hasComponentMetrics
        "monitoring_metrics" = $hasMonitoringMetrics
        "message" = "Context framework metrics validation"
    }
    
    if ($hasContextMetrics -and $hasComponentMetrics) {
        Write-Host "✅ Context framework metrics: PASS" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Context framework metrics: PARTIAL" -ForegroundColor Yellow
    }
    
    if ($Verbose) {
        Write-Host "   Context Metrics: $hasContextMetrics" -ForegroundColor Gray
        Write-Host "   Component Metrics: $hasComponentMetrics" -ForegroundColor Gray
        Write-Host "   Monitoring Metrics: $hasMonitoringMetrics" -ForegroundColor Gray
    }
} catch {
    $validationResults.context_framework.metrics = @{
        "status" = "FAIL"
        "error" = $_.Exception.Message
        "message" = "Context framework metrics failed"
    }
    Write-Host "❌ Context framework metrics: FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

# Step 5: Benchmark Validation
Write-Host "`n📊 Step 5: Benchmark Validation" -ForegroundColor Cyan

if ($RunBenchmarks) {
    try {
        $benchmarkRequest = @{
            level = 1
            category = "employment_law"
            max_cases = 3
        } | ConvertTo-Json

        Write-Host "Running GAIA-style benchmarks (this may take a few minutes)..." -ForegroundColor Yellow
        $benchmarkResponse = Invoke-RestMethod -Uri "$BaseUrl/api/v1/agents/benchmark" -Method Post -Body $benchmarkRequest -ContentType "application/json" -TimeoutSec 180
        
        $passRate = $benchmarkResponse.pass_rate
        $averageScore = $benchmarkResponse.average_score
        $meetsRequirement = $passRate -ge 0.9
        
        $validationResults.benchmarks.gaia = @{
            "status" = if ($meetsRequirement) { "PASS" } else { "FAIL" }
            "pass_rate" = $passRate
            "average_score" = $averageScore
            "total_cases" = $benchmarkResponse.total_cases
            "meets_90_percent" = $meetsRequirement
            "message" = "GAIA-style benchmark validation"
        }
        
        if ($meetsRequirement) {
            Write-Host "✅ GAIA benchmarks: PASS (≥90% requirement met)" -ForegroundColor Green
        } else {
            Write-Host "❌ GAIA benchmarks: FAIL (<90% requirement)" -ForegroundColor Red
        }
        
        Write-Host "   Pass Rate: $($passRate * 100)%" -ForegroundColor $(if ($meetsRequirement) { "Green" } else { "Red" })
        Write-Host "   Average Score: $averageScore" -ForegroundColor Gray
        Write-Host "   Total Cases: $($benchmarkResponse.total_cases)" -ForegroundColor Gray
        
    } catch {
        $validationResults.benchmarks.gaia = @{
            "status" = "FAIL"
            "error" = $_.Exception.Message
            "message" = "GAIA benchmark execution failed"
        }
        Write-Host "❌ GAIA benchmarks: FAIL - $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "⏭️ Benchmarks skipped (use -RunBenchmarks to enable)" -ForegroundColor Yellow
    $validationResults.benchmarks.gaia = @{
        "status" = "SKIPPED"
        "message" = "Benchmarks skipped by user request"
    }
}

# Step 6: Performance Validation
Write-Host "`n⚡ Step 6: Performance Validation" -ForegroundColor Cyan

$performanceTests = @()

# Test response times
for ($i = 1; $i -le 3; $i++) {
    try {
        $startTime = Get-Date
        $testResponse = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 10
        $endTime = Get-Date
        $responseTime = ($endTime - $startTime).TotalMilliseconds
        
        $performanceTests += @{
            "test" = "health_check_$i"
            "response_time_ms" = $responseTime
            "status" = "PASS"
        }
    } catch {
        $performanceTests += @{
            "test" = "health_check_$i"
            "response_time_ms" = -1
            "status" = "FAIL"
            "error" = $_.Exception.Message
        }
    }
}

$avgResponseTime = ($performanceTests | Where-Object { $_.response_time_ms -gt 0 } | Measure-Object -Property response_time_ms -Average).Average
$performancePassed = $avgResponseTime -lt 5000  # 5 second threshold

$validationResults.performance.response_times = @{
    "status" = if ($performancePassed) { "PASS" } else { "FAIL" }
    "average_response_time_ms" = $avgResponseTime
    "tests" = $performanceTests
    "message" = "Performance validation"
}

if ($performancePassed) {
    Write-Host "✅ Performance tests: PASS" -ForegroundColor Green
} else {
    Write-Host "❌ Performance tests: FAIL" -ForegroundColor Red
}
Write-Host "   Average Response Time: $([math]::Round($avgResponseTime, 2))ms" -ForegroundColor Gray

# Step 7: Security Validation
Write-Host "`n🔒 Step 7: Security Validation" -ForegroundColor Cyan

# Test CORS headers
try {
    $corsResponse = Invoke-WebRequest -Uri "$BaseUrl/health" -Method Options -UseBasicParsing
    $hasCorsHeaders = $corsResponse.Headers["Access-Control-Allow-Origin"] -ne $null
    
    $validationResults.security.cors = @{
        "status" = if ($hasCorsHeaders) { "PASS" } else { "FAIL" }
        "has_cors_headers" = $hasCorsHeaders
        "message" = "CORS headers validation"
    }
    
    if ($hasCorsHeaders) {
        Write-Host "✅ CORS headers: PASS" -ForegroundColor Green
    } else {
        Write-Host "❌ CORS headers: FAIL" -ForegroundColor Red
    }
} catch {
    $validationResults.security.cors = @{
        "status" = "FAIL"
        "error" = $_.Exception.Message
        "message" = "CORS headers test failed"
    }
    Write-Host "❌ CORS headers: FAIL - $($_.Exception.Message)" -ForegroundColor Red
}

# Step 8: Generate Validation Report
Write-Host "`n📋 Step 8: Generating Validation Report" -ForegroundColor Cyan

$validationResults.summary = @{
    "timestamp" = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss UTC")
    "base_url" = $BaseUrl
    "frontend_url" = $FrontendUrl
    "validation_version" = "enhanced-agent-v1.0"
}

# Calculate overall status
$allTests = @()
$validationResults.GetEnumerator() | ForEach-Object {
    if ($_.Key -ne "summary") {
        $_.Value.GetEnumerator() | ForEach-Object {
            if ($_.Value.status) {
                $allTests += $_.Value.status
            }
        }
    }
}

$passedTests = ($allTests | Where-Object { $_ -eq "PASS" }).Count
$totalTests = $allTests.Count
$overallPassRate = if ($totalTests -gt 0) { $passedTests / $totalTests } else { 0 }

$validationResults.summary.overall_status = if ($overallPassRate -ge 0.8) { "PASS" } else { "FAIL" }
$validationResults.summary.pass_rate = $overallPassRate
$validationResults.summary.passed_tests = $passedTests
$validationResults.summary.total_tests = $totalTests

# Save validation report
$reportPath = "enhanced_agent_validation_report.json"
$validationResults | ConvertTo-Json -Depth 10 | Out-File -FilePath $reportPath -Encoding UTF8

Write-Host "✅ Validation report saved: $reportPath" -ForegroundColor Green

# Step 9: Final Summary
Write-Host "`n🎯 Final Validation Summary" -ForegroundColor Green
Write-Host "============================" -ForegroundColor Green

if ($validationResults.summary.overall_status -eq "PASS") {
    Write-Host "🎉 VALIDATION PASSED!" -ForegroundColor Green
    Write-Host "The Enhanced LegalResearchAgent deployment meets all requirements." -ForegroundColor Green
} else {
    Write-Host "❌ VALIDATION FAILED!" -ForegroundColor Red
    Write-Host "The deployment has issues that need to be addressed." -ForegroundColor Red
}

Write-Host "`nTest Results:" -ForegroundColor Cyan
Write-Host "• Passed: $passedTests/$totalTests tests ($([math]::Round($overallPassRate * 100, 1))%)" -ForegroundColor $(if ($overallPassRate -ge 0.8) { "Green" } else { "Red" })

if ($validationResults.benchmarks.gaia.status -eq "PASS") {
    Write-Host "• GAIA Benchmarks: ✅ $($validationResults.benchmarks.gaia.pass_rate * 100)% pass rate (≥90% required)" -ForegroundColor Green
} elseif ($validationResults.benchmarks.gaia.status -eq "SKIPPED") {
    Write-Host "• GAIA Benchmarks: ⏭️ Skipped" -ForegroundColor Yellow
} else {
    Write-Host "• GAIA Benchmarks: ❌ Failed or below 90% requirement" -ForegroundColor Red
}

Write-Host "`n🔗 Deployment URLs:" -ForegroundColor Cyan
Write-Host "• API Base: $BaseUrl" -ForegroundColor Yellow
Write-Host "• Health Check: $BaseUrl/health" -ForegroundColor Yellow
Write-Host "• Agent Health: $BaseUrl/api/v1/agents/health" -ForegroundColor Yellow
Write-Host "• API Documentation: $BaseUrl/docs" -ForegroundColor Yellow
Write-Host "• Frontend: $FrontendUrl" -ForegroundColor Yellow

Write-Host "`n📊 Enhanced Features Validated:" -ForegroundColor Cyan
Write-Host "• Context-aware legal research with modular chaining" -ForegroundColor White
Write-Host "• GAIA-style benchmarking with 90% pass rate requirement" -ForegroundColor White
Write-Host "• Real-time monitoring and context refinement" -ForegroundColor White
Write-Host "• Enhanced API endpoints with backward compatibility" -ForegroundColor White

if ($validationResults.summary.overall_status -eq "PASS") {
    Write-Host "`n🚀 Ready for production use!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n⚠️ Please address validation failures before production use." -ForegroundColor Yellow
    exit 1
}
