"""
Advanced Prompt Engineering Engine for Dynamic Intelligence Enhancement
Provides sophisticated prompt engineering, template management, and context-aware prompt generation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import re
import time
from datetime import datetime
from jinja2 import Template, Environment, BaseLoader

logger = logging.getLogger(__name__)

class PromptType(Enum):
    """Types of prompts"""
    LEGAL_QUERY = "legal_query"
    DOCUMENT_GENERATION = "document_generation"
    LEGAL_ANALYSIS = "legal_analysis"
    CASE_RESEARCH = "case_research"
    COMPLIANCE_CHECK = "compliance_check"
    GENERAL = "general"

class PromptStrategy(Enum):
    """Prompt engineering strategies"""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    FEW_SHOT = "few_shot"
    ZERO_SHOT = "zero_shot"
    ROLE_PLAYING = "role_playing"
    STEP_BY_STEP = "step_by_step"
    SOCRATIC = "socratic"

@dataclass
class PromptTemplate:
    """Template for prompt generation"""
    name: str
    prompt_type: PromptType
    strategy: PromptStrategy
    template: str
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    examples: List[Dict[str, str]] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PromptContext:
    """Context for prompt generation"""
    user_type: Optional[str] = None
    legal_area: Optional[str] = None
    jurisdiction: str = "Kenya"
    urgency: Optional[str] = None
    complexity: Optional[str] = None
    language: str = "English"
    format_preference: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)

class PromptEngine:
    """Advanced prompt engineering engine"""
    
    def __init__(self):
        self.templates = {}
        self.jinja_env = Environment(loader=BaseLoader())
        self.performance_metrics = {
            "prompts_generated": 0,
            "template_usage": {},
            "strategy_usage": {},
            "avg_generation_time": 0.0
        }
        
        # Initialize default templates
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default prompt templates"""
        
        # Legal Query Template
        legal_query_template = PromptTemplate(
            name="kenyan_legal_query",
            prompt_type=PromptType.LEGAL_QUERY,
            strategy=PromptStrategy.CHAIN_OF_THOUGHT,
            template="""You are Counsel, a specialized AI legal assistant for Kenyan jurisdiction with deep expertise in Kenyan law.

User Context:
- User Type: {{ user_type or "General Public" }}
- Legal Area: {{ legal_area or "General Legal Inquiry" }}
- Urgency: {{ urgency or "Normal" }}

Legal Query: {{ query }}

Please provide a comprehensive response following this structure:

1. **Direct Answer**: Provide a clear, direct answer to the query
2. **Legal Framework**: Reference relevant Kenyan laws, regulations, and constitutional provisions
3. **Case Law**: Cite applicable Kenyan case law and precedents where relevant
4. **Practical Steps**: Outline specific actionable steps the user should take
5. **Important Considerations**: Highlight any critical legal considerations, deadlines, or requirements
6. **Professional Advice**: Recommend when to seek professional legal counsel

Ensure your response is:
- Accurate and specific to Kenyan law
- Accessible to the user's level of legal knowledge
- Comprehensive yet concise
- Includes relevant citations and references

Response:""",
            variables=["query", "user_type", "legal_area", "urgency"],
            examples=[
                {
                    "input": "How do I register a company in Kenya?",
                    "output": "To register a company in Kenya under the Companies Act 2015..."
                }
            ]
        )
        
        # Document Generation Template
        doc_generation_template = PromptTemplate(
            name="kenyan_legal_document",
            prompt_type=PromptType.DOCUMENT_GENERATION,
            strategy=PromptStrategy.STEP_BY_STEP,
            template="""You are a legal document drafting specialist for Kenyan jurisdiction.

Document Type: {{ document_type }}
Client Information: {{ client_info }}
Document Parameters: {{ parameters }}

Please generate a professional {{ document_type }} that:

1. **Complies with Kenyan Law**: Ensure full compliance with relevant Kenyan statutes and regulations
2. **Includes Required Elements**: Incorporate all legally required clauses and provisions
3. **Uses Proper Legal Language**: Employ appropriate legal terminology and formatting
4. **Follows Standard Structure**: Use the standard format for this document type in Kenya
5. **Includes Necessary References**: Cite relevant statutory provisions where applicable

Document Requirements:
- Professional legal formatting
- Clear and unambiguous language
- Proper signature and witness sections
- Compliance with {{ jurisdiction }} legal standards
- Include relevant statutory references

Generate the complete document:""",
            variables=["document_type", "client_info", "parameters", "jurisdiction"],
            constraints={
                "max_length": 5000,
                "include_signatures": True,
                "legal_compliance": True
            }
        )
        
        # Legal Analysis Template
        analysis_template = PromptTemplate(
            name="kenyan_legal_analysis",
            prompt_type=PromptType.LEGAL_ANALYSIS,
            strategy=PromptStrategy.SOCRATIC,
            template="""You are conducting a comprehensive legal analysis for Kenyan jurisdiction.

Document/Situation to Analyze: {{ content }}
Analysis Focus: {{ focus_areas }}

Conduct a thorough legal analysis by addressing these key questions:

**1. Legal Framework Analysis**
- What Kenyan laws and regulations apply to this situation?
- Are there any constitutional considerations under the Constitution of Kenya 2010?
- What are the relevant statutory provisions?

**2. Risk Assessment**
- What legal risks are present in this situation?
- What are the potential consequences of different courses of action?
- Are there any compliance issues that need to be addressed?

**3. Precedent Analysis**
- Are there relevant Kenyan court decisions that apply?
- How have similar cases been decided by Kenyan courts?
- What legal principles have been established?

**4. Practical Implications**
- What are the practical steps that should be taken?
- What documentation or procedures are required?
- Are there any deadlines or time-sensitive requirements?

**5. Recommendations**
- What is your professional recommendation?
- What alternative approaches might be considered?
- When should professional legal counsel be engaged?

Provide a detailed analysis addressing each of these areas:""",
            variables=["content", "focus_areas"]
        )
        
        # Add templates to registry
        self.register_template(legal_query_template)
        self.register_template(doc_generation_template)
        self.register_template(analysis_template)
    
    def register_template(self, template: PromptTemplate):
        """Register a new prompt template"""
        self.templates[template.name] = template
        logger.info(f"Registered prompt template: {template.name}")
    
    async def generate_prompt(
        self,
        template_name: str,
        variables: Dict[str, Any],
        context: PromptContext = None,
        strategy_override: PromptStrategy = None
    ) -> Dict[str, Any]:
        """Generate a prompt using the specified template"""
        start_time = time.time()
        
        try:
            if template_name not in self.templates:
                raise ValueError(f"Template '{template_name}' not found")
            
            template = self.templates[template_name]
            context = context or PromptContext()
            
            # Apply strategy override if provided
            effective_strategy = strategy_override or template.strategy
            
            # Generate the prompt
            prompt = await self._generate_from_template(template, variables, context, effective_strategy)
            
            # Update metrics
            self._update_metrics(template_name, effective_strategy, time.time() - start_time)
            
            return {
                "prompt": prompt,
                "template_name": template_name,
                "strategy": effective_strategy.value,
                "context": context,
                "metadata": {
                    "generation_time": time.time() - start_time,
                    "template_type": template.prompt_type.value,
                    "variables_used": list(variables.keys())
                }
            }
            
        except Exception as e:
            logger.error(f"Prompt generation failed: {e}")
            raise
    
    async def _generate_from_template(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any],
        context: PromptContext,
        strategy: PromptStrategy
    ) -> str:
        """Generate prompt from template with strategy application"""
        
        # Prepare template variables
        template_vars = variables.copy()
        template_vars.update({
            "user_type": context.user_type,
            "legal_area": context.legal_area,
            "jurisdiction": context.jurisdiction,
            "urgency": context.urgency,
            "complexity": context.complexity,
            "language": context.language
        })
        
        # Apply strategy-specific enhancements
        enhanced_template = await self._apply_strategy(template, strategy, context)
        
        # Render the template
        jinja_template = self.jinja_env.from_string(enhanced_template.template)
        rendered_prompt = jinja_template.render(**template_vars)
        
        # Apply post-processing
        final_prompt = await self._post_process_prompt(rendered_prompt, template, context)
        
        return final_prompt
    
    async def _apply_strategy(
        self,
        template: PromptTemplate,
        strategy: PromptStrategy,
        context: PromptContext
    ) -> PromptTemplate:
        """Apply prompt engineering strategy to template"""
        enhanced_template = template
        
        if strategy == PromptStrategy.CHAIN_OF_THOUGHT:
            enhanced_template = self._apply_chain_of_thought(template)
        elif strategy == PromptStrategy.FEW_SHOT:
            enhanced_template = self._apply_few_shot(template)
        elif strategy == PromptStrategy.ROLE_PLAYING:
            enhanced_template = self._apply_role_playing(template, context)
        elif strategy == PromptStrategy.STEP_BY_STEP:
            enhanced_template = self._apply_step_by_step(template)
        elif strategy == PromptStrategy.SOCRATIC:
            enhanced_template = self._apply_socratic_method(template)
        
        return enhanced_template
    
    def _apply_chain_of_thought(self, template: PromptTemplate) -> PromptTemplate:
        """Apply chain-of-thought reasoning to template"""
        cot_addition = """

Before providing your final answer, please think through this step by step:

1. **Understanding**: What is the user really asking?
2. **Legal Framework**: What laws and regulations apply?
3. **Analysis**: How do these laws apply to the specific situation?
4. **Reasoning**: What is the logical chain of legal reasoning?
5. **Conclusion**: What is the most appropriate response?

Let me work through this systematically:"""
        
        enhanced_template = PromptTemplate(
            name=template.name + "_cot",
            prompt_type=template.prompt_type,
            strategy=PromptStrategy.CHAIN_OF_THOUGHT,
            template=template.template + cot_addition,
            variables=template.variables,
            metadata=template.metadata,
            examples=template.examples
        )
        
        return enhanced_template
    
    def _apply_few_shot(self, template: PromptTemplate) -> PromptTemplate:
        """Apply few-shot learning with examples"""
        if not template.examples:
            return template
        
        examples_text = "\n\nHere are some examples of similar queries and responses:\n\n"
        
        for i, example in enumerate(template.examples[:3], 1):  # Limit to 3 examples
            examples_text += f"Example {i}:\n"
            examples_text += f"Query: {example['input']}\n"
            examples_text += f"Response: {example['output']}\n\n"
        
        examples_text += "Now, please respond to the current query following a similar approach:\n\n"
        
        enhanced_template = PromptTemplate(
            name=template.name + "_few_shot",
            prompt_type=template.prompt_type,
            strategy=PromptStrategy.FEW_SHOT,
            template=examples_text + template.template,
            variables=template.variables,
            metadata=template.metadata,
            examples=template.examples
        )
        
        return enhanced_template
    
    def _apply_role_playing(self, template: PromptTemplate, context: PromptContext) -> PromptTemplate:
        """Apply role-playing enhancement"""
        role_context = self._determine_role_context(template.prompt_type, context)
        
        role_addition = f"""
You are acting as {role_context['role']} with the following characteristics:
- Expertise: {role_context['expertise']}
- Approach: {role_context['approach']}
- Communication Style: {role_context['style']}

Respond in character as this professional would, maintaining their perspective and expertise level.

"""
        
        enhanced_template = PromptTemplate(
            name=template.name + "_role_play",
            prompt_type=template.prompt_type,
            strategy=PromptStrategy.ROLE_PLAYING,
            template=role_addition + template.template,
            variables=template.variables,
            metadata=template.metadata,
            examples=template.examples
        )
        
        return enhanced_template
    
    def _apply_step_by_step(self, template: PromptTemplate) -> PromptTemplate:
        """Apply step-by-step methodology"""
        step_addition = """

Please approach this systematically by following these steps:

Step 1: Identify the key legal issues
Step 2: Determine applicable laws and regulations
Step 3: Analyze how the law applies to the facts
Step 4: Consider any exceptions or special circumstances
Step 5: Formulate your response with clear reasoning
Step 6: Provide practical next steps

Work through each step methodically:"""
        
        enhanced_template = PromptTemplate(
            name=template.name + "_step_by_step",
            prompt_type=template.prompt_type,
            strategy=PromptStrategy.STEP_BY_STEP,
            template=template.template + step_addition,
            variables=template.variables,
            metadata=template.metadata,
            examples=template.examples
        )
        
        return enhanced_template
    
    def _apply_socratic_method(self, template: PromptTemplate) -> PromptTemplate:
        """Apply Socratic questioning method"""
        # The template already includes Socratic questions, so just ensure proper structure
        return template
    
    def _determine_role_context(self, prompt_type: PromptType, context: PromptContext) -> Dict[str, str]:
        """Determine appropriate role context based on prompt type"""
        role_contexts = {
            PromptType.LEGAL_QUERY: {
                "role": "a senior legal counsel specializing in Kenyan law",
                "expertise": "Comprehensive knowledge of Kenyan legal system, statutes, and case law",
                "approach": "Analytical, thorough, and client-focused",
                "style": "Professional yet accessible, with clear explanations"
            },
            PromptType.DOCUMENT_GENERATION: {
                "role": "an experienced legal document drafter",
                "expertise": "Expert in Kenyan legal document preparation and statutory compliance",
                "approach": "Meticulous, detail-oriented, and compliance-focused",
                "style": "Formal legal writing with precision and clarity"
            },
            PromptType.LEGAL_ANALYSIS: {
                "role": "a legal analyst and researcher",
                "expertise": "Deep analytical skills and comprehensive legal research capabilities",
                "approach": "Systematic, evidence-based, and comprehensive",
                "style": "Analytical and structured with detailed reasoning"
            }
        }
        
        return role_contexts.get(prompt_type, role_contexts[PromptType.LEGAL_QUERY])
    
    async def _post_process_prompt(
        self,
        prompt: str,
        template: PromptTemplate,
        context: PromptContext
    ) -> str:
        """Post-process the generated prompt"""
        
        # Apply constraints if specified
        if template.constraints:
            prompt = self._apply_constraints(prompt, template.constraints)
        
        # Add context-specific enhancements
        if context.language != "English":
            prompt = self._add_language_instruction(prompt, context.language)
        
        if context.format_preference:
            prompt = self._add_format_instruction(prompt, context.format_preference)
        
        return prompt.strip()
    
    def _apply_constraints(self, prompt: str, constraints: Dict[str, Any]) -> str:
        """Apply template constraints to prompt"""
        if constraints.get("max_length"):
            max_length = constraints["max_length"]
            if len(prompt) > max_length:
                # Truncate while preserving structure
                prompt = prompt[:max_length-100] + "\n\n[Response truncated to meet length constraints]"
        
        return prompt
    
    def _add_language_instruction(self, prompt: str, language: str) -> str:
        """Add language-specific instructions"""
        if language != "English":
            language_instruction = f"\n\nPlease provide your response in {language}."
            prompt += language_instruction
        
        return prompt
    
    def _add_format_instruction(self, prompt: str, format_preference: str) -> str:
        """Add format-specific instructions"""
        format_instruction = f"\n\nPlease format your response as: {format_preference}"
        return prompt + format_instruction
    
    def _update_metrics(self, template_name: str, strategy: PromptStrategy, generation_time: float):
        """Update performance metrics"""
        self.performance_metrics["prompts_generated"] += 1
        
        # Update template usage
        if template_name not in self.performance_metrics["template_usage"]:
            self.performance_metrics["template_usage"][template_name] = 0
        self.performance_metrics["template_usage"][template_name] += 1
        
        # Update strategy usage
        strategy_name = strategy.value
        if strategy_name not in self.performance_metrics["strategy_usage"]:
            self.performance_metrics["strategy_usage"][strategy_name] = 0
        self.performance_metrics["strategy_usage"][strategy_name] += 1
        
        # Update average generation time
        total = self.performance_metrics["prompts_generated"]
        current_avg = self.performance_metrics["avg_generation_time"]
        self.performance_metrics["avg_generation_time"] = (
            (current_avg * (total - 1) + generation_time) / total
        )
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available templates"""
        return [
            {
                "name": template.name,
                "type": template.prompt_type.value,
                "strategy": template.strategy.value,
                "variables": template.variables,
                "description": template.metadata.get("description", "")
            }
            for template in self.templates.values()
        ]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return self.performance_metrics.copy()
