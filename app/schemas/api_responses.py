"""
Comprehensive API Response Schemas for Counsel AI
All response formats for the 19+ endpoints with AWS Titan integration
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from enum import Enum

# ============================================================================
# HEALTH & STATUS RESPONSES
# ============================================================================

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    INACTIVE = "inactive"

class ServiceDetails(BaseModel):
    status: ServiceStatus
    details: Dict[str, Any]
    last_check: Optional[datetime] = None
    uptime_seconds: Optional[float] = None

class HealthResponse(BaseModel):
    status: ServiceStatus
    timestamp: datetime
    version: str
    uptime: str
    services: Dict[str, ServiceDetails]
    environment: str
    region: str

class LivenessResponse(BaseModel):
    alive: bool
    timestamp: datetime
    uptime_seconds: float

# ============================================================================
# LEGAL COUNSEL RESPONSES
# ============================================================================

class CitationSource(BaseModel):
    document_id: str
    title: str
    source_type: str  # "statute", "case_law", "regulation", "constitution"
    url: Optional[str] = None
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    excerpt: str
    page_number: Optional[int] = None
    section: Optional[str] = None

class LegalQueryResponse(BaseModel):
    query_id: str
    answer: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    legal_area: str  # "constitutional", "criminal", "civil", "commercial", etc.
    citations: List[CitationSource]
    processing_time_ms: int
    model_used: str
    token_usage: Dict[str, int]  # {"input": 1500, "output": 800, "total": 2300}
    cost_estimate: Dict[str, float]  # {"input_cost": 0.0045, "output_cost": 0.012, "total": 0.0165}
    conversation_id: Optional[str] = None
    follow_up_questions: List[str]
    disclaimer: str

class DirectQueryResponse(BaseModel):
    response_text: str
    model_used: str
    success: bool
    latency_ms: int
    token_count: int
    cost_estimate: float
    timestamp: datetime
    request_id: str

class EnhancedRAGResponse(BaseModel):
    success: bool
    response: str
    model_used: str
    retrieved_documents: int
    context_tokens: int
    total_tokens: int
    cost_estimate: Dict[str, Any]
    sources: List[str]
    similarities: List[float]
    latency_ms: int
    rag_quality_score: float = Field(..., ge=0.0, le=1.0)
    context_relevance: float = Field(..., ge=0.0, le=1.0)

class ConversationMessage(BaseModel):
    message_id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]
    citations: Optional[List[CitationSource]] = None

class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    user_id: str
    messages: List[ConversationMessage]
    total_messages: int
    created_at: datetime
    updated_at: datetime
    legal_areas: List[str]
    summary: Optional[str] = None

class LegalSuggestionResponse(BaseModel):
    suggestions: List[str]
    query_context: str
    legal_areas: List[str]
    processing_time_ms: int
    source: str  # "ai_generated", "template_based", "knowledge_base"

class LegalDocumentFetchResponse(BaseModel):
    documents: List[Dict[str, Any]]
    total_found: int
    query: str
    search_time_ms: int
    filters_applied: Dict[str, Any]
    pagination: Dict[str, int]  # {"page": 1, "limit": 10, "total_pages": 5}

# ============================================================================
# AGENT RESPONSES
# ============================================================================

class AgentCapability(BaseModel):
    name: str
    description: str
    enabled: bool
    confidence_threshold: float
    last_used: Optional[datetime] = None

class LegalResearchResult(BaseModel):
    research_id: str
    query: str
    findings: List[Dict[str, Any]]
    legal_precedents: List[CitationSource]
    recommendations: List[str]
    confidence_score: float
    research_depth: str  # "basic", "intermediate", "comprehensive"
    time_taken_seconds: float

class AgentResearchResponse(BaseModel):
    success: bool
    research_result: LegalResearchResult
    agent_used: str
    capabilities_utilized: List[str]
    processing_pipeline: List[str]
    metadata: Dict[str, Any]

class AgentHealthResponse(BaseModel):
    agent_status: ServiceStatus
    available_agents: List[str]
    capabilities: List[AgentCapability]
    active_sessions: int
    total_queries_processed: int
    average_response_time_ms: float

class AgentMetricsResponse(BaseModel):
    total_queries: int
    successful_queries: int
    failed_queries: int
    average_response_time: float
    accuracy_score: float
    user_satisfaction: float
    top_legal_areas: List[Dict[str, Any]]
    performance_trends: Dict[str, List[float]]
    uptime_percentage: float

class AgentMemoryResponse(BaseModel):
    user_id: str
    memory_entries: List[Dict[str, Any]]
    total_entries: int
    memory_types: List[str]  # ["preferences", "case_history", "legal_interests"]
    last_updated: datetime
    retention_policy: str

# ============================================================================
# DOCUMENT PROCESSING RESPONSES
# ============================================================================

class DocumentAnalysisResult(BaseModel):
    document_id: str
    document_type: str  # "contract", "statute", "case_law", "regulation"
    key_points: List[str]
    legal_entities: List[str]
    important_dates: List[Dict[str, Any]]
    risk_factors: List[str]
    compliance_issues: List[str]
    confidence_score: float

class DocumentSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_results: int
    search_query: str
    filters_applied: Dict[str, Any]
    search_time_ms: int
    relevance_scores: List[float]
    facets: Dict[str, List[Dict[str, Any]]]

class DocumentAnalysisResponse(BaseModel):
    success: bool
    analysis: DocumentAnalysisResult
    processing_time_ms: int
    document_metadata: Dict[str, Any]
    extracted_text_length: int
    language_detected: str
    quality_score: float

# ============================================================================
# ENHANCED DOCUMENT ANALYSIS MODELS (Phase 1 Enhancement)
# ============================================================================

class KeyFinding(BaseModel):
    """Detailed finding from document analysis"""
    category: str  # "Contract Terms", "Legal Obligations", "Risk Factors", "Compliance Issues"
    finding: str
    severity: str  # "low", "medium", "high", "critical"
    confidence: float = Field(..., ge=0.0, le=1.0)
    page_reference: Optional[int] = None
    section_reference: Optional[str] = None
    legal_basis: Optional[str] = None
    recommendation: Optional[str] = None

class LegalRisk(BaseModel):
    """Legal risk assessment with mitigation strategies"""
    risk_type: str  # "compliance", "financial", "operational", "reputational"
    title: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    probability: float = Field(..., ge=0.0, le=1.0)
    impact: str
    mitigation: str
    legal_basis: str
    kenyan_law_reference: str
    estimated_cost: Optional[str] = None
    timeline: Optional[str] = None

class ComplianceAnalysis(BaseModel):
    """Comprehensive compliance analysis against Kenyan law"""
    overall_score: float = Field(..., ge=0.0, le=1.0)
    kenyan_law_compliance: bool
    compliance_details: Dict[str, str]  # {"employment_act_2007": "compliant", "labor_relations_act": "requires_review"}
    missing_requirements: List[str]
    recommendations: List[str]
    critical_gaps: List[str] = []  # Make this optional with default empty list
    compliance_timeline: Optional[str] = None

class KenyanLawCitation(BaseModel):
    """Kenyan law citation with detailed reference information"""
    source: str  # "Employment Act 2007", "Constitution of Kenya 2010"
    section: str
    title: str
    relevance: str
    url: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    page_number: Optional[int] = None
    excerpt: str
    legal_area: str  # "employment", "constitutional", "commercial"
    citation_type: str  # "statute", "case_law", "regulation"

class DocumentIntelligence(BaseModel):
    """AI-extracted document intelligence"""
    document_type_detected: str
    language: str
    jurisdiction: str
    parties_identified: List[str]
    key_dates: List[str]
    financial_terms: List[str]
    critical_clauses: List[str]
    contract_duration: Optional[str] = None
    governing_law: Optional[str] = None
    dispute_resolution: Optional[str] = None

class EnhancedDocumentAnalysisResponse(BaseModel):
    """Enhanced document analysis response with comprehensive legal intelligence"""
    # Core response fields
    analysis_id: str
    document_id: str
    status: str = "completed"
    confidence: float = Field(..., ge=0.0, le=1.0)
    processing_time: float
    model_used: str

    # Enhanced analysis content
    analysis_summary: str  # 2-3 paragraph comprehensive summary
    key_findings: List[KeyFinding]
    legal_risks: List[LegalRisk]
    compliance_analysis: ComplianceAnalysis
    citations: List[KenyanLawCitation]
    document_intelligence: DocumentIntelligence

    # Metadata
    created_at: datetime
    analysis_type: str
    focus_areas: List[str]
    kenyan_law_focus: bool = True

# ============================================================================
# MODEL & AI SERVICE RESPONSES
# ============================================================================

class ModelInfo(BaseModel):
    model_id: str
    model_name: str
    provider: str  # "aws_bedrock", "openai", "anthropic"
    status: ServiceStatus
    capabilities: List[str]
    max_tokens: int
    cost_per_1k_tokens: Dict[str, float]  # {"input": 0.003, "output": 0.015}
    last_health_check: datetime

class ModelStatusResponse(BaseModel):
    available_models: List[ModelInfo]
    primary_model: str
    fallback_models: List[str]
    total_models: int
    healthy_models: int
    model_selection_strategy: str

class ModelHealthResponse(BaseModel):
    overall_health: ServiceStatus
    model_statuses: Dict[str, ServiceStatus]
    response_times: Dict[str, float]
    error_rates: Dict[str, float]
    last_check: datetime

class ModelMetricsResponse(BaseModel):
    usage_statistics: Dict[str, Dict[str, Any]]
    performance_metrics: Dict[str, float]
    cost_analysis: Dict[str, float]
    error_logs: List[Dict[str, Any]]
    uptime_stats: Dict[str, float]

class ModelConfigResponse(BaseModel):
    current_config: Dict[str, Any]
    available_models: List[str]
    default_parameters: Dict[str, Any]
    rate_limits: Dict[str, int]
    feature_flags: Dict[str, bool]

# ============================================================================
# MULTIMODAL RESPONSES
# ============================================================================

class MultimodalSearchResult(BaseModel):
    result_id: str
    content_type: str  # "text", "image", "pdf", "audio"
    content: str
    metadata: Dict[str, Any]
    relevance_score: float
    source_document: str
    extracted_entities: List[str]

class MultimodalSearchResponse(BaseModel):
    results: List[MultimodalSearchResult]
    total_results: int
    search_query: str
    content_types_searched: List[str]
    processing_time_ms: int
    search_strategy: str

class MultimodalStatsResponse(BaseModel):
    total_documents: int
    content_type_breakdown: Dict[str, int]
    processing_statistics: Dict[str, Any]
    storage_usage: Dict[str, float]
    recent_activity: List[Dict[str, Any]]
    performance_metrics: Dict[str, float]

# ============================================================================
# ERROR RESPONSES
# ============================================================================

class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    error: bool = True
    error_code: str
    message: str
    details: List[ErrorDetail]
    timestamp: datetime
    request_id: str
    suggestion: Optional[str] = None
    documentation_url: Optional[str] = None

# ============================================================================
# PAGINATION & METADATA
# ============================================================================

class PaginationInfo(BaseModel):
    page: int
    limit: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool

class ResponseMetadata(BaseModel):
    request_id: str
    timestamp: datetime
    processing_time_ms: int
    api_version: str
    rate_limit_remaining: int
    rate_limit_reset: datetime

# ============================================================================
# ENHANCED TITAN INTEGRATION RESPONSES
# ============================================================================

class TitanEmbeddingResponse(BaseModel):
    embedding: List[float]
    model_used: str  # "amazon.titan-embed-text-v2:0"
    input_tokens: int
    processing_time_ms: int
    dimension: int  # 1024 for Titan V2
    cost_estimate: float

class TitanTextResponse(BaseModel):
    generated_text: str
    model_used: str  # "amazon.titan-text-premier-v1:0" or "amazon.titan-text-express-v1:0"
    input_tokens: int
    output_tokens: int
    total_tokens: int
    finish_reason: str
    cost_estimate: Dict[str, float]
    processing_time_ms: int

class TitanMultimodalResponse(BaseModel):
    analysis_result: Dict[str, Any]
    model_used: str  # "amazon.titan-multimodal-embeddings-g1"
    content_type: str
    confidence_scores: Dict[str, float]
    extracted_features: List[str]
    processing_time_ms: int

# ============================================================================
# SPECIALIZED KENYAN LEGAL RESPONSES
# ============================================================================

class KenyanLegalArea(str, Enum):
    CONSTITUTIONAL = "constitutional"
    CRIMINAL = "criminal"
    CIVIL = "civil"
    COMMERCIAL = "commercial"
    EMPLOYMENT = "employment"
    FAMILY = "family"
    PROPERTY = "property"
    TAX = "tax"
    ENVIRONMENTAL = "environmental"
    HUMAN_RIGHTS = "human_rights"

class KenyanLegalSource(BaseModel):
    source_type: str  # "constitution", "act", "regulation", "case_law"
    title: str
    citation: str
    url: str
    relevance: float
    excerpt: str
    legal_area: KenyanLegalArea

class KenyanLegalQueryResponse(BaseModel):
    query_id: str
    answer: str
    legal_area: KenyanLegalArea
    kenyan_sources: List[KenyanLegalSource]
    constitutional_references: List[str]
    applicable_statutes: List[str]
    case_law_precedents: List[str]
    practical_guidance: List[str]
    next_steps: List[str]
    confidence_score: float
    processing_time_ms: int
    model_used: str
    cost_estimate: Dict[str, float]

# ============================================================================
# COMPREHENSIVE API COLLECTION RESPONSE
# ============================================================================

class APIEndpoint(BaseModel):
    path: str
    method: str
    description: str
    requires_auth: bool
    rate_limit: int
    response_schema: str

class APICollectionResponse(BaseModel):
    total_endpoints: int
    endpoints: List[APIEndpoint]
    api_version: str
    documentation_url: str
    health_status: ServiceStatus
    uptime: str
    last_deployment: datetime
