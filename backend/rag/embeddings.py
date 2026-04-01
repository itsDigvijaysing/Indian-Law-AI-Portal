"""
Embedding Generation Module

Handles text-to-vector conversion using various embedding models.
"""

import os
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from loguru import logger

# Import settings to ensure .env is loaded
try:
    from api.core.config import get_settings
except ImportError:
    from backend.api.core.config import get_settings


class EmbeddingGenerator:
    """Generates embeddings for text chunks using various models"""
    
    def __init__(self, model_type: str = "sentence-transformers", model_name: str = "all-MiniLM-L6-v2"):
        self.model_type = model_type
        self.model_name = model_name
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the embedding model"""
        try:
            if self.model_type == "sentence-transformers":
                self.model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded SentenceTransformer model: {self.model_name}")
            
            elif self.model_type == "google":
                # Get API key from settings (properly loads .env)
                settings = get_settings()
                api_key = settings.GOOGLE_API_KEY
                
                if api_key and api_key != "your_google_api_key_here":
                    genai.configure(api_key=api_key)
                    logger.info(f"Configured Google AI for embeddings: {self.model_name}")
                else:
                    logger.warning("GOOGLE_API_KEY not configured, falling back to sentence-transformers")
                    self.model_type = "sentence-transformers"
                    self.model = SentenceTransformer("all-MiniLM-L6-v2")
            
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
                
        except Exception as e:
            logger.error(f"Error initializing embedding model: {e}")
            # Fallback to a simple model
            self.model_type = "sentence-transformers"
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Fallback to all-MiniLM-L6-v2 model")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        try:
            if self.model_type == "sentence-transformers":
                embedding = self.model.encode(text, convert_to_numpy=True)
                return embedding
            
            elif self.model_type == "google":
                # Use Google's embedding API
                result = genai.embed_content(
                    model=f"models/{self.model_name}",
                    content=text,
                    task_type="retrieval_document"
                )
                return np.array(result['embedding'])
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return np.zeros(384)  # Default dimension for many models
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """Generate embeddings for multiple texts efficiently"""
        embeddings = []
        
        try:
            if self.model_type == "sentence-transformers":
                # Process in batches for efficiency
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    batch_embeddings = self.model.encode(batch, convert_to_numpy=True)
                    embeddings.extend(batch_embeddings)
                
                logger.info(f"Generated {len(embeddings)} embeddings in batches")
            
            elif self.model_type == "google":
                # Google API - process individually (rate limiting)
                for text in texts:
                    embedding = self.generate_embedding(text)
                    embeddings.append(embedding)
                
                logger.info(f"Generated {len(embeddings)} embeddings via Google API")
            
        except Exception as e:
            logger.error(f"Error in batch embedding generation: {e}")
            # Fallback to individual processing
            for text in texts:
                embedding = self.generate_embedding(text)
                embeddings.append(embedding)
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        try:
            if self.model_type == "sentence-transformers":
                return self.model.get_sentence_embedding_dimension()
            elif self.model_type == "google":
                return 768  # Google embedding models return 768 dimensions
        except Exception as e:
            logger.error(f"Error getting embedding dimension: {e}")
            return 384  # Safe fallback


class DocumentEmbedder:
    """Handles embedding generation for processed document chunks"""
    
    def __init__(self, embedding_generator: EmbeddingGenerator):
        self.embedding_generator = embedding_generator
        self.embeddings_cache = {}
        logger.info("DocumentEmbedder initialized")
    
    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Add embeddings to document chunks"""
        if not chunks:
            return chunks
        
        # Extract texts for embedding
        texts = [chunk['text'] for chunk in chunks]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_generator.generate_embeddings_batch(texts)
        
        # Add embeddings to chunks
        enriched_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            enriched_chunk = chunk.copy()
            enriched_chunk['embedding'] = embedding
            enriched_chunk['embedding_model'] = self.embedding_generator.model_name
            enriched_chunks.append(enriched_chunk)
        
        logger.info(f"Successfully added embeddings to {len(enriched_chunks)} chunks")
        return enriched_chunks
    
    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a search query"""
        return self.embedding_generator.generate_embedding(query)
    
    def save_embeddings(self, chunks: List[Dict], filepath: str):
        """Save chunks with embeddings to file"""
        try:
            # Convert numpy arrays to lists for JSON serialization
            serializable_chunks = []
            for chunk in chunks:
                serializable_chunk = chunk.copy()
                if 'embedding' in serializable_chunk:
                    serializable_chunk['embedding'] = serializable_chunk['embedding'].tolist()
                serializable_chunks.append(serializable_chunk)
            
            import json
            with open(filepath, 'w') as f:
                json.dump(serializable_chunks, f, indent=2)
            
            logger.info(f"Saved {len(chunks)} chunks with embeddings to {filepath}")
        
        except Exception as e:
            logger.error(f"Error saving embeddings: {e}")
    
    def load_embeddings(self, filepath: str) -> List[Dict]:
        """Load chunks with embeddings from file"""
        try:
            import json
            with open(filepath, 'r') as f:
                chunks = json.load(f)
            
            # Convert embedding lists back to numpy arrays
            for chunk in chunks:
                if 'embedding' in chunk:
                    chunk['embedding'] = np.array(chunk['embedding'])
            
            logger.info(f"Loaded {len(chunks)} chunks with embeddings from {filepath}")
            return chunks
        
        except Exception as e:
            logger.error(f"Error loading embeddings: {e}")
            return []


class EmbeddingConfig:
    """Configuration class for embedding models and parameters"""
    
    # Available embedding models
    SENTENCE_TRANSFORMER_MODELS = {
        "all-MiniLM-L6-v2": {"dim": 384, "description": "Fast, lightweight model"},
        "all-mpnet-base-v2": {"dim": 768, "description": "High quality, slower"},
        "multi-qa-MiniLM-L6-cos-v1": {"dim": 384, "description": "Optimized for QA"},
        "paraphrase-multilingual-MiniLM-L12-v2": {"dim": 384, "description": "Multilingual support"}
    }
    
    GOOGLE_MODELS = {
        "text-embedding-004": {"dim": 768, "description": "Latest Google embedding model"},
        "textembedding-gecko": {"dim": 768, "description": "Google's Gecko model"}
    }
    
    @classmethod
    def get_recommended_model(cls, use_case: str = "legal") -> tuple:
        """Get recommended model for specific use case"""
        if use_case == "legal":
            # For legal documents, prefer higher quality models
            return ("sentence-transformers", "all-mpnet-base-v2")
        elif use_case == "fast":
            # For fast processing
            return ("sentence-transformers", "all-MiniLM-L6-v2")
        elif use_case == "multilingual":
            # For multilingual support
            return ("sentence-transformers", "paraphrase-multilingual-MiniLM-L12-v2")
        else:
            return ("sentence-transformers", "all-MiniLM-L6-v2")
    
    @classmethod
    def get_model_info(cls, model_type: str, model_name: str) -> Dict:
        """Get information about a specific model"""
        if model_type == "sentence-transformers":
            return cls.SENTENCE_TRANSFORMER_MODELS.get(model_name, {})
        elif model_type == "google":
            return cls.GOOGLE_MODELS.get(model_name, {})
        else:
            return {}