# AWS Deployment Script for Counsel AI - Phase 1: Interactive Citations
# PowerShell script for Windows deployment

param(
    [Parameter(Mandatory=$true)]
    [string]$AwsAccountId,

    [Parameter(Mandatory=$false)]
    [string]$AwsRegion = "us-east-1",

    [Parameter(Mandatory=$false)]
    [string]$EcsCluster = "counsel-ai-cluster",

    [Parameter(Mandatory=$false)]
    [string]$EcsService = "counsel-ai-backend",

    [Parameter(Mandatory=$false)]
    [switch]$SkipTests,

    [Parameter(Mandatory=$false)]
    [switch]$SkipMigration,

    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors for output
function Write-Success { param($msg) Write-Host "✓ $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "ℹ $msg" -ForegroundColor Cyan }
function Write-Warning { param($msg) Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "✗ $msg" -ForegroundColor Red }
function Write-Step { param($step, $msg) Write-Host "`n[$step] $msg" -ForegroundColor Magenta }

# Configuration
$IMAGE_NAME = "counsel-ai-backend"
$IMAGE_TAG = "phase1-citations-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$ECR_REPOSITORY = "$AwsAccountId.dkr.ecr.$AwsRegion.amazonaws.com/$IMAGE_NAME"

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  AWS Deployment: Counsel AI - Interactive Citations Phase 1  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Info "Configuration:"
Write-Info "  AWS Account: $AwsAccountId"
Write-Info "  Region: $AwsRegion"
Write-Info "  ECS Cluster: $EcsCluster"
Write-Info "  ECS Service: $EcsService"
Write-Info "  Image Tag: $IMAGE_TAG"
Write-Info "  Dry Run: $DryRun"

if ($DryRun) {
    Write-Warning "DRY RUN MODE - No actual changes will be made"
}

# Step 1: Pre-deployment Tests
if (-not $SkipTests) {
    Write-Step "1/8" "Running Pre-Deployment Tests"

    try {
        Write-Info "Testing database schema..."
        python scripts/test_steps_1_3_and_1_4.py
        Write-Success "Database schema tests passed"

        Write-Info "Testing agent mode structure..."
        python scripts/test_agent_mode_citations.py
        Write-Success "Agent mode tests passed"

        Write-Info "Testing citation utilities..."
        python scripts/test_enhanced_rag_step_1_2.py
        Write-Success "Citation utility tests passed"
    }
    catch {
        Write-Error "Pre-deployment tests failed: $_"
        exit 1
    }
} else {
    Write-Warning "Skipping pre-deployment tests"
}

# Step 2: Git Status Check
Write-Step "2/8" "Checking Git Status"

$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Warning "Uncommitted changes detected:"
    git status --short

    $continue = Read-Host "Continue deployment? (y/N)"
    if ($continue -ne "y") {
        Write-Info "Deployment cancelled"
        exit 0
    }
} else {
    Write-Success "Working directory clean"
}

$currentBranch = git branch --show-current
Write-Info "Current branch: $currentBranch"

# Step 3: Build Docker Image
Write-Step "3/8" "Building Docker Image"

if (-not $DryRun) {
    try {
        Write-Info "Building image: ${IMAGE_NAME}:${IMAGE_TAG}"
        docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

        Write-Info "Tagging for ECR..."
        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REPOSITORY}:${IMAGE_TAG}
        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ECR_REPOSITORY}:latest

        Write-Success "Docker image built successfully"

        # Verify image
        $imageExists = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String "${IMAGE_NAME}:${IMAGE_TAG}"
        if ($imageExists) {
            Write-Success "Image verified: $imageExists"
        }
    }
    catch {
        Write-Error "Docker build failed: $_"
        exit 1
    }
} else {
    Write-Info "[DRY RUN] Would build: ${IMAGE_NAME}:${IMAGE_TAG}"
}

# Step 4: Push to ECR
Write-Step "4/8" "Pushing to Amazon ECR"

