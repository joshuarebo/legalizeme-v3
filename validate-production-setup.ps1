# Production Setup Validation Script for Counsel AI
# This script validates that all components are working correctly

param(
    [string]$Region = "us-east-1",
    [string]$ClusterName = "counsel-cluster",
    [string]$ServiceName = "counsel-service",
    [string]$ALBName = "counsel-alb",
    [string]$DBInstanceId = "counsel-db"
)

$ErrorActionPreference = "Stop"

Write-Host "🔍 Validating Production Setup for Counsel AI" -ForegroundColor Blue

$ValidationResults = @()

try {
    # Get Account ID
    $AccountId = (aws sts get-caller-identity --query Account --output text)
    Write-Host "✓ AWS Account ID: $AccountId" -ForegroundColor Green

    # Test 1: Validate RDS Database
    Write-Host "🗄️ Test 1: Validating RDS Database..." -ForegroundColor Yellow
    
    try {
        $DBStatus = aws rds describe-db-instances --db-instance-identifier $DBInstanceId --query "DBInstances[0].DBInstanceStatus" --output text 2>$null
        if ($DBStatus -eq "available") {
            $DBEndpoint = aws rds describe-db-instances --db-instance-identifier $DBInstanceId --query "DBInstances[0].Endpoint.Address" --output text
            Write-Host "✓ Database Status: $DBStatus" -ForegroundColor Green
            Write-Host "✓ Database Endpoint: $DBEndpoint" -ForegroundColor Green
            $ValidationResults += @{Test="RDS Database"; Status="PASS"; Details="Database available at $DBEndpoint"}
        } else {
            Write-Host "❌ Database Status: $DBStatus" -ForegroundColor Red
            $ValidationResults += @{Test="RDS Database"; Status="FAIL"; Details="Database status: $DBStatus"}
        }
    } catch {
        Write-Host "❌ Database not found or not accessible" -ForegroundColor Red
        $ValidationResults += @{Test="RDS Database"; Status="FAIL"; Details="Database not found"}
    }

    # Test 2: Validate ECS Cluster and Service
    Write-Host "🚀 Test 2: Validating ECS Cluster and Service..." -ForegroundColor Yellow
    
    try {
        $ClusterStatus = aws ecs describe-clusters --clusters $ClusterName --query "clusters[0].status" --output text 2>$null
        if ($ClusterStatus -eq "ACTIVE") {
            Write-Host "✓ ECS Cluster Status: $ClusterStatus" -ForegroundColor Green
            
            $ServiceStatus = aws ecs describe-services --cluster $ClusterName --services $ServiceName --query "services[0].status" --output text 2>$null
            $RunningCount = aws ecs describe-services --cluster $ClusterName --services $ServiceName --query "services[0].runningCount" --output text 2>$null
            $DesiredCount = aws ecs describe-services --cluster $ClusterName --services $ServiceName --query "services[0].desiredCount" --output text 2>$null
            
            if ($ServiceStatus -eq "ACTIVE" -and $RunningCount -eq $DesiredCount) {
                Write-Host "✓ ECS Service Status: $ServiceStatus (Running: $RunningCount/$DesiredCount)" -ForegroundColor Green
                $ValidationResults += @{Test="ECS Service"; Status="PASS"; Details="Service active with $RunningCount/$DesiredCount tasks"}
            } else {
                Write-Host "❌ ECS Service Issues: Status=$ServiceStatus, Running=$RunningCount/$DesiredCount" -ForegroundColor Red
                $ValidationResults += @{Test="ECS Service"; Status="FAIL"; Details="Service status: $ServiceStatus, Running: $RunningCount/$DesiredCount"}
            }
        } else {
            Write-Host "❌ ECS Cluster Status: $ClusterStatus" -ForegroundColor Red
            $ValidationResults += @{Test="ECS Cluster"; Status="FAIL"; Details="Cluster status: $ClusterStatus"}
        }
    } catch {
        Write-Host "❌ ECS Cluster/Service not found" -ForegroundColor Red
        $ValidationResults += @{Test="ECS Service"; Status="FAIL"; Details="Cluster or service not found"}
    }

    # Test 3: Validate Application Load Balancer
    Write-Host "⚖️ Test 3: Validating Application Load Balancer..." -ForegroundColor Yellow
    
    try {
        $ALBState = aws elbv2 describe-load-balancers --names $ALBName --query "LoadBalancers[0].State.Code" --output text 2>$null
        $ALBDNSName = aws elbv2 describe-load-balancers --names $ALBName --query "LoadBalancers[0].DNSName" --output text 2>$null
        
        if ($ALBState -eq "active") {
            Write-Host "✓ ALB Status: $ALBState" -ForegroundColor Green
            Write-Host "✓ ALB DNS Name: $ALBDNSName" -ForegroundColor Green
            
            # Check target group health
            $TargetGroups = aws elbv2 describe-target-groups --load-balancer-arn (aws elbv2 describe-load-balancers --names $ALBName --query "LoadBalancers[0].LoadBalancerArn" --output text) --query "TargetGroups[0].TargetGroupArn" --output text
            $TargetHealth = aws elbv2 describe-target-health --target-group-arn $TargetGroups | ConvertFrom-Json
            
            $HealthyTargets = ($TargetHealth.TargetHealthDescriptions | Where-Object { $_.TargetHealth.State -eq "healthy" }).Count
            $TotalTargets = $TargetHealth.TargetHealthDescriptions.Count
            
            if ($HealthyTargets -gt 0) {
                Write-Host "✓ Target Health: $HealthyTargets/$TotalTargets healthy" -ForegroundColor Green
                $ValidationResults += @{Test="ALB & Targets"; Status="PASS"; Details="ALB active with $HealthyTargets/$TotalTargets healthy targets"}
            } else {
                Write-Host "❌ Target Health: $HealthyTargets/$TotalTargets healthy" -ForegroundColor Red
                $ValidationResults += @{Test="ALB & Targets"; Status="FAIL"; Details="No healthy targets ($HealthyTargets/$TotalTargets)"}
            }
        } else {
            Write-Host "❌ ALB Status: $ALBState" -ForegroundColor Red
            $ValidationResults += @{Test="ALB"; Status="FAIL"; Details="ALB state: $ALBState"}
        }
    } catch {
        Write-Host "❌ ALB not found or not accessible" -ForegroundColor Red
        $ValidationResults += @{Test="ALB"; Status="FAIL"; Details="ALB not found"}
    }

    # Test 4: Validate API Endpoints
    Write-Host "🌐 Test 4: Validating API Endpoints..." -ForegroundColor Yellow
    
    if ($ALBDNSName) {
        $BaseURL = "http://$ALBDNSName"
        
        # Test health endpoint
        try {
            $HealthResponse = Invoke-RestMethod -Uri "$BaseURL/health" -Method GET -TimeoutSec 30
            if ($HealthResponse.status -eq "healthy") {
                Write-Host "✓ Health Endpoint: Working" -ForegroundColor Green
                $ValidationResults += @{Test="Health Endpoint"; Status="PASS"; Details="Health check successful"}
            } else {
                Write-Host "❌ Health Endpoint: Unhealthy" -ForegroundColor Red
                $ValidationResults += @{Test="Health Endpoint"; Status="FAIL"; Details="Health check failed"}
            }
        } catch {
            Write-Host "❌ Health Endpoint: Not responding" -ForegroundColor Red
            $ValidationResults += @{Test="Health Endpoint"; Status="FAIL"; Details="Endpoint not responding"}
        }

        # Test liveness endpoint
        try {
            $LivenessResponse = Invoke-RestMethod -Uri "$BaseURL/health/live" -Method GET -TimeoutSec 30
            if ($LivenessResponse.status -eq "alive") {
                Write-Host "✓ Liveness Endpoint: Working" -ForegroundColor Green
                $ValidationResults += @{Test="Liveness Endpoint"; Status="PASS"; Details="Liveness check successful"}
            } else {
                Write-Host "❌ Liveness Endpoint: Not alive" -ForegroundColor Red
                $ValidationResults += @{Test="Liveness Endpoint"; Status="FAIL"; Details="Liveness check failed"}
            }
        } catch {
            Write-Host "❌ Liveness Endpoint: Not responding" -ForegroundColor Red
            $ValidationResults += @{Test="Liveness Endpoint"; Status="FAIL"; Details="Endpoint not responding"}
        }

        # Test root endpoint
        try {
            $RootResponse = Invoke-RestMethod -Uri "$BaseURL/" -Method GET -TimeoutSec 30
            if ($RootResponse.message -like "*Counsel AI Backend*") {
                Write-Host "✓ Root Endpoint: Working" -ForegroundColor Green
                $ValidationResults += @{Test="Root Endpoint"; Status="PASS"; Details="Root endpoint accessible"}
            } else {
                Write-Host "❌ Root Endpoint: Unexpected response" -ForegroundColor Red
                $ValidationResults += @{Test="Root Endpoint"; Status="FAIL"; Details="Unexpected response"}
            }
        } catch {
            Write-Host "❌ Root Endpoint: Not responding" -ForegroundColor Red
            $ValidationResults += @{Test="Root Endpoint"; Status="FAIL"; Details="Endpoint not responding"}
        }
    }

    # Test 5: Validate Parameter Store Secrets
    Write-Host "🔐 Test 5: Validating Parameter Store Secrets..." -ForegroundColor Yellow
    
    try {
        $DatabaseURLParam = aws ssm get-parameter --name "/counsel/database-url" --with-decryption --query "Parameter.Value" --output text 2>$null
        if ($DatabaseURLParam -like "postgresql://*") {
            Write-Host "✓ Database URL Parameter: Configured" -ForegroundColor Green
            $ValidationResults += @{Test="Database URL Parameter"; Status="PASS"; Details="Parameter configured correctly"}
        } else {
            Write-Host "❌ Database URL Parameter: Invalid format" -ForegroundColor Red
            $ValidationResults += @{Test="Database URL Parameter"; Status="FAIL"; Details="Invalid parameter format"}
        }
    } catch {
        Write-Host "❌ Database URL Parameter: Not found" -ForegroundColor Red
        $ValidationResults += @{Test="Database URL Parameter"; Status="FAIL"; Details="Parameter not found"}
    }

    # Test 6: Validate CloudWatch Logs
    Write-Host "📊 Test 6: Validating CloudWatch Logs..." -ForegroundColor Yellow
    
    try {
        $LogGroups = aws logs describe-log-groups --log-group-name-prefix "/ecs/counsel-task" --query "logGroups[0].logGroupName" --output text 2>$null
        if ($LogGroups -eq "/ecs/counsel-task") {
            Write-Host "✓ CloudWatch Log Group: Exists" -ForegroundColor Green
            
            # Check for recent log events
            $RecentLogs = aws logs describe-log-streams --log-group-name "/ecs/counsel-task" --order-by LastEventTime --descending --max-items 1 --query "logStreams[0].lastEventTime" --output text 2>$null
            if ($RecentLogs -and $RecentLogs -ne "None") {
                $LastLogTime = [DateTimeOffset]::FromUnixTimeMilliseconds($RecentLogs).ToString("yyyy-MM-dd HH:mm:ss")
                Write-Host "✓ Recent Logs: Last event at $LastLogTime" -ForegroundColor Green
                $ValidationResults += @{Test="CloudWatch Logs"; Status="PASS"; Details="Log group exists with recent events"}
            } else {
                Write-Host "❌ Recent Logs: No recent log events" -ForegroundColor Red
                $ValidationResults += @{Test="CloudWatch Logs"; Status="FAIL"; Details="No recent log events"}
            }
        } else {
            Write-Host "❌ CloudWatch Log Group: Not found" -ForegroundColor Red
            $ValidationResults += @{Test="CloudWatch Logs"; Status="FAIL"; Details="Log group not found"}
        }
    } catch {
        Write-Host "❌ CloudWatch Logs: Error accessing logs" -ForegroundColor Red
        $ValidationResults += @{Test="CloudWatch Logs"; Status="FAIL"; Details="Error accessing logs"}
    }

    # Generate Summary Report
    Write-Host ""
    Write-Host "📋 VALIDATION SUMMARY REPORT" -ForegroundColor Cyan
    Write-Host "=============================" -ForegroundColor Cyan
    
    $PassedTests = ($ValidationResults | Where-Object { $_.Status -eq "PASS" }).Count
    $FailedTests = ($ValidationResults | Where-Object { $_.Status -eq "FAIL" }).Count
    $TotalTests = $ValidationResults.Count
    
    Write-Host "Total Tests: $TotalTests" -ForegroundColor White
    Write-Host "Passed: $PassedTests" -ForegroundColor Green
    Write-Host "Failed: $FailedTests" -ForegroundColor Red
    Write-Host ""
    
    foreach ($result in $ValidationResults) {
        $color = if ($result.Status -eq "PASS") { "Green" } else { "Red" }
        $symbol = if ($result.Status -eq "PASS") { "✓" } else { "❌" }
        Write-Host "$symbol $($result.Test): $($result.Status)" -ForegroundColor $color
        Write-Host "   Details: $($result.Details)" -ForegroundColor Gray
    }
    
    Write-Host ""
    
    if ($FailedTests -eq 0) {
        Write-Host "🎉 ALL TESTS PASSED! Production setup is ready!" -ForegroundColor Green
        Write-Host ""
        Write-Host "🚀 DEPLOYMENT INFORMATION" -ForegroundColor Cyan
        Write-Host "=========================" -ForegroundColor Cyan
        if ($ALBDNSName) {
            Write-Host "Application URL: http://$ALBDNSName" -ForegroundColor Yellow
            Write-Host "Health Check: http://$ALBDNSName/health" -ForegroundColor Yellow
            Write-Host "API Documentation: http://$ALBDNSName/docs" -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host "Frontend Integration:" -ForegroundColor Cyan
        Write-Host "- Update API_CONFIG.BASE_URL to: http://$ALBDNSName" -ForegroundColor White
        Write-Host "- Deploy frontend to: https://www.legalizeme.site/counsel" -ForegroundColor White
        Write-Host "- Ensure CORS allows: https://www.legalizeme.site" -ForegroundColor White
    } else {
        Write-Host "❌ $FailedTests TESTS FAILED! Please fix issues before production deployment." -ForegroundColor Red
        Write-Host ""
        Write-Host "🔧 TROUBLESHOOTING STEPS:" -ForegroundColor Yellow
        Write-Host "1. Check AWS ECS service logs: aws logs tail /ecs/counsel-task --follow" -ForegroundColor White
        Write-Host "2. Verify ECS service status: aws ecs describe-services --cluster $ClusterName --services $ServiceName" -ForegroundColor White
        Write-Host "3. Check ALB target health: aws elbv2 describe-target-health --target-group-arn <target-group-arn>" -ForegroundColor White
        Write-Host "4. Review CloudWatch logs for errors" -ForegroundColor White
    }

}
catch {
    Write-Host "❌ Validation failed with error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Production Validation Complete!" -ForegroundColor Green
