#!/bin/bash

# Automated Rollback Script for Counsel AI
# Safely rolls back to previous deployment if issues are detected

set -e

# Configuration
CLUSTER_NAME="counsel-cluster"
SERVICE_NAME="counsel-service"
TASK_FAMILY="counsel-task"
HEALTH_ENDPOINT="http://counsel-alb-694525771.us-east-1.elb.amazonaws.com/health"
MAX_ROLLBACK_ATTEMPTS=3
HEALTH_CHECK_TIMEOUT=30
STABILITY_WAIT_TIME=300  # 5 minutes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if AWS CLI is available and configured
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        error "AWS CLI is not installed or not in PATH"
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        error "AWS CLI is not configured or credentials are invalid"
        exit 1
    fi
    
    success "AWS CLI is configured and ready"
}

# Function to get current task definition
get_current_task_definition() {
    log "Getting current task definition..."
    
    CURRENT_TASK_DEF=$(aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --query 'services[0].taskDefinition' \
        --output text 2>/dev/null)
    
    if [ -z "$CURRENT_TASK_DEF" ] || [ "$CURRENT_TASK_DEF" = "None" ]; then
        error "Failed to get current task definition"
        exit 1
    fi
    
    log "Current task definition: $CURRENT_TASK_DEF"
    echo "$CURRENT_TASK_DEF"
}

# Function to get previous task definition
get_previous_task_definition() {
    local current_task_def="$1"
    
    log "Calculating previous task definition..."
    
    # Extract revision number
    CURRENT_REVISION=$(echo "$current_task_def" | grep -o '[0-9]*$')
    
    if [ -z "$CURRENT_REVISION" ] || [ "$CURRENT_REVISION" -le 1 ]; then
        error "Cannot determine previous revision or already at revision 1"
        exit 1
    fi
    
    PREVIOUS_REVISION=$((CURRENT_REVISION - 1))
    PREVIOUS_TASK_DEF="${TASK_FAMILY}:${PREVIOUS_REVISION}"
    
    # Verify previous task definition exists
    if ! aws ecs describe-task-definition \
        --task-definition "$PREVIOUS_TASK_DEF" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text &> /dev/null; then
        error "Previous task definition $PREVIOUS_TASK_DEF does not exist"
        exit 1
    fi
    
    log "Previous task definition: $PREVIOUS_TASK_DEF"
    echo "$PREVIOUS_TASK_DEF"
}

# Function to check service health
check_service_health() {
    local max_attempts=5
    local attempt=1
    
    log "Checking service health..."
    
    while [ $attempt -le $max_attempts ]; do
        log "Health check attempt $attempt/$max_attempts"
        
        if curl -f -s -m "$HEALTH_CHECK_TIMEOUT" "$HEALTH_ENDPOINT" > /dev/null 2>&1; then
            success "Health check passed"
            return 0
        fi
        
        warning "Health check failed (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    error "Service health check failed after $max_attempts attempts"
    return 1
}

# Function to run regression tests
run_regression_tests() {
    log "Running critical endpoint regression tests..."
    
    # Test critical endpoints
    local endpoints=(
        "/health"
        "/api/v1/counsel/conversations"
        "/api/v1/multimodal/capabilities"
    )
    
    local base_url="http://counsel-alb-694525771.us-east-1.elb.amazonaws.com"
    local failed_tests=0
    
    for endpoint in "${endpoints[@]}"; do
        log "Testing endpoint: $endpoint"
        
        if curl -f -s -m 10 -H "User-Agent: RollbackTest/1.0" "$base_url$endpoint" > /dev/null 2>&1; then
            success "✅ $endpoint - OK"
        else
            error "❌ $endpoint - FAILED"
            ((failed_tests++))
        fi
    done
    
    if [ $failed_tests -eq 0 ]; then
        success "All regression tests passed"
        return 0
    else
        error "$failed_tests regression tests failed"
        return 1
    fi
}

# Function to perform rollback
perform_rollback() {
    local current_task_def="$1"
    local previous_task_def="$2"
    local attempt="$3"
    
    log "🔄 Starting rollback attempt $attempt/$MAX_ROLLBACK_ATTEMPTS"
    log "Rolling back from $current_task_def to $previous_task_def"
    
    # Update service to previous task definition
    log "Updating ECS service..."
    if ! aws ecs update-service \
        --cluster "$CLUSTER_NAME" \
        --service "$SERVICE_NAME" \
        --task-definition "$previous_task_def" \
        --output table; then
        error "Failed to update ECS service"
        return 1
    fi
    
    # Wait for deployment to complete
    log "Waiting for rollback deployment to stabilize..."
    log "This may take up to $((STABILITY_WAIT_TIME / 60)) minutes..."
    
    if ! aws ecs wait services-stable \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --cli-read-timeout $STABILITY_WAIT_TIME \
        --cli-connect-timeout 60; then
        error "Rollback deployment did not stabilize within timeout"
        return 1
    fi
    
    success "Rollback deployment completed"
    
    # Wait additional time for service to be fully ready
    log "Waiting for service to be fully ready..."
    sleep 60
    
    # Verify rollback success
    log "Verifying rollback success..."
    if check_service_health && run_regression_tests; then
        success "✅ Rollback verification successful"
        return 0
    else
        error "❌ Rollback verification failed"
        return 1
    fi
}