if (-not $DryRun) {
    try {
        Write-Info "Logging in to ECR..."
        aws ecr get-login-password --region $AwsRegion | docker login --username AWS --password-stdin $ECR_REPOSITORY

        Write-Info "Pushing versioned image..."
        docker push ${ECR_REPOSITORY}:${IMAGE_TAG}

        Write-Info "Pushing latest tag..."
        docker push ${ECR_REPOSITORY}:latest

        Write-Success "Images pushed to ECR"
    }
    catch {
        Write-Error "ECR push failed: $_"
        exit 1
    }
} else {
    Write-Info "[DRY RUN] Would push to: $ECR_REPOSITORY"
}

# Step 5: Database Migration
if (-not $SkipMigration) {
    Write-Step "5/8" "Running Database Migration"

    Write-Warning "Database migration should be run manually on RDS"
    Write-Info "Migration file: migrations/001_add_interactive_source_fields.sql"
    Write-Info "Command: psql -h RDS_ENDPOINT -U counsel_admin -d counsel -f migrations/001_add_interactive_source_fields.sql"

    $runMigration = Read-Host "Have you run the database migration? (y/N)"
    if ($runMigration -ne "y") {
        Write-Error "Please run database migration before continuing"
        exit 1
    }

    Write-Success "Database migration confirmed"
} else {
    Write-Warning "Skipping database migration"
}

# Step 6: Update ECS Service
Write-Step "6/8" "Updating ECS Service"

if (-not $DryRun) {
    try {
        # Get current task definition
        Write-Info "Getting current task definition..."
        $taskDefArn = aws ecs describe-services `
            --cluster $EcsCluster `
            --services $EcsService `
            --query 'services[0].taskDefinition' `
            --output text

        Write-Info "Current task definition: $taskDefArn"

        # Get task definition details
        $taskDef = aws ecs describe-task-definition `
            --task-definition $taskDefArn `
            --query 'taskDefinition' | ConvertFrom-Json

        # Update image in container definitions
        $containerDef = $taskDef.containerDefinitions[0]
        $oldImage = $containerDef.image
        $containerDef.image = "${ECR_REPOSITORY}:${IMAGE_TAG}"

        Write-Info "Updating image:"
        Write-Info "  From: $oldImage"
        Write-Info "  To:   ${ECR_REPOSITORY}:${IMAGE_TAG}"

        # Remove fields that can't be used in registration
        $taskDef.PSObject.Properties.Remove('taskDefinitionArn')
        $taskDef.PSObject.Properties.Remove('revision')
        $taskDef.PSObject.Properties.Remove('status')
        $taskDef.PSObject.Properties.Remove('requiresAttributes')
        $taskDef.PSObject.Properties.Remove('compatibilities')
        $taskDef.PSObject.Properties.Remove('registeredAt')
        $taskDef.PSObject.Properties.Remove('registeredBy')

        # Save updated task definition
        $taskDefJson = $taskDef | ConvertTo-Json -Depth 10
        $taskDefJson | Out-File -FilePath "temp-task-def.json" -Encoding UTF8

        # Register new task definition
        Write-Info "Registering new task definition..."
        $newTaskDef = aws ecs register-task-definition --cli-input-json file://temp-task-def.json | ConvertFrom-Json
        $newRevision = $newTaskDef.taskDefinition.revision

        Write-Success "New task definition registered: revision $newRevision"

        # Update service
        Write-Info "Updating ECS service..."
        aws ecs update-service `
            --cluster $EcsCluster `
            --service $EcsService `
            --task-definition "$($taskDef.family):$newRevision" `
            --force-new-deployment | Out-Null

        Write-Success "ECS service update initiated"

        # Clean up temp file
        Remove-Item -Path "temp-task-def.json" -Force
    }
    catch {
        Write-Error "ECS service update failed: $_"
        if (Test-Path "temp-task-def.json") {
            Remove-Item -Path "temp-task-def.json" -Force
        }
        exit 1
    }
} else {
    Write-Info "[DRY RUN] Would update ECS service: $EcsService"
}

