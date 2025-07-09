# Fix ALB Health Check Configuration for Counsel AI
# This script updates the Application Load Balancer target group health check path

param(
    [string]$Region = "us-east-1",
    [string]$TargetGroupName = "counsel-targets",
    [string]$HealthCheckPath = "/health/live"
)

$ErrorActionPreference = "Stop"

Write-Host "🔧 Fixing ALB Health Check Configuration for Counsel AI" -ForegroundColor Blue

try {
    # Get Account ID
    $AccountId = (aws sts get-caller-identity --query Account --output text)
    Write-Host "✓ AWS Account ID: $AccountId" -ForegroundColor Green

    # Step 1: Find Target Group ARN
    Write-Host "🔍 Step 1: Finding Target Group..." -ForegroundColor Yellow
    
    $TargetGroupResult = aws elbv2 describe-target-groups --names $TargetGroupName --region $Region 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Target group '$TargetGroupName' not found. Please ensure ALB is deployed first." -ForegroundColor Red
        exit 1
    }
    
    $TargetGroupArn = (aws elbv2 describe-target-groups --names $TargetGroupName --region $Region --query "TargetGroups[0].TargetGroupArn" --output text)
    Write-Host "✓ Found Target Group: $TargetGroupArn" -ForegroundColor Green

    # Step 2: Get Current Health Check Configuration
    Write-Host "📋 Step 2: Checking Current Health Check Configuration..." -ForegroundColor Yellow
    
    $CurrentHealthCheck = aws elbv2 describe-target-groups --target-group-arns $TargetGroupArn --query "TargetGroups[0].HealthCheckPath" --output text
    Write-Host "Current Health Check Path: $CurrentHealthCheck" -ForegroundColor Cyan
    
    if ($CurrentHealthCheck -eq $HealthCheckPath) {
        Write-Host "✓ Health check path is already correctly configured!" -ForegroundColor Green
        Write-Host "No changes needed." -ForegroundColor Cyan
        exit 0
    }

    # Step 3: Update Health Check Configuration
    Write-Host "🔧 Step 3: Updating Health Check Configuration..." -ForegroundColor Yellow
    
    $UpdateResult = aws elbv2 modify-target-group --target-group-arn $TargetGroupArn --health-check-path $HealthCheckPath --health-check-interval-seconds 30 --health-check-timeout-seconds 10 --healthy-threshold-count 2 --unhealthy-threshold-count 3 --health-check-protocol HTTP --health-check-port traffic-port --region $Region | ConvertFrom-Json
    
    Write-Host "✓ Health check configuration updated successfully!" -ForegroundColor Green

    # Step 4: Verify the Update
    Write-Host "✅ Step 4: Verifying Health Check Update..." -ForegroundColor Yellow
    
    $UpdatedHealthCheck = aws elbv2 describe-target-groups --target-group-arns $TargetGroupArn --query "TargetGroups[0].HealthCheckPath" --output text
    Write-Host "Updated Health Check Path: $UpdatedHealthCheck" -ForegroundColor Cyan
    
    if ($UpdatedHealthCheck -eq $HealthCheckPath) {
        Write-Host "✓ Health check path successfully updated to: $HealthCheckPath" -ForegroundColor Green
    } else {
        Write-Host "❌ Health check update verification failed" -ForegroundColor Red
        exit 1
    }

    # Step 5: Check Target Health
    Write-Host "🏥 Step 5: Checking Target Health..." -ForegroundColor Yellow
    
    $TargetHealth = aws elbv2 describe-target-health --target-group-arn $TargetGroupArn --region $Region | ConvertFrom-Json
    
    if ($TargetHealth.TargetHealthDescriptions.Count -eq 0) {
        Write-Host "ℹ️ No targets currently registered in the target group" -ForegroundColor Cyan
    } else {
        Write-Host "Target Health Status:" -ForegroundColor Cyan
        foreach ($target in $TargetHealth.TargetHealthDescriptions) {
            $targetId = $target.Target.Id
            $targetPort = $target.Target.Port
            $healthState = $target.TargetHealth.State
            $description = $target.TargetHealth.Description
            
            $color = switch ($healthState) {
                "healthy" { "Green" }
                "unhealthy" { "Red" }
                "initial" { "Yellow" }
                "draining" { "Yellow" }
                default { "White" }
            }
            
            Write-Host "  - Target: $targetId:$targetPort - Status: $healthState" -ForegroundColor $color
            if ($description) {
                Write-Host "    Description: $description" -ForegroundColor Gray
            }
        }
    }

    # Output Summary
    Write-Host ""
    Write-Host "🎉 ALB Health Check Configuration Update Complete!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "Configuration Details:" -ForegroundColor Cyan
    Write-Host "- Target Group: $TargetGroupName" -ForegroundColor White
    Write-Host "- Target Group ARN: $TargetGroupArn" -ForegroundColor White
    Write-Host "- Health Check Path: $HealthCheckPath" -ForegroundColor White
    Write-Host "- Health Check Interval: 30 seconds" -ForegroundColor White
    Write-Host "- Health Check Timeout: 10 seconds" -ForegroundColor White
    Write-Host "- Healthy Threshold: 2 checks" -ForegroundColor White
    Write-Host "- Unhealthy Threshold: 3 checks" -ForegroundColor White
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "1. Wait 2-3 minutes for health checks to stabilize" -ForegroundColor White
    Write-Host "2. Verify application responds correctly at: $HealthCheckPath" -ForegroundColor White
    Write-Host "3. Monitor target health in AWS Console" -ForegroundColor White
    Write-Host ""
    Write-Host "✅ Health check is now configured for production use!" -ForegroundColor Green

}
catch {
    Write-Host "❌ Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Please check AWS permissions and ALB configuration." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ ALB Health Check Fix Complete!" -ForegroundColor Green
