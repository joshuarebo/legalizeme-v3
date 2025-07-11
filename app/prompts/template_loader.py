"""
Template Loader - Utility for loading and managing prompt templates
"""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TemplateMetadata:
    """Metadata for a loaded template"""
    name: str
    file_path: str
    loaded_at: datetime
    file_size: int
    checksum: str

class TemplateLoader:
    """
    Utility class for loading and managing various types of prompt templates
    Supports YAML and JSON formats with validation and caching
    """
    
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self.template_cache: Dict[str, Dict[str, Any]] = {}
        self.metadata_cache: Dict[str, TemplateMetadata] = {}
    
    async def load_template_file(
        self,
        file_path: Union[str, Path],
        validate: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Load a template file (YAML or JSON)"""
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"Template file not found: {file_path}")
            return None
        
        # Check cache first
        if self.cache_enabled and str(file_path) in self.template_cache:
            cached_metadata = self.metadata_cache.get(str(file_path))
            if cached_metadata and self._is_cache_valid(file_path, cached_metadata):
                logger.debug(f"Using cached template: {file_path}")
                return self.template_cache[str(file_path)]
        
        try:
            # Load file content
            with open(file_path, 'r', encoding='utf-8') as file:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    template_data = yaml.safe_load(file)
                elif file_path.suffix.lower() == '.json':
                    template_data = json.load(file)
                else:
                    logger.error(f"Unsupported template file format: {file_path.suffix}")
                    return None
            
            # Validate template if requested
            if validate:
                validation_result = self.validate_template(template_data, file_path)
                if not validation_result["valid"]:
                    logger.error(f"Template validation failed for {file_path}: {validation_result['errors']}")
                    return None
            
            # Cache the template
            if self.cache_enabled:
                self._cache_template(file_path, template_data)
            
            logger.debug(f"Successfully loaded template: {file_path}")
            return template_data
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading template {file_path}: {e}")
            return None
    
    def validate_template(
        self,
        template_data: Dict[str, Any],
        file_path: Path = None
    ) -> Dict[str, Any]:
        """Validate template structure and content"""
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check for required top-level fields
        required_fields = ["name", "category", "version", "description"]
        for field in required_fields:
            if field not in template_data:
                validation_result["errors"].append(f"Missing required field: {field}")
                validation_result["valid"] = False
        
        # Validate name field
        if "name" in template_data:
            name = template_data["name"]
            if not isinstance(name, str) or len(name.strip()) == 0:
                validation_result["errors"].append("Name must be a non-empty string")
                validation_result["valid"] = False
        
        # Validate category field
        if "category" in template_data:
            category = template_data["category"]
            valid_categories = [
                "employment_law", "contract_law", "property_law", 
                "corporate_law", "criminal_law", "civil_law", "general"
            ]
            if category not in valid_categories:
                validation_result["warnings"].append(f"Category '{category}' not in standard categories")
        
        # Validate version field
        if "version" in template_data:
            version = template_data["version"]
            if not isinstance(version, str):
                validation_result["errors"].append("Version must be a string")
                validation_result["valid"] = False
        
        # Validate input requirements structure
        if "input_requirements" in template_data:
            input_req = template_data["input_requirements"]
            if not isinstance(input_req, dict):
                validation_result["errors"].append("input_requirements must be a dictionary")
                validation_result["valid"] = False
            else:
                # Check for required and optional fields
                if "required" in input_req and not isinstance(input_req["required"], list):
                    validation_result["errors"].append("input_requirements.required must be a list")
                    validation_result["valid"] = False
                
                if "optional" in input_req and not isinstance(input_req["optional"], list):
                    validation_result["errors"].append("input_requirements.optional must be a list")
                    validation_result["valid"] = False
        
        # Validate tools_needed structure
        if "tools_needed" in template_data:
            tools = template_data["tools_needed"]
            if not isinstance(tools, dict):
                validation_result["errors"].append("tools_needed must be a dictionary")
                validation_result["valid"] = False
            else:
                for tool_category, tool_list in tools.items():
                    if not isinstance(tool_list, list):
                        validation_result["errors"].append(f"tools_needed.{tool_category} must be a list")
                        validation_result["valid"] = False
        
        # Validate template_prompts structure
        if "template_prompts" in template_data:
            prompts = template_data["template_prompts"]
            if not isinstance(prompts, dict):
                validation_result["errors"].append("template_prompts must be a dictionary")
                validation_result["valid"] = False
            else:
                for prompt_name, prompt_content in prompts.items():
                    if not isinstance(prompt_content, str):
                        validation_result["errors"].append(f"template_prompts.{prompt_name} must be a string")
                        validation_result["valid"] = False
                    elif len(prompt_content.strip()) == 0:
                        validation_result["warnings"].append(f"template_prompts.{prompt_name} is empty")
        
        # Check for common typos in field names
        common_typos = {
            "discription": "description",
            "catagory": "category",
            "requirments": "requirements",
            "anaylsis": "analysis"
        }
        
        for typo, correct in common_typos.items():
            if typo in template_data:
                validation_result["warnings"].append(f"Possible typo: '{typo}' should be '{correct}'")
        
        return validation_result
    
    def _is_cache_valid(self, file_path: Path, metadata: TemplateMetadata) -> bool:
        """Check if cached template is still valid"""
        try:
            current_stat = file_path.stat()
            current_size = current_stat.st_size
            current_mtime = current_stat.st_mtime
            
            # Simple validation based on file size and modification time
            return (current_size == metadata.file_size and 
                   current_mtime <= metadata.loaded_at.timestamp())
        except Exception:
            return False
    
    def _cache_template(self, file_path: Path, template_data: Dict[str, Any]):
        """Cache a loaded template"""
        try:
            file_stat = file_path.stat()
            
            # Create metadata
            metadata = TemplateMetadata(
                name=template_data.get("name", "unknown"),
                file_path=str(file_path),
                loaded_at=datetime.utcnow(),
                file_size=file_stat.st_size,
                checksum=str(hash(str(template_data)))  # Simple checksum
            )
            
            # Cache template and metadata
            self.template_cache[str(file_path)] = template_data
            self.metadata_cache[str(file_path)] = metadata
            
        except Exception as e:
            logger.warning(f"Failed to cache template {file_path}: {e}")
    
    def clear_cache(self):
        """Clear the template cache"""
        self.template_cache.clear()
        self.metadata_cache.clear()
        logger.info("Template cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cached_templates": len(self.template_cache),
            "cache_enabled": self.cache_enabled,
            "cache_size_bytes": sum(
                len(str(template)) for template in self.template_cache.values()
            ),
            "cached_files": list(self.template_cache.keys())
        }
    
    async def load_templates_from_directory(
        self,
        directory_path: Union[str, Path],
        pattern: str = "*.yaml",
        validate: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """Load all templates from a directory"""
        
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            logger.error(f"Directory not found or not a directory: {directory_path}")
            return {}
        
        templates = {}
        template_files = list(directory_path.glob(pattern))
        
        for template_file in template_files:
            try:
                template_data = await self.load_template_file(template_file, validate)
                if template_data:
                    template_name = template_data.get("name", template_file.stem)
                    templates[template_name] = template_data
                    logger.debug(f"Loaded template: {template_name}")
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
        
        logger.info(f"Loaded {len(templates)} templates from {directory_path}")
        return templates
    
    def export_template(
        self,
        template_data: Dict[str, Any],
        output_path: Union[str, Path],
        format: str = "yaml"
    ) -> bool:
        """Export template data to file"""
        
        output_path = Path(output_path)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                if format.lower() == "yaml":
                    yaml.dump(template_data, file, default_flow_style=False, indent=2)
                elif format.lower() == "json":
                    json.dump(template_data, file, indent=2, ensure_ascii=False)
                else:
                    logger.error(f"Unsupported export format: {format}")
                    return False
            
            logger.info(f"Template exported to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export template to {output_path}: {e}")
            return False
    
    def merge_templates(
        self,
        base_template: Dict[str, Any],
        override_template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge two templates, with override taking precedence"""
        
        merged = base_template.copy()
        
        for key, value in override_template.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                merged[key] = self.merge_templates(merged[key], value)
            else:
                # Override value
                merged[key] = value
        
        return merged
