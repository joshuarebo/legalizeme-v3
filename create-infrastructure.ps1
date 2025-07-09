# Complete AWS Infrastructure Setup for Counsel AI ECS Fargate Deployment
# This script creates VPC, ALB, ECS Service, and all required infrastructure

param(
    [string]$Region = "us-east-1",
    [string]$ClusterName = "counsel-cluster",
    [string]$ServiceName = "counsel-service",
    [string]$VpcName = "counsel-vpc",
    [string]$ALBName = "counsel-alb",
    [string]$TargetGroupName = "counsel-targets"
)

$ErrorActionPreference = "Stop"

Write-Host "🏗️ Creating Complete AWS Infrastructure for Counsel AI" -ForegroundColor Blue

try {
    # Get Account ID
    $AccountId = (aws sts get-caller-identity --query Account --output text)
    Write-Host "✓ AWS Account ID: $AccountId" -ForegroundColor Green

    # Step 1: Create VPC and Networking
    Write-Host "🌐 Step 1: Creating VPC and Networking..." -ForegroundColor Yellow
    
    # Create VPC
    $VpcResult = aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$($VpcName)}]" | ConvertFrom-Json
    $VpcId = $VpcResult.Vpc.VpcId
    Write-Host "✓ VPC Created: $VpcId" -ForegroundColor Green

    # Enable DNS hostnames
    aws ec2 modify-vpc-attribute --vpc-id $VpcId --enable-dns-hostnames

    # Create Internet Gateway
    $IgwResult = aws ec2 create-internet-gateway --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=$($VpcName)-igw}]" | ConvertFrom-Json
    $IgwId = $IgwResult.InternetGateway.InternetGatewayId
    aws ec2 attach-internet-gateway --internet-gateway-id $IgwId --vpc-id $VpcId
    Write-Host "✓ Internet Gateway Created: $IgwId" -ForegroundColor Green

    # Get Availability Zones
    $AZs = (aws ec2 describe-availability-zones --region $Region --query "AvailabilityZones[0:2].ZoneName" --output text).Split("`t")
    
    # Create Public Subnets
    $PublicSubnet1Result = aws ec2 create-subnet --vpc-id $VpcId --cidr-block 10.0.1.0/24 --availability-zone $AZs[0] --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$($VpcName)-public-1}]" | ConvertFrom-Json
    $PublicSubnet1Id = $PublicSubnet1Result.Subnet.SubnetId

    $PublicSubnet2Result = aws ec2 create-subnet --vpc-id $VpcId --cidr-block 10.0.2.0/24 --availability-zone $AZs[1] --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$($VpcName)-public-2}]" | ConvertFrom-Json
    $PublicSubnet2Id = $PublicSubnet2Result.Subnet.SubnetId

    # Enable auto-assign public IP
    aws ec2 modify-subnet-attribute --subnet-id $PublicSubnet1Id --map-public-ip-on-launch
    aws ec2 modify-subnet-attribute --subnet-id $PublicSubnet2Id --map-public-ip-on-launch

    Write-Host "✓ Public Subnets Created: $PublicSubnet1Id, $PublicSubnet2Id" -ForegroundColor Green

    # Create Route Table
    $RouteTableResult = aws ec2 create-route-table --vpc-id $VpcId --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=$($VpcName)-public-rt}]" | ConvertFrom-Json
    $RouteTableId = $RouteTableResult.RouteTable.RouteTableId
    
    # Add route to Internet Gateway
    aws ec2 create-route --route-table-id $RouteTableId --destination-cidr-block 0.0.0.0/0 --gateway-id $IgwId
    
    # Associate subnets with route table
    aws ec2 associate-route-table --subnet-id $PublicSubnet1Id --route-table-id $RouteTableId
    aws ec2 associate-route-table --subnet-id $PublicSubnet2Id --route-table-id $RouteTableId
    
    Write-Host "✓ Route Table Configured: $RouteTableId" -ForegroundColor Green

    # Step 2: Create Security Groups
    Write-Host "🔒 Step 2: Creating Security Groups..." -ForegroundColor Yellow
    
    # ALB Security Group
    $ALBSGResult = aws ec2 create-security-group --group-name counsel-alb-sg --description "Security group for Counsel ALB" --vpc-id $VpcId --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=counsel-alb-sg}]" | ConvertFrom-Json
    $ALBSGId = $ALBSGResult.GroupId
    
    # Allow HTTP and HTTPS traffic
    aws ec2 authorize-security-group-ingress --group-id $ALBSGId --protocol tcp --port 80 --cidr 0.0.0.0/0
    aws ec2 authorize-security-group-ingress --group-id $ALBSGId --protocol tcp --port 443 --cidr 0.0.0.0/0
    
    # ECS Security Group
    $ECSGResult = aws ec2 create-security-group --group-name counsel-ecs-sg --description "Security group for Counsel ECS tasks" --vpc-id $VpcId --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=counsel-ecs-sg}]" | ConvertFrom-Json
    $ECSGId = $ECSGResult.GroupId
    
    # Allow traffic from ALB
    aws ec2 authorize-security-group-ingress --group-id $ECSGId --protocol tcp --port 8000 --source-group $ALBSGId
    
    Write-Host "✓ Security Groups Created: ALB($ALBSGId), ECS($ECSGId)" -ForegroundColor Green

    # Step 3: Create RDS PostgreSQL Database
    Write-Host "🗄️ Step 3: Creating RDS PostgreSQL Database..." -ForegroundColor Yellow

    # Create DB Subnet Group
    $DBSubnetGroupResult = aws rds create-db-subnet-group --db-subnet-group-name counsel-db-subnet-group --db-subnet-group-description "Subnet group for Counsel AI database" --subnet-ids $PublicSubnet1Id $PublicSubnet2Id --tags "Key=Name,Value=counsel-db-subnet-group" | ConvertFrom-Json
    $DBSubnetGroupName = $DBSubnetGroupResult.DBSubnetGroup.DBSubnetGroupName
    Write-Host "✓ DB Subnet Group Created: $DBSubnetGroupName" -ForegroundColor Green

    # Create DB Security Group
    $DBSGResult = aws ec2 create-security-group --group-name counsel-db-sg --description "Security group for Counsel PostgreSQL database" --vpc-id $VpcId --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=counsel-db-sg}]" | ConvertFrom-Json
    $DBSGId = $DBSGResult.GroupId

    # Allow PostgreSQL access from ECS tasks
    aws ec2 authorize-security-group-ingress --group-id $DBSGId --protocol tcp --port 5432 --source-group $ECSGId
    Write-Host "✓ DB Security Group Created: $DBSGId" -ForegroundColor Green

    # Create RDS PostgreSQL Instance
    $DBInstanceResult = aws rds create-db-instance --db-instance-identifier counsel-db --db-instance-class db.t3.micro --engine postgres --engine-version "15.4" --master-username counseladmin --master-user-password "CounselAI2025SecurePass!" --allocated-storage 20 --storage-type gp2 --vpc-security-group-ids $DBSGId --db-subnet-group-name $DBSubnetGroupName --backup-retention-period 7 --multi-az false --publicly-accessible false --storage-encrypted true --tags "Key=Name,Value=counsel-db" "Key=Environment,Value=production" | ConvertFrom-Json
    $DBInstanceId = $DBInstanceResult.DBInstance.DBInstanceIdentifier
    Write-Host "✓ RDS PostgreSQL Instance Creating: $DBInstanceId (this may take 5-10 minutes)" -ForegroundColor Green

    # Wait for DB to be available (optional - can be done in background)
    Write-Host "⏳ Waiting for database to become available..." -ForegroundColor Yellow
    aws rds wait db-instance-available --db-instance-identifier $DBInstanceId

    # Get DB endpoint
    $DBEndpointResult = aws rds describe-db-instances --db-instance-identifier $DBInstanceId --query "DBInstances[0].Endpoint.Address" --output text
    Write-Host "✓ Database Available at: $DBEndpointResult" -ForegroundColor Green

    # Store database connection string in Parameter Store
    $DatabaseURL = "postgresql://counseladmin:CounselAI2025SecurePass!@${DBEndpointResult}:5432/postgres"
    aws ssm put-parameter --name "/counsel/database-url" --value $DatabaseURL --type "SecureString" --description "PostgreSQL connection string for Counsel AI"
    Write-Host "✓ Database URL stored in Parameter Store" -ForegroundColor Green

    # Step 4: Create Application Load Balancer
    Write-Host "⚖️ Step 4: Creating Application Load Balancer..." -ForegroundColor Yellow
    
    $ALBResult = aws elbv2 create-load-balancer --name $ALBName --subnets $PublicSubnet1Id $PublicSubnet2Id --security-groups $ALBSGId --scheme internet-facing --type application --ip-address-type ipv4 | ConvertFrom-Json
    $ALBArn = $ALBResult.LoadBalancers[0].LoadBalancerArn
    $ALBDNSName = $ALBResult.LoadBalancers[0].DNSName
    
    Write-Host "✓ ALB Created: $ALBDNSName" -ForegroundColor Green

    # Create Target Group with updated health check path
    $TargetGroupResult = aws elbv2 create-target-group --name $TargetGroupName --protocol HTTP --port 8000 --vpc-id $VpcId --target-type ip --health-check-path "/health/live" --health-check-interval-seconds 30 --health-check-timeout-seconds 10 --healthy-threshold-count 2 --unhealthy-threshold-count 3 | ConvertFrom-Json
    $TargetGroupArn = $TargetGroupResult.TargetGroups[0].TargetGroupArn
    
    Write-Host "✓ Target Group Created: $TargetGroupArn" -ForegroundColor Green

    # Create Listener
    $ListenerResult = aws elbv2 create-listener --load-balancer-arn $ALBArn --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$TargetGroupArn | ConvertFrom-Json
    $ListenerArn = $ListenerResult.Listeners[0].ListenerArn
    
    Write-Host "✓ ALB Listener Created: $ListenerArn" -ForegroundColor Green

    # Step 5: Register Task Definition
    Write-Host "📋 Step 5: Registering ECS Task Definition..." -ForegroundColor Yellow
    
    # Update task definition with actual values
    $TaskDefinition = Get-Content "aws-ecs-deployment.json" | ConvertFrom-Json
    $TaskDefinition.executionRoleArn = $TaskDefinition.executionRoleArn -replace "ACCOUNT_ID", $AccountId
    $TaskDefinition.taskRoleArn = $TaskDefinition.taskRoleArn -replace "ACCOUNT_ID", $AccountId
    $TaskDefinition.containerDefinitions[0].image = $TaskDefinition.containerDefinitions[0].image -replace "ACCOUNT_ID", $AccountId
    
    # Update secrets ARNs
    foreach ($secret in $TaskDefinition.containerDefinitions[0].secrets) {
        $secret.valueFrom = $secret.valueFrom -replace "ACCOUNT_ID", $AccountId
    }
    
    $TaskDefinition | ConvertTo-Json -Depth 10 | Out-File "task-definition-final.json" -Encoding UTF8
    
    $TaskDefResult = aws ecs register-task-definition --cli-input-json file://task-definition-final.json | ConvertFrom-Json
    $TaskDefArn = $TaskDefResult.taskDefinition.taskDefinitionArn
    
    Write-Host "✓ Task Definition Registered: $TaskDefArn" -ForegroundColor Green

    # Step 6: Create ECS Service
    Write-Host "🚀 Step 6: Creating ECS Service..." -ForegroundColor Yellow
    
    $ServiceConfig = @{
        serviceName = $ServiceName
        cluster = $ClusterName
        taskDefinition = $TaskDefArn
        desiredCount = 1
        launchType = "FARGATE"
        networkConfiguration = @{
            awsvpcConfiguration = @{
                subnets = @($PublicSubnet1Id, $PublicSubnet2Id)
                securityGroups = @($ECSGId)
                assignPublicIp = "ENABLED"
            }
        }
        loadBalancers = @(
            @{
                targetGroupArn = $TargetGroupArn
                containerName = "counsel-container"
                containerPort = 8000
            }
        )
        healthCheckGracePeriodSeconds = 120
    } | ConvertTo-Json -Depth 10
    
    $ServiceConfig | Out-File "service-config.json" -Encoding UTF8
    
    $ServiceResult = aws ecs create-service --cli-input-json file://service-config.json | ConvertFrom-Json
    $ServiceArn = $ServiceResult.service.serviceArn
    
    Write-Host "✓ ECS Service Created: $ServiceArn" -ForegroundColor Green

    # Output Summary
    Write-Host ""
    Write-Host "🎉 Infrastructure Deployment Complete!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "Application URL: http://$ALBDNSName" -ForegroundColor Yellow
    Write-Host "Health Check: http://$ALBDNSName/health" -ForegroundColor Yellow
    Write-Host "API Documentation: http://$ALBDNSName/docs" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Infrastructure Details:" -ForegroundColor Cyan
    Write-Host "- VPC ID: $VpcId" -ForegroundColor White
    Write-Host "- ALB DNS: $ALBDNSName" -ForegroundColor White
    Write-Host "- ECS Cluster: $ClusterName" -ForegroundColor White
    Write-Host "- ECS Service: $ServiceName" -ForegroundColor White
    Write-Host "- Target Group: $TargetGroupArn" -ForegroundColor White
    Write-Host ""
    Write-Host "⏳ Service is starting up... This may take 2-3 minutes." -ForegroundColor Yellow
    Write-Host "Monitor deployment: aws ecs describe-services --cluster $ClusterName --services $ServiceName" -ForegroundColor Cyan

}
catch {
    Write-Host "❌ Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Rolling back resources..." -ForegroundColor Yellow
    # Add rollback logic here if needed
    exit 1
}
finally {
    # Cleanup temporary files
    if (Test-Path "task-definition-final.json") { Remove-Item "task-definition-final.json" }
    if (Test-Path "service-config.json") { Remove-Item "service-config.json" }
}

Write-Host "AWS ECS Fargate Deployment Complete!" -ForegroundColor Green
