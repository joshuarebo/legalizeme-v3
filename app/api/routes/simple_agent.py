"""
SIMPLE KENYAN LEGAL AI AGENT - PHASE 1
=====================================
Ultra-reliable agent that forwards requests to the working counsel endpoints.
No complex dependencies, no initialization issues, just works.
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SimpleAgentRequest(BaseModel):
    query: str = Field(..., max_length=2000)
    strategy: str = Field(default="quick", description="Research strategy: quick, comprehensive, focused")
    context: Optional[Dict[str, Any]] = Field(default=None)
    user_context: Optional[Dict[str, Any]] = Field(default=None)

class SimpleAgentResponse(BaseModel):
    answer: str
    confidence: float
    model_used: str
    processing_time_ms: float
    timestamp: str
    strategy_used: str
    citations: List[Dict[str, Any]] = Field(default=[])
    follow_up_suggestions: List[str] = Field(default=[])
    related_queries: List[str] = Field(default=[])

# ============================================================================
# KENYAN LEGAL KNOWLEDGE BASE
# ============================================================================

KENYAN_LEGAL_CONTEXT = """
You are a Kenyan legal expert with deep knowledge of:

KEY KENYAN LAWS:
- Constitution of Kenya 2010
- Employment Act 2007
- Labour Relations Act 2007
- Companies Act 2015
- Land Act 2012
- Family Protection Act
- Children Act 2022
- Data Protection Act 2019

LEGAL INSTITUTIONS:
- High Court of Kenya
- Court of Appeal
- Supreme Court
- Employment and Labour Relations Court
- Environment and Land Court
- Family Division

EMPLOYMENT RIGHTS:
- Minimum wage requirements
- Working hours (max 52 hours/week)
- Annual leave (21 days minimum)
- Maternity leave (3 months)
- Paternity leave (2 weeks)
- Termination procedures
- Severance pay requirements

Always provide practical, actionable advice while recommending professional legal consultation for specific cases.
"""

# ============================================================================
# CORE AGENT FUNCTIONS
# ============================================================================

def generate_follow_up_suggestions(query: str) -> List[str]:
    """Generate contextual follow-up suggestions"""
    query_lower = query.lower()

    if "employment" in query_lower or "job" in query_lower:
        return [
            "What are termination procedures in Kenya?",
            "How to calculate severance pay?",
            "Employment contract requirements"
        ]
    elif "company" in query_lower or "business" in query_lower:
        return [
            "Company registration process in Kenya",
            "Director responsibilities under Companies Act",
            "Business licensing requirements"
        ]
    elif "land" in query_lower or "property" in query_lower:
        return [
            "Land ownership rights in Kenya",
            "Property transfer procedures",
            "Land disputes resolution"
        ]
    else:
        return [
            "Constitutional rights in Kenya",
            "Court procedures and filing",
            "Legal aid services available"
        ]

def generate_related_queries(query: str) -> List[str]:
    """Generate related queries for exploration"""
    query_lower = query.lower()

    if "employment" in query_lower or "job" in query_lower:
        return [
            "Employment Act 2007 Kenya",
            "Labour Relations Act 2007",
            "Minimum wage Kenya 2024"
        ]
    elif "company" in query_lower or "business" in query_lower:
        return [
            "Companies Act 2015 Kenya",
            "Business registration Kenya",
            "Corporate governance Kenya"
        ]
    elif "land" in query_lower or "property" in query_lower:
        return [
            "Land Act 2012 Kenya",
            "Property law Kenya",
            "Land registration Kenya"
        ]
    else:
        return [
            "Constitution of Kenya 2010",
            "Bill of Rights Kenya",
            "Kenyan legal system"
        ]

# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/research", response_model=SimpleAgentResponse)
async def simple_agent_research(
    request: SimpleAgentRequest
):
    """
    SIMPLE KENYAN LEGAL RESEARCH AGENT
    Forwards requests to the working counsel endpoint for maximum reliability
    """
    start_time = datetime.utcnow()

    try:
        logger.info(f"🚀 Simple Agent Research: {request.query[:100]}...")

        # Create enhanced prompt with Kenyan legal context
        enhanced_query = f"""As a Kenyan legal expert, please provide comprehensive guidance on: {request.query}

Strategy: {request.strategy}

