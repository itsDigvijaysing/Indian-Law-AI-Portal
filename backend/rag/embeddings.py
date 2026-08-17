"""
Embedding Generation Module

Handles text-to-vector conversion using various embedding models.
"""

import numpy as np
from typing import List, Dict
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
                result = genai.embed_content(
                    model=f"models/{self.model_name}",
                    content=text,
                    task_type="retrieval_document"
                )
                return np.array(result['embedding'])

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return np.zeros(384)  # default dimension for the local ST models
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """Generate embeddings for multiple texts efficiently"""
        embeddings = []
        
        try:
            if self.model_type == "sentence-transformers":
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    batch_embeddings = self.model.encode(batch, convert_to_numpy=True)
                    embeddings.extend(batch_embeddings)

                logger.info(f"Generated {len(embeddings)} embeddings in batches")

            elif self.model_type == "google":
                # One at a time: the hosted API rate-limits batched calls hard.
                for text in texts:
                    embedding = self.generate_embedding(text)
                    embeddings.append(embedding)

                logger.info(f"Generated {len(embeddings)} embeddings via Google API")

        except Exception as e:
            logger.error(f"Error in batch embedding generation: {e}")
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
        logger.info("DocumentEmbedder initialized")
    
    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Add embeddings to document chunks"""
        if not chunks:
            return chunks

        texts = [chunk['text'] for chunk in chunks]

        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_generator.generate_embeddings_batch(texts)

        enriched_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            enriched_chunk = chunk.copy()
            enriched_chunk['embedding'] = embedding
            enriched_chunk['embedding_model'] = self.embedding_generator.model_name
            enriched_chunks.append(enriched_chunk)
        
        logger.info(f"Successfully added embeddings to {len(enriched_chunks)} chunks")
        return enriched_chunks