# Step 7: Wait for Deployment Stabilization
Write-Step "7/8" "Waiting for Deployment to Stabilize"

if (-not $DryRun) {
    try {
        Write-Info "Monitoring deployment progress..."
        Write-Info "This may take 10-15 minutes..."

        $startTime = Get-Date
        $timeout = 1200  # 20 minutes

        while (((Get-Date) - $startTime).TotalSeconds -lt $timeout) {
            $service = aws ecs describe-services `
                --cluster $EcsCluster `
                --services $EcsService `
                --query 'services[0]' | ConvertFrom-Json

            $deployments = $service.deployments
            $primaryDeployment = $deployments | Where-Object { $_.status -eq "PRIMARY" }

            if ($deployments.Count -eq 1 -and $primaryDeployment.runningCount -eq $primaryDeployment.desiredCount) {
                Write-Success "Deployment stabilized!"
                Write-Info "Running count: $($primaryDeployment.runningCount)/$($primaryDeployment.desiredCount)"
                break
            }

            Write-Info "Deployment in progress... Running: $($primaryDeployment.runningCount)/$($primaryDeployment.desiredCount)"
            Start-Sleep -Seconds 30
        }

        if (((Get-Date) - $startTime).TotalSeconds -ge $timeout) {
            Write-Error "Deployment timeout - check AWS console for details"
            exit 1
        }
    }
    catch {
        Write-Error "Deployment monitoring failed: $_"
        exit 1
    }
} else {
    Write-Info "[DRY RUN] Would wait for deployment stabilization"
}

# Step 8: Post-Deployment Verification
Write-Step "8/8" "Running Post-Deployment Verification"

if (-not $DryRun) {
    Write-Info "Waiting 30 seconds for services to be ready..."
    Start-Sleep -Seconds 30

    # Get ALB DNS
    $albDns = "api.legalizeme.co.ke"  # Update with your actual ALB DNS

    Write-Info "Testing endpoints on: https://$albDns"

    # Test health endpoint
    try {
        $healthResponse = Invoke-RestMethod -Uri "https://$albDns/api/v1/health" -Method Get
        Write-Success "Health check: $($healthResponse.status)"
    }
    catch {
        Write-Warning "Health check failed: $_"
    }

    # Test enhanced RAG with citations
    try {
        $queryBody = @{
            query = "What is the notice period for employment termination in Kenya?"
            use_enhanced_rag = $true
            agent_mode = $false
        } | ConvertTo-Json

        $ragResponse = Invoke-RestMethod -Uri "https://$albDns/api/v1/counsel/query" -Method Post -Body $queryBody -ContentType "application/json"

        if ($ragResponse.sources -and $ragResponse.citation_map) {
            Write-Success "Enhanced RAG working with citations"
            Write-Info "  Found $($ragResponse.sources.Count) sources"
            Write-Info "  Citations: $($ragResponse.citation_map.Keys -join ', ')"
        } else {
            Write-Warning "Enhanced RAG response missing citations"
        }
    }
    catch {
        Write-Warning "Enhanced RAG test failed: $_"
    }

    Write-Success "Deployment verification complete"
} else {
    Write-Info "[DRY RUN] Would verify deployment"
}

# Summary
Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                  Deployment Complete!                          ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green

Write-Info "`nDeployment Summary:"
Write-Info "  Image: ${ECR_REPOSITORY}:${IMAGE_TAG}"
Write-Info "  ECS Service: $EcsService"
Write-Info "  Region: $AwsRegion"
Write-Info "`nNext Steps:"
Write-Info "  1. Monitor CloudWatch logs for errors"
Write-Info "  2. Check application metrics in CloudWatch"
Write-Info "  3. Test all endpoints thoroughly"
Write-Info "  4. Notify frontend team of deployment"

Write-Host "`nDeployment completed at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Green
