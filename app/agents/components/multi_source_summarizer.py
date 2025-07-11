"""
Multi-Source Summarizer Component - Context-aware document summarization
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .base_component import BaseComponent, ComponentResult, ComponentStatus, ComponentError
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

@dataclass
class SummarizationStrategy:
    """Configuration for summarization strategy"""
    name: str
    max_length: int = 500
    focus_areas: List[str] = None
    include_citations: bool = True
    preserve_legal_terms: bool = True
    extract_key_points: bool = True
    confidence_threshold: float = 0.6

class MultiSourceSummarizer(BaseComponent):
    """
    Context-aware multi-source summarizer that intelligently
    combines and summarizes documents based on legal context
    """
    
    def __init__(self, context_manager=None, ai_service=None):
        super().__init__("MultiSourceSummarizer", context_manager)
        self.ai_service = ai_service or AIService()
        
        # Summarization strategies
        self.strategies = {
            "concise": SummarizationStrategy(
                name="concise",
                max_length=300,
                extract_key_points=True,
                confidence_threshold=0.7
            ),
            "comprehensive": SummarizationStrategy(
                name="comprehensive",
                max_length=800,
                focus_areas=["legal_principles", "precedents", "procedures"],
                include_citations=True,
                extract_key_points=True,
                confidence_threshold=0.6
            ),
            "focused": SummarizationStrategy(
                name="focused",
                max_length=500,
                preserve_legal_terms=True,
                include_citations=True,
                confidence_threshold=0.7
            ),
            "technical": SummarizationStrategy(
                name="technical",
                max_length=600,
                focus_areas=["definitions", "requirements", "procedures"],
                preserve_legal_terms=True,
                include_citations=True,
                confidence_threshold=0.8
            )
        }
    
    async def _initialize_component(self):
        """Initialize AI service"""
        # AI service is typically initialized elsewhere
        pass
    
    async def _validate_input(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate summarization input"""
        if "documents" not in input_data:
            return {"valid": False, "error": "Documents are required for summarization"}
        
        documents = input_data["documents"]
        if not isinstance(documents, list) or len(documents) == 0:
            return {"valid": False, "error": "Documents must be a non-empty list"}
        
        # Check if documents have required fields
        for i, doc in enumerate(documents):
            if not isinstance(doc, dict):
                return {"valid": False, "error": f"Document {i} must be a dictionary"}
            
            if "content" not in doc and "title" not in doc:
                return {"valid": False, "error": f"Document {i} must have content or title"}
        
        return {"valid": True}
    
    async def _execute_component(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute context-aware multi-source summarization"""
        
        documents = input_data["documents"]
        query = input_data.get("query", "")
        
        # Select summarization strategy based on context
        strategy = self._select_summarization_strategy(context, input_data)
        
        # Prepare documents for summarization
        prepared_docs = await self._prepare_documents(documents, context, strategy)
        
        # Group documents by relevance and source
        grouped_docs = self._group_documents(prepared_docs, strategy)
        
        # Generate summaries for each group
        group_summaries = await self._summarize_groups(grouped_docs, query, strategy, context)
        
        # Combine group summaries into final summary
        final_summary = await self._combine_summaries(group_summaries, query, strategy, context)
        
        # Extract key insights and citations
        insights = self._extract_key_insights(group_summaries, strategy)
        citations = self._extract_citations(prepared_docs, strategy)
        
        # Generate reasoning steps
        reasoning_steps = self._generate_reasoning_steps(strategy, len(documents), len(group_summaries))
        
        return {
            "summary": final_summary,
            "key_insights": insights,
            "citations": citations,
            "strategy_used": strategy.name,
            "documents_processed": len(documents),
            "groups_created": len(grouped_docs),
            "reasoning_steps": reasoning_steps,
            "source_breakdown": self._analyze_source_breakdown(prepared_docs)
        }
    
    def _select_summarization_strategy(self, context: Dict[str, Any], input_data: Dict[str, Any]) -> SummarizationStrategy:
        """Select appropriate summarization strategy based on context"""
        
        # Check for explicit strategy in input
        if "strategy" in input_data and input_data["strategy"] in self.strategies:
            return self.strategies[input_data["strategy"]]
        
        # Analyze context for strategy selection
        query_complexity = context.get("query_complexity", {})
        urgency_analysis = context.get("urgency_analysis", {})
        detected_domains = context.get("detected_domains", [])
        
        # High urgency -> concise strategy
        if urgency_analysis.get("level") == "high":
            return self.strategies["concise"]
        
        # Technical domains -> technical strategy
        if any(domain in ["employment", "contract"] for domain in detected_domains):
            return self.strategies["technical"]
        
        # High complexity -> comprehensive strategy
        if query_complexity.get("level") == "high":
            return self.strategies["comprehensive"]
        
        # Default to focused strategy
        return self.strategies["focused"]
    
    async def _prepare_documents(
        self,
        documents: List[Dict[str, Any]],
        context: Dict[str, Any],
        strategy: SummarizationStrategy
    ) -> List[Dict[str, Any]]:
        """Prepare documents for summarization"""
        
        prepared_docs = []
        
        for doc in documents:
            prepared_doc = doc.copy()
            
            # Extract relevant content
            content = doc.get("content", "")
            title = doc.get("title", "")
            
            # Combine title and content
            full_text = f"{title}\n\n{content}" if title else content
            
            # Truncate if too long (keep most relevant parts)
            if len(full_text) > 2000:  # Reasonable limit for processing
                full_text = self._extract_relevant_excerpt(full_text, context, 2000)
            
            prepared_doc["processed_content"] = full_text
            prepared_doc["content_length"] = len(full_text)
            prepared_doc["relevance_score"] = doc.get("relevance_score", 0.5)
            
            # Add domain classification
            prepared_doc["domain_classification"] = self._classify_document_domain(full_text, context)
            
            prepared_docs.append(prepared_doc)
        
        # Sort by relevance score
        prepared_docs.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return prepared_docs
    
    def _extract_relevant_excerpt(self, text: str, context: Dict[str, Any], max_length: int) -> str:
        """Extract most relevant excerpt from long text"""
        
        # Get query and domain context
        query_info = context.get("query_info", {})
        query = query_info.get("query", "")
        detected_domains = context.get("detected_domains", [])
        
        # Split into sentences
        sentences = text.split('. ')
        
        # Score sentences based on relevance
        scored_sentences = []
        query_words = set(query.lower().split()) if query else set()
        domain_words = set()
        
        # Add domain-specific keywords
        domain_keywords = {
            "employment": ["employment", "employee", "employer", "work", "salary", "termination"],
            "contract": ["contract", "agreement", "clause", "terms", "breach", "obligation"],
            "property": ["property", "land", "lease", "rent", "landlord", "tenant"]
        }
        
        for domain in detected_domains:
            if domain in domain_keywords:
                domain_words.update(domain_keywords[domain])
        
        for sentence in sentences:
            sentence_words = set(sentence.lower().split())
            
            # Calculate relevance score
            query_overlap = len(query_words.intersection(sentence_words)) / max(len(query_words), 1)
            domain_overlap = len(domain_words.intersection(sentence_words)) / max(len(domain_words), 1)
            
            score = query_overlap * 0.7 + domain_overlap * 0.3
            scored_sentences.append((score, sentence))
        
        # Sort by score and select top sentences
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        
        # Build excerpt within length limit
        excerpt = ""
        for score, sentence in scored_sentences:
            if len(excerpt) + len(sentence) + 2 <= max_length:  # +2 for '. '
                excerpt += sentence + ". "
            else:
                break
        
        return excerpt.strip()
    
    def _classify_document_domain(self, text: str, context: Dict[str, Any]) -> List[str]:
        """Classify document into legal domains"""
        
        text_lower = text.lower()
        domains = []
        
        # Domain classification keywords
        domain_patterns = {
            "employment": ["employment", "employee", "employer", "job", "work", "salary", "termination", "leave"],
            "contract": ["contract", "agreement", "clause", "terms", "breach", "obligation", "consideration"],
            "property": ["property", "land", "lease", "rent", "landlord", "tenant", "real estate"],
            "criminal": ["criminal", "crime", "offense", "prosecution", "defendant", "guilty"],
            "civil": ["civil", "plaintiff", "defendant", "damages", "liability", "tort"],
            "constitutional": ["constitution", "constitutional", "rights", "fundamental", "bill of rights"]
        }
        
        for domain, keywords in domain_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                domains.append(domain)
        
        return domains or ["general"]
    
    def _group_documents(self, documents: List[Dict[str, Any]], strategy: SummarizationStrategy) -> Dict[str, List[Dict[str, Any]]]:
        """Group documents by domain and source for targeted summarization"""
        
        groups = {}
        
        for doc in documents:
            # Group by primary domain
            domains = doc.get("domain_classification", ["general"])
            primary_domain = domains[0] if domains else "general"
            
            if primary_domain not in groups:
                groups[primary_domain] = []
            
            groups[primary_domain].append(doc)
        
        # Limit group sizes to avoid overwhelming the summarizer
        max_docs_per_group = 5
        for domain, docs in groups.items():
            if len(docs) > max_docs_per_group:
                # Keep highest relevance documents
                docs.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
                groups[domain] = docs[:max_docs_per_group]
        
        return groups
    
    async def _summarize_groups(
        self,
        grouped_docs: Dict[str, List[Dict[str, Any]]],
        query: str,
        strategy: SummarizationStrategy,
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """Summarize each group of documents"""
        
        group_summaries = {}
        
        for domain, docs in grouped_docs.items():
            try:
                # Combine documents in the group
                combined_text = self._combine_group_documents(docs, strategy)
                
                # Create domain-specific prompt
                prompt = self._create_summarization_prompt(combined_text, query, domain, strategy, context)
                
                # Generate summary using AI service
                summary_result = await self.ai_service._generate_with_fallback(prompt, "legal_summarization")
                
                group_summaries[domain] = summary_result.get("response", "")
                
            except Exception as e:
                logger.warning(f"Failed to summarize {domain} group: {e}")
                # Create fallback summary
                group_summaries[domain] = self._create_fallback_summary(docs, domain)
        
        return group_summaries
    
    def _combine_group_documents(self, docs: List[Dict[str, Any]], strategy: SummarizationStrategy) -> str:
        """Combine documents in a group for summarization"""
        
        combined_parts = []
        
        for i, doc in enumerate(docs):
            content = doc.get("processed_content", "")
            source = doc.get("source", "Unknown")
            title = doc.get("title", f"Document {i+1}")
            
            # Format document section
            section = f"=== {title} (Source: {source}) ===\n{content}\n"
            combined_parts.append(section)
        
        return "\n".join(combined_parts)
    
    def _create_summarization_prompt(
        self,
        text: str,
        query: str,
        domain: str,
        strategy: SummarizationStrategy,
        context: Dict[str, Any]
    ) -> str:
        """Create context-aware summarization prompt"""
        
        # Get system constraints from context
        system_context = context.get("system_context", {})
        constraints = system_context.get("constraints", [])
        
        prompt = f"""
You are a legal AI assistant specializing in Kenyan law. Summarize the following legal documents with focus on {domain} law.

Query Context: {query}

Legal Documents:
{text}

Instructions:
1. Create a {strategy.max_length}-word summary focusing on {domain} legal aspects
2. {"Include specific citations and references" if strategy.include_citations else "Focus on key concepts without detailed citations"}
3. {"Preserve all legal terminology exactly as written" if strategy.preserve_legal_terms else "Explain legal terms clearly"}
4. {"Extract and highlight key legal points" if strategy.extract_key_points else "Provide a flowing narrative summary"}

System Constraints:
{chr(10).join(f"- {constraint}" for constraint in constraints)}

Focus Areas: {', '.join(strategy.focus_areas or ['general legal analysis'])}

Provide a clear, accurate summary that directly addresses the query while maintaining legal precision.

Summary:"""
        
        return prompt

    async def _combine_summaries(
        self,
        group_summaries: Dict[str, str],
        query: str,
        strategy: SummarizationStrategy,
        context: Dict[str, Any]
    ) -> str:
        """Combine group summaries into final comprehensive summary"""

        if len(group_summaries) == 1:
            return list(group_summaries.values())[0]

        # Create combination prompt
        summaries_text = "\n\n".join([
            f"=== {domain.upper()} LAW SUMMARY ===\n{summary}"
            for domain, summary in group_summaries.items()
        ])

        prompt = f"""
Combine the following domain-specific legal summaries into a coherent, comprehensive response to the query: "{query}"

Domain Summaries:
{summaries_text}

Instructions:
1. Create a unified response that addresses the query directly
2. Integrate insights from all relevant legal domains
3. Maintain logical flow and legal accuracy
4. Highlight any conflicts or complementary aspects between domains
5. Keep the final summary within {strategy.max_length} words

Final Integrated Summary:"""

        try:
            result = await self.ai_service._generate_with_fallback(prompt, "legal_integration")
            return result.get("response", "")
        except Exception as e:
            logger.warning(f"Failed to combine summaries: {e}")
            # Fallback: concatenate summaries
            return "\n\n".join(group_summaries.values())

    def _extract_key_insights(self, group_summaries: Dict[str, str], strategy: SummarizationStrategy) -> List[str]:
        """Extract key insights from summaries"""

        if not strategy.extract_key_points:
            return []

        insights = []

        # Extract insights from each domain summary
        for domain, summary in group_summaries.items():
            domain_insights = self._extract_domain_insights(summary, domain)
            insights.extend(domain_insights)

        # Remove duplicates and limit count
        unique_insights = list(dict.fromkeys(insights))  # Preserves order
        return unique_insights[:10]  # Limit to top 10 insights

    def _extract_domain_insights(self, summary: str, domain: str) -> List[str]:
        """Extract insights from a domain-specific summary"""

        insights = []
        sentences = summary.split('. ')

        # Keywords that indicate important insights
        insight_indicators = [
            "must", "shall", "required", "prohibited", "entitled", "liable",
            "according to", "under the", "section", "act", "regulation",
            "court held", "established", "principle", "precedent"
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Avoid very short sentences
                if any(indicator in sentence.lower() for indicator in insight_indicators):
                    insights.append(f"[{domain.upper()}] {sentence}")

        return insights[:3]  # Limit per domain

    def _extract_citations(self, documents: List[Dict[str, Any]], strategy: SummarizationStrategy) -> List[Dict[str, Any]]:
        """Extract and format citations from documents"""

        if not strategy.include_citations:
            return []

        citations = []

        for doc in documents:
            citation = {
                "title": doc.get("title", "Unknown Document"),
                "source": doc.get("source", "Unknown Source"),
                "url": doc.get("url"),
                "document_type": doc.get("document_type", "unknown"),
                "relevance_score": doc.get("relevance_score", 0.0)
            }

            # Add formal citation if available
            if "citation" in doc:
                citation["formal_citation"] = doc["citation"]
            else:
                citation["formal_citation"] = self._generate_citation(doc)

            citations.append(citation)

        # Sort by relevance and limit
        citations.sort(key=lambda x: x["relevance_score"], reverse=True)
        return citations[:10]  # Limit to top 10 citations

    def _generate_citation(self, document: Dict[str, Any]) -> str:
        """Generate a formal citation for a document"""

        title = document.get("title", "Unknown Document")
        source = document.get("source", "Unknown Source")
        doc_type = document.get("document_type", "document")

        # Basic citation format
        if doc_type == "legislation":
            return f"{title}, Kenya"
        elif doc_type == "case":
            return f"{title}"
        else:
            return f"{title} ({source})"

    def _create_fallback_summary(self, docs: List[Dict[str, Any]], domain: str) -> str:
        """Create a fallback summary when AI summarization fails"""

        if not docs:
            return f"No {domain} documents available for summarization."

        # Extract key information
        titles = [doc.get("title", "Unknown") for doc in docs[:3]]
        sources = list(set(doc.get("source", "Unknown") for doc in docs))

        return f"Based on {len(docs)} {domain} documents from {', '.join(sources)}, including: {', '.join(titles)}. Detailed analysis requires manual review."

    def _analyze_source_breakdown(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the breakdown of sources in the documents"""

        source_counts = {}
        domain_counts = {}
        total_docs = len(documents)

        for doc in documents:
            # Count sources
            source = doc.get("source", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1

            # Count domains
            domains = doc.get("domain_classification", ["general"])
            for domain in domains:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

        return {
            "total_documents": total_docs,
            "sources": source_counts,
            "domains": domain_counts,
            "source_diversity": len(source_counts),
            "domain_diversity": len(domain_counts)
        }

    def _generate_reasoning_steps(self, strategy: SummarizationStrategy, doc_count: int, group_count: int) -> List[str]:
        """Generate reasoning steps for the summarization process"""

        steps = [
            f"Selected '{strategy.name}' summarization strategy",
            f"Processed {doc_count} documents across {group_count} legal domains"
        ]

        if strategy.preserve_legal_terms:
            steps.append("Preserved legal terminology for accuracy")

        if strategy.include_citations:
            steps.append("Included citations and source references")

        if strategy.extract_key_points:
            steps.append("Extracted key legal insights and principles")

        if group_count > 1:
            steps.append("Integrated insights across multiple legal domains")

        steps.append(f"Generated summary within {strategy.max_length} word limit")

        return steps

    async def _calculate_confidence(self, output_data: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Calculate confidence based on summarization quality"""

        summary = output_data.get("summary", "")
        documents_processed = output_data.get("documents_processed", 0)
        citations = output_data.get("citations", [])

        # Base confidence on summary length and content
        if not summary or len(summary) < 50:
            return 0.1

        # Factor in number of documents processed
        doc_factor = min(documents_processed / 5, 1.0)  # Optimal around 5 docs

        # Factor in citation quality
        citation_factor = min(len(citations) / 3, 1.0)  # Optimal around 3 citations

        # Factor in domain coverage
        source_breakdown = output_data.get("source_breakdown", {})
        domain_diversity = source_breakdown.get("domain_diversity", 1)
        diversity_factor = min(domain_diversity / 2, 1.0)  # Optimal around 2 domains

        # Combine factors
        confidence = 0.4 + (doc_factor * 0.3) + (citation_factor * 0.2) + (diversity_factor * 0.1)

        return min(1.0, max(0.0, confidence))
