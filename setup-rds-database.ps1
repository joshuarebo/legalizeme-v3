# AWS RDS PostgreSQL Setup Script for Counsel AI
# This script creates a production-ready PostgreSQL database for the Counsel AI application

param(
    [string]$Region = "us-east-1",
    [string]$DBInstanceId = "counsel-db",
    [string]$DBUsername = "counseladmin",
    [string]$DBPassword = "CounselAI2025SecurePass!",
    [string]$VpcId = "",
    [string]$SubnetId1 = "",
    [string]$SubnetId2 = "",
    [string]$ECSSecurityGroupId = ""
)

$ErrorActionPreference = "Stop"

Write-Host "🗄️ Setting up AWS RDS PostgreSQL Database for Counsel AI" -ForegroundColor Blue

try {
    # Get Account ID
    $AccountId = (aws sts get-caller-identity --query Account --output text)
    Write-Host "✓ AWS Account ID: $AccountId" -ForegroundColor Green

    # If VPC parameters not provided, try to find existing ones
    if (-not $VpcId) {
        Write-Host "🔍 Looking for existing VPC..." -ForegroundColor Yellow
        $VpcResult = aws ec2 describe-vpcs --filters "Name=tag:Name,Values=counsel-vpc" --query "Vpcs[0].VpcId" --output text
        if ($VpcResult -ne "None") {
            $VpcId = $VpcResult
            Write-Host "✓ Found existing VPC: $VpcId" -ForegroundColor Green
        } else {
            Write-Host "❌ No VPC found. Please run create-infrastructure.ps1 first or provide VPC parameters." -ForegroundColor Red
            exit 1
        }
    }

    # Get subnets if not provided
    if (-not $SubnetId1 -or -not $SubnetId2) {
        Write-Host "🔍 Looking for existing subnets..." -ForegroundColor Yellow
        $SubnetResults = aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VpcId" "Name=tag:Name,Values=counsel-vpc-public-*" --query "Subnets[].SubnetId" --output text
        $Subnets = $SubnetResults.Split("`t")
        if ($Subnets.Count -ge 2) {
            $SubnetId1 = $Subnets[0]
            $SubnetId2 = $Subnets[1]
            Write-Host "✓ Found subnets: $SubnetId1, $SubnetId2" -ForegroundColor Green
        } else {
            Write-Host "❌ Insufficient subnets found. Please provide subnet IDs." -ForegroundColor Red
            exit 1
        }
    }

    # Get ECS security group if not provided
    if (-not $ECSSecurityGroupId) {
        Write-Host "🔍 Looking for ECS security group..." -ForegroundColor Yellow
        $ECSSecurityGroupResult = aws ec2 describe-security-groups --filters "Name=group-name,Values=counsel-ecs-sg" --query "SecurityGroups[0].GroupId" --output text
        if ($ECSSecurityGroupResult -ne "None") {
            $ECSSecurityGroupId = $ECSSecurityGroupResult
            Write-Host "✓ Found ECS security group: $ECSSecurityGroupId" -ForegroundColor Green
        } else {
            Write-Host "❌ ECS security group not found. Please run create-infrastructure.ps1 first." -ForegroundColor Red
            exit 1
        }
    }

    # Step 1: Create DB Subnet Group
    Write-Host "📋 Step 1: Creating DB Subnet Group..." -ForegroundColor Yellow
    
    # Check if subnet group already exists
    $ExistingSubnetGroup = aws rds describe-db-subnet-groups --db-subnet-group-name counsel-db-subnet-group 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ DB Subnet Group already exists" -ForegroundColor Green
    } else {
        $DBSubnetGroupResult = aws rds create-db-subnet-group --db-subnet-group-name counsel-db-subnet-group --db-subnet-group-description "Subnet group for Counsel AI database" --subnet-ids $SubnetId1 $SubnetId2 --tags "Key=Name,Value=counsel-db-subnet-group" "Key=Environment,Value=production" | ConvertFrom-Json
        Write-Host "✓ DB Subnet Group Created: counsel-db-subnet-group" -ForegroundColor Green
    }

    # Step 2: Create DB Security Group
    Write-Host "🔒 Step 2: Creating DB Security Group..." -ForegroundColor Yellow
    
    # Check if security group already exists
    $ExistingDBSG = aws ec2 describe-security-groups --filters "Name=group-name,Values=counsel-db-sg" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $DBSGId = (aws ec2 describe-security-groups --filters "Name=group-name,Values=counsel-db-sg" --query "SecurityGroups[0].GroupId" --output text)
        Write-Host "✓ DB Security Group already exists: $DBSGId" -ForegroundColor Green
    } else {
        $DBSGResult = aws ec2 create-security-group --group-name counsel-db-sg --description "Security group for Counsel PostgreSQL database" --vpc-id $VpcId --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=counsel-db-sg},{Key=Environment,Value=production}]" | ConvertFrom-Json
        $DBSGId = $DBSGResult.GroupId
        
        # Allow PostgreSQL access from ECS tasks
        aws ec2 authorize-security-group-ingress --group-id $DBSGId --protocol tcp --port 5432 --source-group $ECSSecurityGroupId
        Write-Host "✓ DB Security Group Created: $DBSGId" -ForegroundColor Green
    }

    # Step 3: Create RDS PostgreSQL Instance
    Write-Host "🗄️ Step 3: Creating RDS PostgreSQL Instance..." -ForegroundColor Yellow
    
    # Check if DB instance already exists
    $ExistingDB = aws rds describe-db-instances --db-instance-identifier $DBInstanceId 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ RDS Instance already exists: $DBInstanceId" -ForegroundColor Green
        $DBEndpoint = (aws rds describe-db-instances --db-instance-identifier $DBInstanceId --query "DBInstances[0].Endpoint.Address" --output text)
    } else {
        $DBInstanceResult = aws rds create-db-instance --db-instance-identifier $DBInstanceId --db-instance-class db.t3.micro --engine postgres --engine-version "15.4" --master-username $DBUsername --master-user-password $DBPassword --allocated-storage 20 --storage-type gp2 --vpc-security-group-ids $DBSGId --db-subnet-group-name counsel-db-subnet-group --backup-retention-period 7 --multi-az false --publicly-accessible false --storage-encrypted true --tags "Key=Name,Value=$DBInstanceId" "Key=Environment,Value=production" "Key=Application,Value=counsel-ai" | ConvertFrom-Json
        
        Write-Host "✓ RDS PostgreSQL Instance Creating: $DBInstanceId" -ForegroundColor Green
        Write-Host "⏳ Waiting for database to become available (this may take 5-10 minutes)..." -ForegroundColor Yellow
        
        # Wait for DB to be available
        aws rds wait db-instance-available --db-instance-identifier $DBInstanceId
        
        # Get DB endpoint
        $DBEndpoint = (aws rds describe-db-instances --db-instance-identifier $DBInstanceId --query "DBInstances[0].Endpoint.Address" --output text)
        Write-Host "✓ Database Available at: $DBEndpoint" -ForegroundColor Green
    }

    # Step 4: Store Database Connection String in Parameter Store
    Write-Host "🔐 Step 4: Storing Database Connection in Parameter Store..." -ForegroundColor Yellow
    
    $DatabaseURL = "postgresql://${DBUsername}:${DBPassword}@${DBEndpoint}:5432/postgres"
    
    # Check if parameter already exists
    $ExistingParam = aws ssm get-parameter --name "/counsel/database-url" 2>$null
    if ($LASTEXITCODE -eq 0) {
        aws ssm put-parameter --name "/counsel/database-url" --value $DatabaseURL --type "SecureString" --description "PostgreSQL connection string for Counsel AI" --overwrite
        Write-Host "✓ Database URL updated in Parameter Store" -ForegroundColor Green
    } else {
        aws ssm put-parameter --name "/counsel/database-url" --value $DatabaseURL --type "SecureString" --description "PostgreSQL connection string for Counsel AI"
        Write-Host "✓ Database URL stored in Parameter Store" -ForegroundColor Green
    }

    # Step 5: Create Database Schema (Optional)
    Write-Host "📊 Step 5: Database Schema Setup..." -ForegroundColor Yellow
    Write-Host "ℹ️ Database schema will be created automatically by the application on first run" -ForegroundColor Cyan

    # Output Summary
    Write-Host ""
    Write-Host "🎉 RDS PostgreSQL Database Setup Complete!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "Database Details:" -ForegroundColor Cyan
    Write-Host "- Instance ID: $DBInstanceId" -ForegroundColor White
    Write-Host "- Endpoint: $DBEndpoint" -ForegroundColor White
    Write-Host "- Engine: PostgreSQL 15.4" -ForegroundColor White
    Write-Host "- Storage: 20GB (encrypted)" -ForegroundColor White
    Write-Host "- Backup Retention: 7 days" -ForegroundColor White
    Write-Host "- Security Group: $DBSGId" -ForegroundColor White
    Write-Host ""
    Write-Host "Connection Details:" -ForegroundColor Cyan
    Write-Host "- Username: $DBUsername" -ForegroundColor White
    Write-Host "- Database: postgres" -ForegroundColor White
    Write-Host "- Port: 5432" -ForegroundColor White
    Write-Host "- Connection String stored in: /counsel/database-url" -ForegroundColor White
    Write-Host ""
    Write-Host "✅ Database is ready for production use!" -ForegroundColor Green

}
catch {
    Write-Host "❌ Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Please check AWS permissions and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ RDS PostgreSQL Setup Complete!" -ForegroundColor Green
