import logging
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import re
import numpy as np
from pathlib import Path

# Optional imports for enhanced capabilities
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

from app.config import settings
from app.services.vector_service import VectorService
from app.services.ai_service import AIService
from app.models.document import Document
from app.database import SessionLocal

logger = logging.getLogger(__name__)

@dataclass
class LegalSource:
    """Represents a legal source with citation information"""
    title: str
    source: str
    url: Optional[str] = None
    document_type: str = "unknown"
    relevance_score: float = 0.0
    excerpt: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    citation: str = ""

@dataclass
class RAGResponse:
    """Enhanced RAG response with sources and confidence"""
    response_text: str
    confidence_score: float
    sources: List[LegalSource]
    model_used: str = "unknown"
    retrieval_strategy: str = "semantic"
    processing_time_ms: float = 0.0
    total_documents_searched: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

class LegalRAGService:
    """Enhanced RAG service for legal document retrieval and generation"""
    
    def __init__(self, vector_service: VectorService = None, ai_service: AIService = None):
        self.vector_service = vector_service or VectorService()
        self.ai_service = ai_service or AIService()
        
        # ChromaDB setup
        self.chroma_client = None
        self.legal_collection = None
        self.collection_name = "enhanced_legal_documents"
        
        # Embedding models
        self.embedding_model = None
        self.bedrock_client = None
        
        # Configuration
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.max_sources = 5
        self.min_confidence_threshold = 0.3
        
        # Performance tracking
        self.metrics = {
            "total_queries": 0,
            "successful_retrievals": 0,
            "avg_response_time": 0.0,
            "cache_hits": 0
        }
        
        self._initialized = False
        
    async def initialize(self):
        """Initialize the enhanced RAG service"""
        if self._initialized:
            return
            
        try:
            logger.info("Initializing Enhanced Legal RAG Service...")
            
            # Initialize ChromaDB
            await self._initialize_chromadb()
            
            # Initialize embedding models
            await self._initialize_embedding_models()
            
            # Initialize AWS Bedrock for embeddings (if available)
            await self._initialize_bedrock()
            
            # Initialize base services
            await self.vector_service.initialize()
            
            self._initialized = True
            logger.info("Enhanced Legal RAG Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced Legal RAG Service: {e}")
            raise
    
    async def _initialize_chromadb(self):
        """Initialize ChromaDB with enhanced configuration"""
        if not HAS_CHROMADB:
            logger.warning("ChromaDB not available, using fallback vector service")
            return
            
        try:
            # Create persistent directory
            chroma_dir = Path(getattr(settings, 'CHROMA_PERSIST_DIRECTORY', './chroma_db'))
            chroma_dir.mkdir(exist_ok=True)
            
            # Initialize client
            self.chroma_client = chromadb.PersistentClient(
                path=str(chroma_dir),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create enhanced collection
            try:
                self.legal_collection = self.chroma_client.get_collection(
                    name=self.collection_name
                )
                logger.info(f"Retrieved existing enhanced collection: {self.collection_name}")
            except Exception:
                self.legal_collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={
                        "description": "Enhanced legal documents with advanced metadata",
                        "version": "2.0",
                        "created_at": datetime.utcnow().isoformat()
                    }
                )
                logger.info(f"Created new enhanced collection: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.chroma_client = None
            self.legal_collection = None
    
    async def _initialize_embedding_models(self):
        """Initialize embedding models"""
        if not HAS_SENTENCE_TRANSFORMERS:
            logger.warning("Sentence transformers not available, using fallback embeddings")
            return
            
        try:
            # Load sentence transformer model
            model_name = getattr(settings, 'EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None
    
    async def _initialize_bedrock(self):
        """Initialize AWS Bedrock for embeddings"""
        if not HAS_BOTO3:
            logger.warning("Boto3 not available, AWS Bedrock embeddings disabled")
            return
            
        try:
            # Initialize Bedrock client
            self.bedrock_client = boto3.client(
                'bedrock-runtime',
                region_name=getattr(settings, 'AWS_REGION', 'us-east-1')
            )
            logger.info("AWS Bedrock client initialized for embeddings")
            
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            self.bedrock_client = None

    async def query_with_sources(self, query: str, max_sources: int = 5, strategy: str = "hybrid") -> RAGResponse:
        """Enhanced query with comprehensive source tracking and confidence scoring"""
        start_time = datetime.utcnow()
        
        if not self._initialized:
            await self.initialize()
        
        try:
            self.metrics["total_queries"] += 1
            
            # Retrieve relevant documents
            retrieved_docs = await self._retrieve_documents(query, max_sources * 2, strategy)
            
            if not retrieved_docs:
                return RAGResponse(
                    response_text="I couldn't find relevant legal documents to answer your question.",
                    confidence_score=0.0,
                    sources=[],
                    retrieval_strategy=strategy,
                    total_documents_searched=0
                )
            
            # Generate response with context
            response_data = await self._generate_response_with_context(query, retrieved_docs)
            
            # Create legal sources with citations
            sources = self._create_legal_sources(retrieved_docs[:max_sources])
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update metrics
            self.metrics["successful_retrievals"] += 1
            self._update_avg_response_time(processing_time)
            
            return RAGResponse(
                response_text=response_data["response"],
                confidence_score=response_data["confidence"],
                sources=sources,
                model_used=response_data.get("model_used", "unknown"),
                retrieval_strategy=strategy,
                processing_time_ms=processing_time,
                total_documents_searched=len(retrieved_docs),
                timestamp=start_time
            )
            
        except Exception as e:
            logger.error(f"Error in query_with_sources: {e}")
            return RAGResponse(
                response_text=f"An error occurred while processing your query: {str(e)}",
                confidence_score=0.0,
                sources=[],
                retrieval_strategy=strategy,
                total_documents_searched=0
            )

    async def _retrieve_documents(self, query: str, limit: int, strategy: str) -> List[Dict[str, Any]]:
        """Retrieve documents using specified strategy"""
        try:
            if strategy == "semantic" and self.legal_collection:
                return await self._semantic_retrieval(query, limit)
            elif strategy == "hybrid":
                return await self._hybrid_retrieval(query, limit)
            else:
                # Fallback to existing vector service
                return await self._fallback_retrieval(query, limit)
                
        except Exception as e:
            logger.error(f"Error in document retrieval: {e}")
            return []

    async def _semantic_retrieval(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Semantic retrieval using ChromaDB"""
        if not self.legal_collection:
            return []
            
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            if not query_embedding:
                return []
            
            # Query ChromaDB
            results = self.legal_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert to standard format
            documents = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0], 
                results["distances"][0]
            )):
                documents.append({
                    "content": doc,
                    "metadata": metadata,
                    "relevance_score": 1.0 - distance,  # Convert distance to similarity
                    "rank": i + 1
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error in semantic retrieval: {e}")
            return []

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using available models"""
        try:
            # Use sentence transformers (more reliable than Bedrock embeddings)
            if self.embedding_model:
                embedding = self.embedding_model.encode(text)
                return embedding.tolist()

            # Fallback: create simple hash-based embedding for testing
            import hashlib
            text_hash = hashlib.md5(text.encode()).hexdigest()
            # Convert hash to 384-dimensional vector
            embedding = [float(int(text_hash[i:i+2], 16)) / 255.0 for i in range(0, min(len(text_hash), 48), 2)]
            # Pad to 384 dimensions
            while len(embedding) < 384:
                embedding.extend(embedding[:min(384-len(embedding), len(embedding))])
            return embedding[:384]

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

# Removed Bedrock Titan embedding - using sentence-transformers instead for reliability

    async def _hybrid_retrieval(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Hybrid retrieval combining semantic and keyword search"""
        try:
            # Get semantic results
            semantic_docs = await self._semantic_retrieval(query, limit)

            # Get keyword results from existing vector service
            keyword_docs = await self._fallback_retrieval(query, limit)

            # Merge and deduplicate results
            merged_docs = {}

            # Add semantic results with higher weight
            for doc in semantic_docs:
                doc_id = self._get_document_id(doc)
                doc["relevance_score"] *= 0.7  # Weight semantic results
                doc["retrieval_method"] = "semantic"
                merged_docs[doc_id] = doc

            # Add keyword results with lower weight
            for doc in keyword_docs:
                doc_id = self._get_document_id(doc)
                if doc_id in merged_docs:
                    # Combine scores
                    merged_docs[doc_id]["relevance_score"] = (
                        merged_docs[doc_id]["relevance_score"] + doc.get("relevance_score", 0.5) * 0.3
                    )
                    merged_docs[doc_id]["retrieval_method"] = "hybrid"
                else:
                    doc["relevance_score"] = doc.get("relevance_score", 0.5) * 0.3
                    doc["retrieval_method"] = "keyword"
                    merged_docs[doc_id] = doc

            # Sort by relevance score and return top results
            sorted_docs = sorted(
                merged_docs.values(),
                key=lambda x: x.get("relevance_score", 0),
                reverse=True
            )

            return sorted_docs[:limit]

        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}")
            return await self._fallback_retrieval(query, limit)

    async def _fallback_retrieval(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Fallback retrieval using existing vector service"""
        try:
            # Use existing vector service
            results = await self.vector_service.search_similar_documents(query, limit)

            # Convert to standard format
            documents = []
            for i, doc in enumerate(results):
                documents.append({
                    "content": doc.content if hasattr(doc, 'content') else "",
                    "metadata": {
                        "title": doc.title if hasattr(doc, 'title') else "",
                        "source": doc.source if hasattr(doc, 'source') else "",
                        "url": doc.url if hasattr(doc, 'url') else "",
                        "document_type": doc.document_type if hasattr(doc, 'document_type') else "",
                        "category": doc.category if hasattr(doc, 'category') else ""
                    },
                    "relevance_score": getattr(doc, 'relevance_score', 0.5),
                    "rank": i + 1
                })

            return documents

        except Exception as e:
            logger.error(f"Error in fallback retrieval: {e}")
            return []

    def _get_document_id(self, doc: Dict[str, Any]) -> str:
        """Generate unique document ID for deduplication"""
        metadata = doc.get("metadata", {})
        title = metadata.get("title", "")
        url = metadata.get("url", "")

        if url:
            return f"url_{hash(url)}"
        elif title:
            return f"title_{hash(title)}"
        else:
            return f"content_{hash(doc.get('content', '')[:100])}"

    async def _generate_response_with_context(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate response using retrieved documents as context"""
        try:
            # Prepare context from retrieved documents
            context_parts = []
            for i, doc in enumerate(documents[:self.max_sources]):
                metadata = doc.get("metadata", {})
                title = metadata.get("title", f"Document {i+1}")
                source = metadata.get("source", "Unknown")
                content = doc.get("content", "")[:800]  # Limit content length

                context_parts.append(f"[Source {i+1}: {title} - {source}]\n{content}\n")

            context = "\n".join(context_parts)

            # Create enhanced prompt for legal queries
            prompt = self._create_legal_prompt(query, context)

            # Generate response using AI service
            response_data = await self.ai_service._generate_with_fallback(prompt, "legal_query")

            # Calculate confidence based on source quality and response coherence
            confidence = self._calculate_confidence(documents, response_data.get("response", ""))

            return {
                "response": response_data.get("response", ""),
                "confidence": confidence,
                "model_used": response_data.get("model_used", "unknown")
            }

        except Exception as e:
            logger.error(f"Error generating response with context: {e}")
            return {
                "response": "I encountered an error while generating the response.",
                "confidence": 0.0,
                "model_used": "error"
            }

    def _create_legal_prompt(self, query: str, context: str) -> str:
        """Create specialized prompt for legal queries"""
        return f"""You are an expert legal AI assistant specializing in Kenyan law. Use the provided legal documents to answer the user's question accurately and comprehensively.

LEGAL CONTEXT:
{context}

USER QUESTION: {query}

INSTRUCTIONS:
1. Base your answer primarily on the provided legal documents
2. Cite specific sources when making legal statements
3. If the documents don't contain sufficient information, clearly state this
4. Provide practical guidance while noting that this is not legal advice
5. Use clear, professional language appropriate for legal matters
6. Include relevant legal principles and precedents from the sources

RESPONSE:"""

    def _calculate_confidence(self, documents: List[Dict[str, Any]], response: str) -> float:
        """Calculate confidence score based on source quality and response coherence"""
        try:
            if not documents or not response:
                return 0.0

            # Base confidence on document relevance scores
            avg_relevance = sum(doc.get("relevance_score", 0) for doc in documents) / len(documents)

            # Adjust based on number of sources
            source_factor = min(len(documents) / self.max_sources, 1.0)

            # Adjust based on response length (longer responses generally more comprehensive)
            length_factor = min(len(response) / 500, 1.0)

            # Check for legal citations in response
            citation_factor = 1.0
            if any(keyword in response.lower() for keyword in ["section", "article", "act", "case", "court"]):
                citation_factor = 1.2

            confidence = (avg_relevance * 0.5 + source_factor * 0.3 + length_factor * 0.2) * citation_factor

            return min(confidence, 1.0)

        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5

    def _create_legal_sources(self, documents: List[Dict[str, Any]]) -> List[LegalSource]:
        """Create legal sources with proper citations"""
        sources = []

        for doc in documents:
            metadata = doc.get("metadata", {})

            # Create citation
            citation = self._generate_citation(metadata)

            # Extract relevant excerpt
            excerpt = self._extract_relevant_excerpt(doc.get("content", ""))

            source = LegalSource(
                title=metadata.get("title", "Unknown Document"),
                source=metadata.get("source", "Unknown"),
                url=metadata.get("url"),
                document_type=metadata.get("document_type", "unknown"),
                relevance_score=doc.get("relevance_score", 0.0),
                excerpt=excerpt,
                metadata=metadata,
                citation=citation
            )

            sources.append(source)

        return sources

    def _generate_citation(self, metadata: Dict[str, Any]) -> str:
        """Generate proper legal citation"""
        try:
            title = metadata.get("title", "")
            source = metadata.get("source", "")
            document_type = metadata.get("document_type", "")
            url = metadata.get("url", "")

            # Generate citation based on document type
            if document_type == "legislation":
                # Extract act information
                act_match = re.search(r'(\w+\s+Act)\s*(\d+)?\s*of\s*(\d{4})', title, re.IGNORECASE)
                if act_match:
                    return f"{act_match.group(1)} {act_match.group(2) or ''} of {act_match.group(3)}"
                else:
                    return f"{title} (Kenya Law)"

            elif document_type == "judgment":
                # Extract case information
                case_match = re.search(r'([A-Z][^v]+)\s+v\.?\s+([A-Z][^,\n]+)', title)
                if case_match:
                    return f"{case_match.group(1).strip()} v. {case_match.group(2).strip()}"
                else:
                    return f"{title} (Kenya Law)"

            elif document_type == "constitution":
                return "Constitution of Kenya, 2010"

            else:
                return f"{title} ({source})"

        except Exception as e:
            logger.error(f"Error generating citation: {e}")
            return metadata.get("title", "Unknown Document")

    def _extract_relevant_excerpt(self, content: str, max_length: int = 300) -> str:
        """Extract relevant excerpt from document content"""
        try:
            if not content:
                return ""

            # Clean content
            content = re.sub(r'\s+', ' ', content).strip()

            # If content is short enough, return as is
            if len(content) <= max_length:
                return content

            # Try to find a good breaking point (sentence end)
            excerpt = content[:max_length]
            last_period = excerpt.rfind('.')
            last_semicolon = excerpt.rfind(';')

            break_point = max(last_period, last_semicolon)
            if break_point > max_length * 0.7:  # If break point is reasonably close to end
                excerpt = content[:break_point + 1]
            else:
                excerpt = content[:max_length] + "..."

            return excerpt

        except Exception as e:
            logger.error(f"Error extracting excerpt: {e}")
            return content[:max_length] + "..." if len(content) > max_length else content

    def _update_avg_response_time(self, response_time: float):
        """Update average response time metric"""
        current_avg = self.metrics["avg_response_time"]
        total_queries = self.metrics["total_queries"]

        if total_queries == 1:
            self.metrics["avg_response_time"] = response_time
        else:
            self.metrics["avg_response_time"] = (
                (current_avg * (total_queries - 1) + response_time) / total_queries
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful_retrievals"] / self.metrics["total_queries"]
                if self.metrics["total_queries"] > 0 else 0.0
            ),
            "initialized": self._initialized,
            "has_chromadb": self.legal_collection is not None,
            "has_embedding_model": self.embedding_model is not None,
            "has_bedrock": self.bedrock_client is not None
        }

    async def ingest_document(self, document: Document) -> bool:
        """Ingest a document into the enhanced RAG system"""
        if not self._initialized:
            await self.initialize()

        try:
            # Chunk the document
            chunks = self._chunk_document(document.content)

            # Generate embeddings for chunks
            embeddings = []
            for chunk in chunks:
                embedding = await self._generate_embedding(chunk)
                if embedding:
                    embeddings.append(embedding)
                else:
                    # Fallback to zero vector if embedding fails
                    embeddings.append([0.0] * 384)  # Default dimension

            if not embeddings:
                logger.error(f"Failed to generate embeddings for document {document.id}")
                return False

            # Prepare metadata for each chunk
            base_metadata = {
                "document_id": document.id,
                "title": document.title,
                "source": document.source,
                "document_type": document.document_type,
                "url": document.url or "",
                "category": document.category or "",
                "jurisdiction": document.jurisdiction or "kenya",
                "created_at": document.created_at.isoformat() if document.created_at else "",
                "word_count": document.word_count or 0
            }

            # Add chunks to ChromaDB
            if self.legal_collection:
                chunk_ids = [f"doc_{document.id}_chunk_{i}" for i in range(len(chunks))]
                chunk_metadatas = []

                for i, chunk in enumerate(chunks):
                    chunk_metadata = base_metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": i,
                        "chunk_text": chunk[:200] + "..." if len(chunk) > 200 else chunk,
                        "chunk_size": len(chunk)
                    })
                    chunk_metadatas.append(chunk_metadata)

                self.legal_collection.add(
                    documents=chunks,
                    embeddings=embeddings,
                    metadatas=chunk_metadatas,
                    ids=chunk_ids
                )

                logger.info(f"Added {len(chunks)} chunks for document {document.id} to enhanced collection")

            # Also add to existing vector service for fallback
            await self.vector_service.add_document(document)

            return True

        except Exception as e:
            logger.error(f"Error ingesting document {document.id}: {e}")
            return False

    def _chunk_document(self, content: str) -> List[str]:
        """Chunk document content for better retrieval"""
        try:
            if not content:
                return []

            # Clean content
            content = re.sub(r'\s+', ' ', content).strip()

            # If content is smaller than chunk size, return as single chunk
            if len(content) <= self.chunk_size:
                return [content]

            chunks = []
            start = 0

            while start < len(content):
                end = start + self.chunk_size

                # If this is not the last chunk, try to break at sentence boundary
                if end < len(content):
                    # Look for sentence endings within overlap distance
                    search_start = max(start + self.chunk_size - self.chunk_overlap, start)
                    search_end = min(end + self.chunk_overlap, len(content))

                    # Find the best break point
                    break_points = []
                    for i in range(search_start, search_end):
                        if content[i] in '.!?':
                            break_points.append(i + 1)

                    if break_points:
                        # Choose break point closest to target end
                        end = min(break_points, key=lambda x: abs(x - end))

                chunk = content[start:end].strip()
                if chunk:
                    chunks.append(chunk)

                # Move start position with overlap
                start = max(end - self.chunk_overlap, start + 1)

                # Prevent infinite loop
                if start >= len(content):
                    break

            return chunks

        except Exception as e:
            logger.error(f"Error chunking document: {e}")
            return [content]  # Return original content as fallback

    async def ingest_corpus_from_directory(self, corpus_dir: str) -> Dict[str, Any]:
        """Ingest legal corpus from directory"""
        corpus_path = Path(corpus_dir)
        if not corpus_path.exists():
            logger.error(f"Corpus directory does not exist: {corpus_dir}")
            return {"success": False, "error": "Directory not found"}

        results = {
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "total_documents": 0,
            "errors": []
        }

        try:
            # Process all text files in directory
            for file_path in corpus_path.rglob("*.txt"):
                results["total_files"] += 1

                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    if not content.strip():
                        continue

                    # Create document metadata from filename and path
                    relative_path = file_path.relative_to(corpus_path)
                    document_type = self._infer_document_type(file_path.name)

                    # Create temporary document object
                    temp_doc = type('Document', (), {
                        'id': abs(hash(str(file_path))),  # Use positive integer ID
                        'title': file_path.stem.replace('_', ' ').title(),
                        'content': content,
                        'source': 'legal_corpus',
                        'document_type': document_type,
                        'url': None,
                        'category': str(relative_path.parent) if relative_path.parent != Path('.') else 'general',
                        'jurisdiction': 'kenya',
                        'created_at': datetime.utcnow(),
                        'word_count': len(content.split()),
                        'tags': [],
                        'subcategory': None,
                        'language': 'en',
                        'readability_score': None,
                        'embedding': None,
                        'embedding_model': None,
                        'is_processed': False,
                        'is_indexed': False,
                        'processing_status': 'pending',
                        'error_message': None,
                        'updated_at': None,
                        'last_indexed': None,
                        'relevance_score': None
                    })()

                    # Ingest document
                    success = await self.ingest_document(temp_doc)
                    if success:
                        results["processed_files"] += 1
                        results["total_documents"] += 1
                    else:
                        results["failed_files"] += 1
                        results["errors"].append(f"Failed to ingest {file_path.name}")

                except Exception as e:
                    results["failed_files"] += 1
                    results["errors"].append(f"Error processing {file_path.name}: {str(e)}")
                    logger.error(f"Error processing file {file_path}: {e}")

            results["success"] = True
            logger.info(f"Corpus ingestion completed: {results}")
            return results

        except Exception as e:
            logger.error(f"Error ingesting corpus: {e}")
            results["success"] = False
            results["error"] = str(e)
            return results

    def _infer_document_type(self, filename: str) -> str:
        """Infer document type from filename"""
        filename_lower = filename.lower()

        if any(keyword in filename_lower for keyword in ['constitution', 'constitutional']):
            return 'constitution'
        elif any(keyword in filename_lower for keyword in ['act', 'statute', 'law']):
            return 'legislation'
        elif any(keyword in filename_lower for keyword in ['case', 'judgment', 'ruling']):
            return 'judgment'
        elif any(keyword in filename_lower for keyword in ['gazette', 'notice']):
            return 'gazette'
        elif any(keyword in filename_lower for keyword in ['regulation', 'rule']):
            return 'regulation'
        else:
            return 'legal_document'

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the document collection"""
        try:
            stats = {
                "total_documents": 0,
                "total_chunks": 0,
                "document_types": {},
                "sources": {},
                "collection_exists": False
            }

            if self.legal_collection:
                # Get collection info
                collection_info = self.legal_collection.get()
                stats["total_chunks"] = len(collection_info["ids"])
                stats["collection_exists"] = True

                # Analyze metadata
                for metadata in collection_info["metadatas"]:
                    # Count document types
                    doc_type = metadata.get("document_type", "unknown")
                    stats["document_types"][doc_type] = stats["document_types"].get(doc_type, 0) + 1

                    # Count sources
                    source = metadata.get("source", "unknown")
                    stats["sources"][source] = stats["sources"].get(source, 0) + 1

                # Count unique documents
                unique_doc_ids = set()
                for metadata in collection_info["metadatas"]:
                    doc_id = metadata.get("document_id")
                    if doc_id:
                        unique_doc_ids.add(doc_id)

                stats["total_documents"] = len(unique_doc_ids)

            return stats

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e), "collection_exists": False}
