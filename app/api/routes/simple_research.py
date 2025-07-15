"""
SIMPLE DIRECT BEDROCK RESEARCH ENDPOINT
Bypasses all agent complexity and directly calls AWS Bedrock
"""

import boto3
import json
import logging
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter()

class SimpleResearchRequest(BaseModel):
    query: str
    strategy: str = "quick"

class SimpleResearchResponse(BaseModel):
    answer: str
    confidence: float
    retrieval_strategy: str
    research_strategy: str
    timestamp: str

@router.post("/simple-research")
async def simple_research(request: SimpleResearchRequest):
    """
    SIMPLE DIRECT AWS BEDROCK RESEARCH
    No agent complexity, just direct model calls
    """
    try:
        logger.info(f"🚀 SIMPLE RESEARCH: {request.query[:100]}...")
        
        # Direct AWS Bedrock client using environment variables
        bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        # Simple prompt
        prompt = f"""You are a Kenyan legal expert. Answer this question about Kenyan law:

Question: {request.query}

Provide a comprehensive answer covering:
1. Relevant Kenyan laws and regulations
2. Key legal principles
3. Practical implications

Answer:"""

        # Try Claude Sonnet 4 first
        try:
            response = bedrock_client.invoke_model(
                modelId='us.anthropic.claude-sonnet-4-20250514-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            answer = result['content'][0]['text']
            
            logger.info("✅ Claude Sonnet 4 successful")
            
            return SimpleResearchResponse(
                answer=answer,
                confidence=0.85,
                retrieval_strategy="direct_bedrock_claude_sonnet_4",
                research_strategy=request.strategy,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e1:
            logger.warning(f"Claude Sonnet 4 failed: {e1}")
            
            # Try Claude 3.7 fallback
            try:
                response = bedrock_client.invoke_model(
                    modelId='us.anthropic.claude-3-7-sonnet-20250219-v1:0',
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 2000,
                        "messages": [{"role": "user", "content": prompt}]
                    })
                )
                
                result = json.loads(response['body'].read())
                answer = result['content'][0]['text']
                
                logger.info("✅ Claude 3.7 fallback successful")
                
                return SimpleResearchResponse(
                    answer=answer,
                    confidence=0.80,
                    retrieval_strategy="direct_bedrock_claude_3_7",
                    research_strategy=request.strategy,
                    timestamp=datetime.utcnow().isoformat()
                )
                
            except Exception as e2:
                logger.warning(f"Claude 3.7 failed: {e2}")
                
                # Try Mistral fallback
                try:
                    response = bedrock_client.invoke_model(
                        modelId='mistral.mistral-large-2402-v1:0',
                        body=json.dumps({
                            "prompt": prompt,
                            "max_tokens": 2000,
                            "temperature": 0.7
                        })
                    )
                    
                    result = json.loads(response['body'].read())
                    answer = result['outputs'][0]['text']
                    
                    logger.info("✅ Mistral fallback successful")
                    
                    return SimpleResearchResponse(
                        answer=answer,
                        confidence=0.75,
                        retrieval_strategy="direct_bedrock_mistral",
                        research_strategy=request.strategy,
                        timestamp=datetime.utcnow().isoformat()
                    )
                    
                except Exception as e3:
                    logger.error(f"All models failed: {e3}")
                    raise
                    
    except Exception as e:
        logger.error(f"💥 Simple research failed: {e}")
        
        # Emergency response
        return SimpleResearchResponse(
            answer=f"I apologize, but I'm currently experiencing technical difficulties processing your query about: {request.query}. For Kenyan legal matters, I recommend consulting the Employment Act 2007, Labour Relations Act 2007, and seeking professional legal counsel.",
            confidence=0.3,
            retrieval_strategy="emergency_fallback",
            research_strategy=request.strategy,
            timestamp=datetime.utcnow().isoformat()
        )

@router.get("/simple-test")
async def simple_test():
    """Test endpoint to verify the simple research is working"""
    return {"status": "Simple research endpoint is working", "timestamp": datetime.utcnow().isoformat()}
