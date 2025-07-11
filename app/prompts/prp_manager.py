"""
PRP (Product Requirement Prompts) Manager
Manages and applies structured prompt templates for legal use cases
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class PRPTemplate:
    """Represents a Product Requirement Prompt template"""
    name: str
    category: str
    version: str
    description: str
    user_goal: str
    input_requirements: Dict[str, Any]
    tools_needed: Dict[str, List[str]]
    domain_context: Dict[str, Any]
    analysis_framework: Dict[str, Any]
    expected_outputs: Dict[str, Any]
    confidence_criteria: Dict[str, Any]
    common_scenarios: Dict[str, Any]
    escalation_triggers: List[str]
    quality_checks: List[str]
    template_prompts: Dict[str, str]
    
    # Metadata
    loaded_at: datetime = field(default_factory=datetime.utcnow)
    file_path: Optional[str] = None

class PRPManager:
    """
    Manages Product Requirement Prompt templates and provides
    context-aware prompt generation for legal use cases
    """
    
    def __init__(self, templates_directory: str = None):
        self.templates_directory = Path(templates_directory or self._get_default_templates_dir())
        self.templates: Dict[str, PRPTemplate] = {}
        self.category_index: Dict[str, List[str]] = {}
        self._loaded = False
    
    def _get_default_templates_dir(self) -> str:
        """Get default templates directory"""
        current_dir = Path(__file__).parent
        return str(current_dir / "prp_templates")
    
    async def initialize(self) -> bool:
        """Initialize the PRP manager by loading all templates"""
        try:
            await self.load_all_templates()
            self._loaded = True
            logger.info(f"PRP Manager initialized with {len(self.templates)} templates")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PRP Manager: {e}")
            return False
    
    async def load_all_templates(self):
        """Load all PRP templates from the templates directory"""
        if not self.templates_directory.exists():
            logger.warning(f"Templates directory not found: {self.templates_directory}")
            return
        
        template_files = list(self.templates_directory.glob("*.yaml"))
        
        for template_file in template_files:
            try:
                template = await self.load_template(template_file)
                if template:
                    self.templates[template.name] = template
                    
                    # Update category index
                    category = template.category
                    if category not in self.category_index:
                        self.category_index[category] = []
                    self.category_index[category].append(template.name)
                    
                    logger.debug(f"Loaded template: {template.name}")
                    
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
    
    async def load_template(self, template_path: Union[str, Path]) -> Optional[PRPTemplate]:
        """Load a single PRP template from file"""
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                template_data = yaml.safe_load(file)
            
            # Validate required fields
            required_fields = ['name', 'category', 'version', 'description', 'user_goal']
            for field in required_fields:
                if field not in template_data:
                    logger.error(f"Template {template_path} missing required field: {field}")
                    return None
            
            # Create PRPTemplate instance
            template = PRPTemplate(
                name=template_data['name'],
                category=template_data['category'],
                version=template_data['version'],
                description=template_data['description'],
                user_goal=template_data['user_goal'],
                input_requirements=template_data.get('input_requirements', {}),
                tools_needed=template_data.get('tools_needed', {}),
                domain_context=template_data.get('domain_context', {}),
                analysis_framework=template_data.get('analysis_framework', {}),
                expected_outputs=template_data.get('expected_outputs', {}),
                confidence_criteria=template_data.get('confidence_criteria', {}),
                common_scenarios=template_data.get('common_scenarios', {}),
                escalation_triggers=template_data.get('escalation_triggers', []),
                quality_checks=template_data.get('quality_checks', []),
                template_prompts=template_data.get('template_prompts', {}),
                file_path=str(template_path)
            )
            
            return template
            
        except Exception as e:
            logger.error(f"Error loading template from {template_path}: {e}")
            return None
    
    def get_template(self, template_name: str) -> Optional[PRPTemplate]:
        """Get a specific template by name"""
        return self.templates.get(template_name)
    
    def get_templates_by_category(self, category: str) -> List[PRPTemplate]:
        """Get all templates in a specific category"""
        template_names = self.category_index.get(category, [])
        return [self.templates[name] for name in template_names if name in self.templates]
    
    def list_categories(self) -> List[str]:
        """List all available template categories"""
        return list(self.category_index.keys())
    
    def list_templates(self) -> List[str]:
        """List all available template names"""
        return list(self.templates.keys())
    
    def select_template_for_context(self, context: Dict[str, Any]) -> Optional[PRPTemplate]:
        """Select the most appropriate template based on context"""
        
        # Extract context information
        detected_domains = context.get("detected_domains", [])
        query_info = context.get("query_info", {})
        query = query_info.get("query", "").lower()
        routing_rules = context.get("routing_rules", {})
        
        # Priority mapping for domain to template category
        domain_template_map = {
            "employment": "employment_law",
            "contract": "contract_law", 
            "property": "property_law",
            "corporate": "corporate_law"
        }
        
        # Try to match by detected domains
        for domain in detected_domains:
            if domain in domain_template_map:
                category = domain_template_map[domain]
                templates = self.get_templates_by_category(category)
                if templates:
                    return templates[0]  # Return first template in category
        
        # Try to match by routing rules
        if "employment_matters" in routing_rules:
            templates = self.get_templates_by_category("employment_law")
            if templates:
                return templates[0]
        
        if "document_processing" in routing_rules and "contract" in query:
            templates = self.get_templates_by_category("contract_law")
            if templates:
                return templates[0]
        
        # Try to match by query keywords
        keyword_category_map = {
            "employment": "employment_law",
            "contract": "contract_law",
            "lease": "property_law",
            "rent": "property_law",
            "company": "corporate_law",
            "corporate": "corporate_law"
        }
        
        for keyword, category in keyword_category_map.items():
            if keyword in query:
                templates = self.get_templates_by_category(category)
                if templates:
                    return templates[0]
        
        # Default fallback - return first available template
        if self.templates:
            return list(self.templates.values())[0]
        
        return None
    
    def generate_prompt(
        self,
        template_name: str,
        prompt_type: str,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Optional[str]:
        """Generate a prompt using a specific template and prompt type"""
        
        template = self.get_template(template_name)
        if not template:
            logger.error(f"Template not found: {template_name}")
            return None
        
        prompt_template = template.template_prompts.get(prompt_type)
        if not prompt_template:
            logger.error(f"Prompt type '{prompt_type}' not found in template '{template_name}'")
            return None
        
        try:
            # Format the prompt with input data
            formatted_prompt = prompt_template.format(**input_data)
            
            # Add context-specific enhancements
            if context:
                enhanced_prompt = self._enhance_prompt_with_context(formatted_prompt, template, context)
                return enhanced_prompt
            
            return formatted_prompt
            
        except KeyError as e:
            logger.error(f"Missing required input data for prompt generation: {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating prompt: {e}")
            return None
    
    def _enhance_prompt_with_context(
        self,
        base_prompt: str,
        template: PRPTemplate,
        context: Dict[str, Any]
    ) -> str:
        """Enhance prompt with context-specific information"""
        
        enhancements = []
        
        # Add system constraints from context
        system_context = context.get("system_context", {})
        constraints = system_context.get("constraints", [])
        if constraints:
            constraints_text = "\n".join(f"- {constraint}" for constraint in constraints)
            enhancements.append(f"System Constraints:\n{constraints_text}")
        
        # Add domain-specific context
        domain_context = context.get("domain_context", {})
        primary_sources = domain_context.get("primary_sources", [])
        if primary_sources:
            sources_text = "\n".join(f"- {source}" for source in primary_sources[:3])
            enhancements.append(f"Primary Legal Sources:\n{sources_text}")
        
        # Add quality standards
        response_context = context.get("response_context", {})
        quality_standards = response_context.get("quality_standards", {})
        if quality_standards:
            min_confidence = quality_standards.get("minimum_confidence", 0.7)
            enhancements.append(f"Minimum Confidence Required: {min_confidence}")
        
        # Add urgency context
        urgency_analysis = context.get("urgency_analysis", {})
        if urgency_analysis.get("level") == "high":
            enhancements.append("URGENT: Provide concise, actionable guidance.")
        
        # Combine base prompt with enhancements
        if enhancements:
            enhanced_prompt = base_prompt + "\n\nAdditional Context:\n" + "\n\n".join(enhancements)
            return enhanced_prompt
        
        return base_prompt
    
    def validate_input_requirements(
        self,
        template_name: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate input data against template requirements"""
        
        template = self.get_template(template_name)
        if not template:
            return {"valid": False, "error": f"Template not found: {template_name}"}
        
        requirements = template.input_requirements
        required_fields = requirements.get("required", [])
        optional_fields = requirements.get("optional", [])
        
        validation_result = {
            "valid": True,
            "missing_required": [],
            "missing_optional": [],
            "extra_fields": []
        }
        
        # Check required fields
        for field in required_fields:
            if field not in input_data:
                validation_result["missing_required"].append(field)
                validation_result["valid"] = False
        
        # Check optional fields
        for field in optional_fields:
            if field not in input_data:
                validation_result["missing_optional"].append(field)
        
        # Check for extra fields
        all_expected_fields = set(required_fields + optional_fields)
        provided_fields = set(input_data.keys())
        extra_fields = provided_fields - all_expected_fields
        validation_result["extra_fields"] = list(extra_fields)
        
        return validation_result
    
    def get_template_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a template"""
        
        template = self.get_template(template_name)
        if not template:
            return None
        
        return {
            "name": template.name,
            "category": template.category,
            "version": template.version,
            "description": template.description,
            "user_goal": template.user_goal,
            "input_requirements": template.input_requirements,
            "tools_needed": template.tools_needed,
            "available_prompts": list(template.template_prompts.keys()),
            "common_scenarios": list(template.common_scenarios.keys()),
            "quality_checks": template.quality_checks,
            "loaded_at": template.loaded_at.isoformat(),
            "file_path": template.file_path
        }
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get statistics about the PRP manager"""
        
        return {
            "total_templates": len(self.templates),
            "categories": list(self.category_index.keys()),
            "templates_by_category": {
                category: len(templates) 
                for category, templates in self.category_index.items()
            },
            "loaded": self._loaded,
            "templates_directory": str(self.templates_directory)
        }
