# AWS ECS Deployment Verification Script
# This script verifies that the Counsel AI deployment is working correctly

param(
    [string]$Region = "us-east-1",
    [string]$ClusterName = "counsel-cluster",
    [string]$ServiceName = "counsel-service",
    [string]$ALBName = "counsel-alb"
)

$ErrorActionPreference = "Continue"

Write-Host "🔍 Verifying AWS ECS Fargate Deployment for Counsel AI" -ForegroundColor Blue

# Function to test HTTP endpoint
function Test-Endpoint {
    param($Url, $Description)
    
    try {
        Write-Host "Testing $Description..." -ForegroundColor Yellow
        $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 30
        Write-Host "✅ $Description: SUCCESS" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ $Description: FAILED - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to test API endpoint
function Test-APIEndpoint {
    param($BaseUrl)
    
    try {
        Write-Host "Testing API endpoint..." -ForegroundColor Yellow
        $body = @{
            query = "What are the constitutional rights in Kenya?"
            model_preference = "claude-sonnet-4"
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$BaseUrl/api/v1/counsel/query-direct" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 60
        
        if ($response.response_text -and $response.response_text.Length -gt 0) {
            Write-Host "✅ API Endpoint: SUCCESS" -ForegroundColor Green
            Write-Host "   Model Used: $($response.model_used)" -ForegroundColor Cyan
            Write-Host "   Response Length: $($response.response_text.Length) characters" -ForegroundColor Cyan
            return $true
        } else {
            Write-Host "❌ API Endpoint: FAILED - Empty response" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ API Endpoint: FAILED - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

try {
    # Step 1: Check AWS CLI configuration
    Write-Host "📋 Step 1: Checking AWS CLI configuration..." -ForegroundColor Yellow
    $accountId = aws sts get-caller-identity --query Account --output text 2>$null
    if ($accountId) {
        Write-Host "✅ AWS CLI configured - Account ID: $accountId" -ForegroundColor Green
    } else {
        Write-Host "❌ AWS CLI not configured or no permissions" -ForegroundColor Red
        exit 1
    }

    # Step 2: Check ECS Cluster
    Write-Host "🏗️ Step 2: Checking ECS Cluster..." -ForegroundColor Yellow
    $clusterInfo = aws ecs describe-clusters --clusters $ClusterName --region $Region 2>$null | ConvertFrom-Json
    if ($clusterInfo.clusters -and $clusterInfo.clusters[0].status -eq "ACTIVE") {
        Write-Host "✅ ECS Cluster '$ClusterName' is ACTIVE" -ForegroundColor Green
        Write-Host "   Running Tasks: $($clusterInfo.clusters[0].runningTasksCount)" -ForegroundColor Cyan
        Write-Host "   Active Services: $($clusterInfo.clusters[0].activeServicesCount)" -ForegroundColor Cyan
    } else {
        Write-Host "❌ ECS Cluster '$ClusterName' not found or not active" -ForegroundColor Red
        exit 1
    }

    # Step 3: Check ECS Service
    Write-Host "🚀 Step 3: Checking ECS Service..." -ForegroundColor Yellow
    $serviceInfo = aws ecs describe-services --cluster $ClusterName --services $ServiceName --region $Region 2>$null | ConvertFrom-Json
    if ($serviceInfo.services -and $serviceInfo.services[0].status -eq "ACTIVE") {
        $service = $serviceInfo.services[0]
        Write-Host "✅ ECS Service '$ServiceName' is ACTIVE" -ForegroundColor Green
        Write-Host "   Desired Count: $($service.desiredCount)" -ForegroundColor Cyan
        Write-Host "   Running Count: $($service.runningCount)" -ForegroundColor Cyan
        Write-Host "   Pending Count: $($service.pendingCount)" -ForegroundColor Cyan
        
        if ($service.runningCount -eq $service.desiredCount) {
            Write-Host "✅ Service is stable" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Service is not stable - tasks may be starting" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ ECS Service '$ServiceName' not found or not active" -ForegroundColor Red
        exit 1
    }

    # Step 4: Check Load Balancer
    Write-Host "⚖️ Step 4: Checking Application Load Balancer..." -ForegroundColor Yellow
    $albInfo = aws elbv2 describe-load-balancers --names $ALBName --region $Region 2>$null | ConvertFrom-Json
    if ($albInfo.LoadBalancers -and $albInfo.LoadBalancers[0].State.Code -eq "active") {
        $alb = $albInfo.LoadBalancers[0]
        $albDNS = $alb.DNSName
        Write-Host "✅ Application Load Balancer '$ALBName' is active" -ForegroundColor Green
        Write-Host "   DNS Name: $albDNS" -ForegroundColor Cyan
        Write-Host "   Scheme: $($alb.Scheme)" -ForegroundColor Cyan
    } else {
        Write-Host "❌ Application Load Balancer '$ALBName' not found or not active" -ForegroundColor Red
        exit 1
    }

    # Step 5: Check Target Group Health
    Write-Host "🎯 Step 5: Checking Target Group Health..." -ForegroundColor Yellow
    $targetGroups = aws elbv2 describe-target-groups --names "counsel-targets" --region $Region 2>$null | ConvertFrom-Json
    if ($targetGroups.TargetGroups) {
        $targetGroupArn = $targetGroups.TargetGroups[0].TargetGroupArn
        $targetHealth = aws elbv2 describe-target-health --target-group-arn $targetGroupArn --region $Region 2>$null | ConvertFrom-Json
        
        $healthyTargets = ($targetHealth.TargetHealthDescriptions | Where-Object { $_.TargetHealth.State -eq "healthy" }).Count
        $totalTargets = $targetHealth.TargetHealthDescriptions.Count
        
        Write-Host "✅ Target Group Health: $healthyTargets/$totalTargets healthy" -ForegroundColor Green
        
        foreach ($target in $targetHealth.TargetHealthDescriptions) {
            $status = if ($target.TargetHealth.State -eq "healthy") { "✅" } else { "❌" }
            Write-Host "   $status Target: $($target.Target.Id):$($target.Target.Port) - $($target.TargetHealth.State)" -ForegroundColor Cyan
        }
    }

    # Step 6: Test Application Endpoints
    Write-Host "🧪 Step 6: Testing Application Endpoints..." -ForegroundColor Yellow
    $baseUrl = "http://$albDNS"
    
    # Test root endpoint
    $rootTest = Test-Endpoint "$baseUrl/" "Root Endpoint"
    
    # Test health endpoint
    $healthTest = Test-Endpoint "$baseUrl/health" "Health Endpoint"
    
    # Test API documentation
    $docsTest = Test-Endpoint "$baseUrl/docs" "API Documentation"
    
    # Test API endpoint (if health is working)
    $apiTest = $false
    if ($healthTest) {
        Write-Host "Waiting 10 seconds before testing API..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        $apiTest = Test-APIEndpoint $baseUrl
    }

    # Step 7: Check CloudWatch Logs
    Write-Host "📊 Step 7: Checking CloudWatch Logs..." -ForegroundColor Yellow
    $logGroups = aws logs describe-log-groups --log-group-name-prefix "/ecs/counsel-task" --region $Region 2>$null | ConvertFrom-Json
    if ($logGroups.logGroups) {
        Write-Host "✅ CloudWatch Log Group exists" -ForegroundColor Green
        $logGroup = $logGroups.logGroups[0]
        Write-Host "   Log Group: $($logGroup.logGroupName)" -ForegroundColor Cyan
        Write-Host "   Creation Time: $([DateTimeOffset]::FromUnixTimeMilliseconds($logGroup.creationTime).ToString())" -ForegroundColor Cyan
    } else {
        Write-Host "⚠️ CloudWatch Log Group not found" -ForegroundColor Yellow
    }

    # Summary
    Write-Host ""
    Write-Host "📋 DEPLOYMENT VERIFICATION SUMMARY" -ForegroundColor Blue
    Write-Host "=================================" -ForegroundColor Blue
    
    $tests = @(
        @{ Name = "ECS Cluster"; Status = $true },
        @{ Name = "ECS Service"; Status = $true },
        @{ Name = "Load Balancer"; Status = $true },
        @{ Name = "Root Endpoint"; Status = $rootTest },
        @{ Name = "Health Endpoint"; Status = $healthTest },
        @{ Name = "API Documentation"; Status = $docsTest },
        @{ Name = "API Endpoint"; Status = $apiTest }
    )
    
    $passedTests = ($tests | Where-Object { $_.Status -eq $true }).Count
    $totalTests = $tests.Count
    
    foreach ($test in $tests) {
        $status = if ($test.Status) { "✅ PASS" } else { "❌ FAIL" }
        Write-Host "$status $($test.Name)" -ForegroundColor $(if ($test.Status) { "Green" } else { "Red" })
    }
    
    Write-Host ""
    Write-Host "Overall Score: $passedTests/$totalTests tests passed" -ForegroundColor $(if ($passedTests -eq $totalTests) { "Green" } else { "Yellow" })
    
    if ($passedTests -eq $totalTests) {
        Write-Host ""
        Write-Host "🎉 DEPLOYMENT VERIFICATION SUCCESSFUL!" -ForegroundColor Green
        Write-Host "Your Counsel AI Legal Backend is fully operational!" -ForegroundColor Green
        Write-Host ""
        Write-Host "🔗 Access URLs:" -ForegroundColor Cyan
        Write-Host "   Application: $baseUrl" -ForegroundColor White
        Write-Host "   Health Check: $baseUrl/health" -ForegroundColor White
        Write-Host "   API Documentation: $baseUrl/docs" -ForegroundColor White
        Write-Host ""
        Write-Host "Ready for integration with legalizeme.site/counsel! 🚀" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "⚠️ DEPLOYMENT VERIFICATION INCOMPLETE" -ForegroundColor Yellow
        Write-Host "Some tests failed. Please check the logs and retry." -ForegroundColor Yellow
    }

}
catch {
    Write-Host "❌ Verification failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Verification Complete!" -ForegroundColor Green
