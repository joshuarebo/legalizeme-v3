# Simple AWS Infrastructure Setup for Counsel AI ECS Fargate Deployment

$ErrorActionPreference = "Stop"

Write-Host "Creating AWS Infrastructure for Counsel AI..." -ForegroundColor Blue

try {
    # Get Account ID
    $AccountId = (aws sts get-caller-identity --query Account --output text)
    Write-Host "AWS Account ID: $AccountId" -ForegroundColor Green

    # Step 1: Create VPC
    Write-Host "Creating VPC..." -ForegroundColor Yellow
    $VpcResult = aws ec2 create-vpc --cidr-block 10.0.0.0/16 | ConvertFrom-Json
    $VpcId = $VpcResult.Vpc.VpcId
    Write-Host "VPC Created: $VpcId" -ForegroundColor Green

    # Enable DNS hostnames
    aws ec2 modify-vpc-attribute --vpc-id $VpcId --enable-dns-hostnames

    # Create Internet Gateway
    $IgwResult = aws ec2 create-internet-gateway | ConvertFrom-Json
    $IgwId = $IgwResult.InternetGateway.InternetGatewayId
    aws ec2 attach-internet-gateway --internet-gateway-id $IgwId --vpc-id $VpcId
    Write-Host "Internet Gateway Created: $IgwId" -ForegroundColor Green

    # Get Availability Zones
    $AZs = (aws ec2 describe-availability-zones --region us-east-1 --query "AvailabilityZones[0:2].ZoneName" --output text).Split("`t")
    
    # Create Public Subnets
    $PublicSubnet1Result = aws ec2 create-subnet --vpc-id $VpcId --cidr-block 10.0.1.0/24 --availability-zone $AZs[0] | ConvertFrom-Json
    $PublicSubnet1Id = $PublicSubnet1Result.Subnet.SubnetId
    
    $PublicSubnet2Result = aws ec2 create-subnet --vpc-id $VpcId --cidr-block 10.0.2.0/24 --availability-zone $AZs[1] | ConvertFrom-Json
    $PublicSubnet2Id = $PublicSubnet2Result.Subnet.SubnetId

    # Enable auto-assign public IP
    aws ec2 modify-subnet-attribute --subnet-id $PublicSubnet1Id --map-public-ip-on-launch
    aws ec2 modify-subnet-attribute --subnet-id $PublicSubnet2Id --map-public-ip-on-launch

    Write-Host "Public Subnets Created: $PublicSubnet1Id, $PublicSubnet2Id" -ForegroundColor Green

    # Create Route Table
    $RouteTableResult = aws ec2 create-route-table --vpc-id $VpcId | ConvertFrom-Json
    $RouteTableId = $RouteTableResult.RouteTable.RouteTableId
    
    # Add route to Internet Gateway
    aws ec2 create-route --route-table-id $RouteTableId --destination-cidr-block 0.0.0.0/0 --gateway-id $IgwId
    
    # Associate subnets with route table
    aws ec2 associate-route-table --subnet-id $PublicSubnet1Id --route-table-id $RouteTableId
    aws ec2 associate-route-table --subnet-id $PublicSubnet2Id --route-table-id $RouteTableId
    
    Write-Host "Route Table Configured: $RouteTableId" -ForegroundColor Green

    # Step 2: Create Security Groups
    Write-Host "Creating Security Groups..." -ForegroundColor Yellow
    
    # ALB Security Group
    $ALBSGResult = aws ec2 create-security-group --group-name counsel-alb-sg --description "Security group for Counsel ALB" --vpc-id $VpcId | ConvertFrom-Json
    $ALBSGId = $ALBSGResult.GroupId
    
    # Allow HTTP and HTTPS traffic
    aws ec2 authorize-security-group-ingress --group-id $ALBSGId --protocol tcp --port 80 --cidr 0.0.0.0/0
    aws ec2 authorize-security-group-ingress --group-id $ALBSGId --protocol tcp --port 443 --cidr 0.0.0.0/0
    
    # ECS Security Group
    $ECSGResult = aws ec2 create-security-group --group-name counsel-ecs-sg --description "Security group for Counsel ECS tasks" --vpc-id $VpcId | ConvertFrom-Json
    $ECSGId = $ECSGResult.GroupId
    
    # Allow traffic from ALB
    aws ec2 authorize-security-group-ingress --group-id $ECSGId --protocol tcp --port 8000 --source-group $ALBSGId
    
    Write-Host "Security Groups Created: ALB($ALBSGId), ECS($ECSGId)" -ForegroundColor Green

    # Step 3: Create Application Load Balancer
    Write-Host "Creating Application Load Balancer..." -ForegroundColor Yellow
    
    $ALBResult = aws elbv2 create-load-balancer --name counsel-alb --subnets $PublicSubnet1Id $PublicSubnet2Id --security-groups $ALBSGId --scheme internet-facing --type application --ip-address-type ipv4 | ConvertFrom-Json
    $ALBArn = $ALBResult.LoadBalancers[0].LoadBalancerArn
    $ALBDNSName = $ALBResult.LoadBalancers[0].DNSName
    
    Write-Host "ALB Created: $ALBDNSName" -ForegroundColor Green

    # Create Target Group
    $TargetGroupResult = aws elbv2 create-target-group --name counsel-targets --protocol HTTP --port 8000 --vpc-id $VpcId --target-type ip --health-check-path "/health" --health-check-interval-seconds 30 --health-check-timeout-seconds 10 --healthy-threshold-count 2 --unhealthy-threshold-count 3 | ConvertFrom-Json
    $TargetGroupArn = $TargetGroupResult.TargetGroups[0].TargetGroupArn
    
    Write-Host "Target Group Created: $TargetGroupArn" -ForegroundColor Green

    # Create Listener
    $ListenerResult = aws elbv2 create-listener --load-balancer-arn $ALBArn --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$TargetGroupArn | ConvertFrom-Json
    $ListenerArn = $ListenerResult.Listeners[0].ListenerArn
    
    Write-Host "ALB Listener Created: $ListenerArn" -ForegroundColor Green

    # Step 4: Register Task Definition
    Write-Host "Registering ECS Task Definition..." -ForegroundColor Yellow
    
    $TaskDefResult = aws ecs register-task-definition --cli-input-json file://aws-ecs-deployment.json | ConvertFrom-Json
    $TaskDefArn = $TaskDefResult.taskDefinition.taskDefinitionArn
    
    Write-Host "Task Definition Registered: $TaskDefArn" -ForegroundColor Green

    # Step 5: Create ECS Service
    Write-Host "Creating ECS Service..." -ForegroundColor Yellow
    
    $ServiceConfig = @"
{
    "serviceName": "counsel-service",
    "cluster": "counsel-cluster",
    "taskDefinition": "$TaskDefArn",
    "desiredCount": 1,
    "launchType": "FARGATE",
    "networkConfiguration": {
        "awsvpcConfiguration": {
            "subnets": ["$PublicSubnet1Id", "$PublicSubnet2Id"],
            "securityGroups": ["$ECSGId"],
            "assignPublicIp": "ENABLED"
        }
    },
    "loadBalancers": [
        {
            "targetGroupArn": "$TargetGroupArn",
            "containerName": "counsel-container",
            "containerPort": 8000
        }
    ],
    "healthCheckGracePeriodSeconds": 120
}
"@
    
    $ServiceConfig | Out-File "service-config.json" -Encoding UTF8
    
    $ServiceResult = aws ecs create-service --cli-input-json file://service-config.json | ConvertFrom-Json
    $ServiceArn = $ServiceResult.service.serviceArn
    
    Write-Host "ECS Service Created: $ServiceArn" -ForegroundColor Green

    # Output Summary
    Write-Host ""
    Write-Host "Infrastructure Deployment Complete!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "Application URL: http://$ALBDNSName" -ForegroundColor Yellow
    Write-Host "Health Check: http://$ALBDNSName/health" -ForegroundColor Yellow
    Write-Host "API Documentation: http://$ALBDNSName/docs" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Infrastructure Details:" -ForegroundColor Cyan
    Write-Host "- VPC ID: $VpcId" -ForegroundColor White
    Write-Host "- ALB DNS: $ALBDNSName" -ForegroundColor White
    Write-Host "- ECS Cluster: counsel-cluster" -ForegroundColor White
    Write-Host "- ECS Service: counsel-service" -ForegroundColor White
    Write-Host "- Target Group: $TargetGroupArn" -ForegroundColor White
    Write-Host ""
    Write-Host "Service is starting up... This may take 2-3 minutes." -ForegroundColor Yellow

}
catch {
    Write-Host "Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    # Cleanup temporary files
    if (Test-Path "service-config.json") { Remove-Item "service-config.json" }
}

Write-Host "AWS ECS Fargate Deployment Complete!" -ForegroundColor Green