# Function to send notification (placeholder for future integration)
send_notification() {
    local status="$1"
    local message="$2"
    
    log "📧 Notification: [$status] $message"
    
    # Future: Integrate with Slack, email, or other notification systems
    # Example:
    # curl -X POST -H 'Content-type: application/json' \
    #     --data "{\"text\":\"[$status] Counsel AI Rollback: $message\"}" \
    #     "$SLACK_WEBHOOK_URL"
}

# Function to create rollback report
create_rollback_report() {
    local status="$1"
    local current_task="$2"
    local previous_task="$3"
    local timestamp=$(date +'%Y-%m-%d_%H-%M-%S')
    local report_file="rollback_report_$timestamp.json"
    
    cat > "$report_file" << EOF
{
  "rollback_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "status": "$status",
  "cluster": "$CLUSTER_NAME",
  "service": "$SERVICE_NAME",
  "rollback_from": "$current_task",
  "rollback_to": "$previous_task",
  "health_endpoint": "$HEALTH_ENDPOINT",
  "aws_region": "${AWS_REGION:-us-east-1}",
  "initiated_by": "${USER:-automated}",
  "reason": "${ROLLBACK_REASON:-Automated rollback due to deployment issues}"
}
EOF
    
    log "Rollback report created: $report_file"
}

# Main rollback function
main() {
    log "🚨 STARTING AUTOMATED ROLLBACK PROCEDURE"
    log "=========================================="
    
    # Check prerequisites
    check_aws_cli
    
    # Get current and previous task definitions
    CURRENT_TASK_DEF=$(get_current_task_definition)
    PREVIOUS_TASK_DEF=$(get_previous_task_definition "$CURRENT_TASK_DEF")
    
    log "Rollback plan:"
    log "  From: $CURRENT_TASK_DEF"
    log "  To:   $PREVIOUS_TASK_DEF"
    
    # Attempt rollback with retries
    local attempt=1
    local rollback_successful=false
    
    while [ $attempt -le $MAX_ROLLBACK_ATTEMPTS ] && [ "$rollback_successful" = false ]; do
        if perform_rollback "$CURRENT_TASK_DEF" "$PREVIOUS_TASK_DEF" "$attempt"; then
            rollback_successful=true
            success "🎉 ROLLBACK COMPLETED SUCCESSFULLY"
            
            # Create success report
            create_rollback_report "SUCCESS" "$CURRENT_TASK_DEF" "$PREVIOUS_TASK_DEF"
            
            # Send success notification
            send_notification "SUCCESS" "Rollback completed successfully from $CURRENT_TASK_DEF to $PREVIOUS_TASK_DEF"
            
            log "=========================================="
            log "✅ System has been rolled back and is operational"
            log "✅ All critical endpoints are responding"
            log "✅ Service is stable and ready for traffic"
            log "=========================================="
            
            exit 0
        else
            warning "Rollback attempt $attempt failed"
            ((attempt++))
            
            if [ $attempt -le $MAX_ROLLBACK_ATTEMPTS ]; then
                log "Retrying rollback in 30 seconds..."
                sleep 30
            fi
        fi
    done
    
    # If we reach here, all rollback attempts failed
    error "🚨 CRITICAL: ALL ROLLBACK ATTEMPTS FAILED"
    
    # Create failure report
    create_rollback_report "FAILED" "$CURRENT_TASK_DEF" "$PREVIOUS_TASK_DEF"
    
    # Send failure notification
    send_notification "CRITICAL" "All rollback attempts failed. Manual intervention required."
    
    log "=========================================="
    error "❌ MANUAL INTERVENTION REQUIRED"
    error "❌ Contact DevOps team immediately"
    error "❌ Service may be in unstable state"
    log "=========================================="
    
    exit 1
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Automated Rollback Script for Counsel AI"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h          Show this help message"
        echo "  --dry-run          Show what would be done without executing"
        echo "  --force            Skip confirmation prompts"
        echo ""
        echo "Environment Variables:"
        echo "  ROLLBACK_REASON    Reason for rollback (for reporting)"
        echo "  AWS_REGION         AWS region (default: us-east-1)"
        echo ""
        exit 0
        ;;
    --dry-run)
        log "DRY RUN MODE - No changes will be made"
        CURRENT_TASK_DEF=$(get_current_task_definition)
        PREVIOUS_TASK_DEF=$(get_previous_task_definition "$CURRENT_TASK_DEF")
        log "Would rollback from $CURRENT_TASK_DEF to $PREVIOUS_TASK_DEF"
        exit 0
        ;;
    --force)
        log "Force mode enabled - skipping confirmations"
        ;;
    "")
        # No arguments - proceed with interactive mode
        read -p "Are you sure you want to perform an automated rollback? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Rollback cancelled by user"
            exit 0
        fi
        ;;
    *)
        error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

# Execute main function
main