Please provide:
1. Relevant Kenyan laws and regulations
2. Key legal principles
3. Practical guidance
4. Recommended next steps
5. When to seek professional legal counsel"""

        # Use LLM manager directly for maximum reliability
        from app.services.llm_manager import llm_manager

        try:
            # Call LLM manager directly (same as enhanced RAG endpoint)
            llm_response = await llm_manager.invoke_model(
                prompt=enhanced_query,
                model_preference="claude-sonnet-4"
            )

            if llm_response.get("success", False):
                answer = llm_response.get("response_text", "")
                model_used = llm_response.get("model_used", "claude-sonnet-4")
                logger.info(f"✅ LLM manager successful with {model_used}")
            else:
                raise Exception(f"LLM manager failed: {llm_response.get('error', 'Unknown error')}")

        except Exception as llm_error:
            logger.error(f"LLM manager failed: {llm_error}")
            raise Exception(f"LLM processing failed: {llm_error}")

        # If no answer, provide emergency response
        if not answer or len(answer.strip()) == 0:
            logger.error("🚨 Counsel endpoint returned empty response, using emergency response")
            answer = f"""I apologize, but I'm currently experiencing technical difficulties processing your query about: "{request.query}"

Based on general knowledge of Kenyan law, here are some key points:

**For Employment Matters:**
- Refer to Employment Act 2007 and Labour Relations Act 2007
- Contact Ministry of Labour for guidance
- Consider Employment and Labour Relations Court for disputes

**For Business/Company Issues:**
- Consult Companies Act 2015
- Visit Huduma Centre for registration services
- Contact Kenya Association of Manufacturers for guidance

**For Constitutional/Rights Issues:**
- Reference Constitution of Kenya 2010
- Contact Kenya National Commission on Human Rights
- Consider High Court for constitutional matters

**Immediate Recommendations:**
1. Consult with a qualified Kenyan lawyer
2. Visit relevant government offices (Huduma Centres)
3. Contact professional legal aid organizations

Please try again later or contact our support team if this issue persists."""
            model_used = "Emergency System"

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Generate follow-up suggestions and related queries
        follow_ups = generate_follow_up_suggestions(request.query)
        related_queries = generate_related_queries(request.query)

        # Simple agent - no database dependencies for maximum reliability
        logger.info(f"✅ Simple agent research completed successfully")

        # Return successful response
        return SimpleAgentResponse(
            answer=answer,
            confidence=0.85 if model_used != "Emergency System" else 0.3,
            model_used=model_used,
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat(),
            strategy_used=request.strategy,
            citations=[],  # Will add in Phase 2
            follow_up_suggestions=follow_ups,
            related_queries=related_queries
        )
        
    except Exception as e:
        logger.error(f"💥 Simple agent research failed: {e}")
        logger.exception("Full error details:")
        
        # ABSOLUTE EMERGENCY FALLBACK
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return SimpleAgentResponse(
            answer=f"I apologize, but I'm currently experiencing technical difficulties. Your question about '{request.query}' is important. Please try again later or contact support. For immediate Kenyan legal assistance, consider consulting the Employment Act 2007, Companies Act 2015, or seeking professional legal counsel.",
            confidence=0.1,
            model_used="Emergency Fallback",
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat(),
            strategy_used=request.strategy,
            citations=[],
            follow_up_suggestions=["Try again later", "Contact support", "Consult legal counsel"],
            related_queries=["Employment Act 2007", "Companies Act 2015", "Legal support"]
        )

@router.get("/health")
async def simple_agent_health():
    """Simple agent health check - always works"""
    return {
        "status": "healthy",
        "agent_type": "simple_kenyan_legal_agent",
        "version": "1.0.0",
        "capabilities": ["legal_research", "kenyan_law", "employment_law", "company_law"],
        "models_available": ["claude-sonnet-4", "claude-3.7", "mistral-large"],
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/capabilities")
async def simple_agent_capabilities():
    """List agent capabilities for frontend integration"""
    return {
        "research_strategies": ["quick", "comprehensive", "focused"],
        "legal_areas": [
            "Employment Law",
            "Company Law", 
            "Constitutional Law",
            "Land Law",
            "Family Law",
            "Data Protection",
            "Labour Relations"
        ],
        "supported_queries": [
            "Employment rights and obligations",
            "Company registration and compliance",
            "Constitutional rights and freedoms",
            "Land ownership and transfer",
            "Family law matters",
            "Data protection compliance"
        ],
        "response_format": {
            "answer": "Comprehensive legal guidance",
            "confidence": "0.0 to 1.0 confidence score",
            "citations": "Relevant legal sources (Phase 2)",
            "follow_up_suggestions": "Related questions to explore"
        }
    }
