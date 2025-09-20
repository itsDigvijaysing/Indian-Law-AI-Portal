"""
Vector Database Module

Handles storage and retrieval of document embeddings using FAISS.
"""

import os
import pickle
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
import faiss
from loguru import logger


class VectorDatabase:
    """FAISS-based vector database for storing and retrieving document embeddings"""
    
    def __init__(self, dimension: int, index_type: str = "flat"):
        self.dimension = dimension
        self.index_type = index_type
        self.index = None
        self.chunks = []  # Store original chunk data
        self.metadata = []  # Store chunk metadata
        self._initialize_index()
        logger.info(f"VectorDatabase initialized with dimension={dimension}, type={index_type}")
    
    def _initialize_index(self):
        """Initialize FAISS index"""
        try:
            if self.index_type == "flat":
                # L2 distance (Euclidean)
                self.index = faiss.IndexFlatL2(self.dimension)
            elif self.index_type == "ivf":
                # Inverted file index for larger datasets
                nlist = 100  # number of clusters
                quantizer = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            elif self.index_type == "hnsw":
                # Hierarchical Navigable Small World for fast similarity search
                self.index = faiss.IndexHNSWFlat(self.dimension, 32)
            else:
                # Default to flat index
                self.index = faiss.IndexFlatL2(self.dimension)
                
            logger.info(f"FAISS index initialized: {self.index_type}")
            
        except Exception as e:
            logger.error(f"Error initializing FAISS index: {e}")
            # Fallback to simple flat index
            self.index = faiss.IndexFlatL2(self.dimension)
    
    def add_documents(self, chunks: List[Dict]):
        """Add document chunks with embeddings to the vector database"""
        if not chunks:
            logger.warning("No chunks provided to add to vector database")
            return
        
        try:
            # Extract embeddings and metadata
            embeddings = []
            metadata = []
            
            for chunk in chunks:
                if 'embedding' not in chunk:
                    logger.warning(f"Chunk missing embedding: {chunk.get('chunk_id', 'unknown')}")
                    continue
                
                embedding = chunk['embedding']
                if isinstance(embedding, list):
                    embedding = np.array(embedding)
                
                embeddings.append(embedding)
                metadata.append({
                    'chunk_id': chunk.get('chunk_id', ''),
                    'document': chunk.get('document', ''),
                    'section': chunk.get('section', ''),
                    'text': chunk.get('text', ''),
                    'word_count': chunk.get('word_count', 0),
                    'char_count': chunk.get('char_count', 0)
                })
            
            if not embeddings:
                logger.warning("No valid embeddings found in chunks")
                return
            
            # Convert to numpy array
            embeddings_array = np.vstack(embeddings).astype('float32')
            
            # Train index if needed (for IVF)
            if self.index_type == "ivf" and not self.index.is_trained:
                logger.info("Training IVF index...")
                self.index.train(embeddings_array)
            
            # Add to index
            start_id = len(self.chunks)
            self.index.add(embeddings_array)
            
            # Store chunks and metadata
            self.chunks.extend(chunks)
            self.metadata.extend(metadata)
            
            logger.info(f"Added {len(embeddings)} documents to vector database. Total: {self.index.ntotal}")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}")
    
    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Dict]:
        """Search for similar documents using query embedding"""
        try:
            if self.index.ntotal == 0:
                logger.warning("Vector database is empty")
                return []
            
            # Ensure query embedding is the right shape and type
            if isinstance(query_embedding, list):
                query_embedding = np.array(query_embedding)
            
            query_embedding = query_embedding.astype('float32').reshape(1, -1)
            
            # Search
            distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
            
            # Prepare results
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.metadata):
                    result = self.metadata[idx].copy()
                    result['similarity_score'] = float(1 / (1 + distance))  # Convert distance to similarity
                    result['rank'] = i + 1
                    results.append(result)
            
            logger.info(f"Found {len(results)} similar documents")
            return results
            
        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            return []
    
    def get_document_count(self) -> int:
        """Get total number of documents in the database"""
        return self.index.ntotal if self.index else 0
    
    def save_index(self, filepath: str):
        """Save the vector index and metadata to disk"""
        try:
            # Save FAISS index
            index_path = f"{filepath}.index"
            faiss.write_index(self.index, index_path)
            
            # Save metadata and chunks
            metadata_path = f"{filepath}.metadata"
            with open(metadata_path, 'wb') as f:
                pickle.dump({
                    'chunks': self.chunks,
                    'metadata': self.metadata,
                    'dimension': self.dimension,
                    'index_type': self.index_type
                }, f)
            
            logger.info(f"Saved vector database to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving vector database: {e}")
    
    def load_index(self, filepath: str) -> bool:
        """Load vector index and metadata from disk"""
        try:
            # Load FAISS index
            index_path = f"{filepath}.index"
            if os.path.exists(index_path):
                self.index = faiss.read_index(index_path)
            else:
                logger.error(f"Index file not found: {index_path}")
                return False
            
            # Load metadata and chunks
            metadata_path = f"{filepath}.metadata"
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    data = pickle.load(f)
                    self.chunks = data['chunks']
                    self.metadata = data['metadata']
                    self.dimension = data['dimension']
                    self.index_type = data['index_type']
            else:
                logger.error(f"Metadata file not found: {metadata_path}")
                return False
            
            logger.info(f"Loaded vector database from {filepath}. Documents: {self.index.ntotal}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading vector database: {e}")
            return False
    
    def clear(self):
        """Clear all data from the vector database"""
        self._initialize_index()
        self.chunks = []
        self.metadata = []
        logger.info("Vector database cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the vector database"""
        if not self.index:
            return {}
        
        doc_types = {}
        total_chars = 0
        total_words = 0
        
        for metadata in self.metadata:
            doc_type = metadata.get('document', 'unknown')
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            total_chars += metadata.get('char_count', 0)
            total_words += metadata.get('word_count', 0)
        
        return {
            'total_documents': self.index.ntotal,
            'dimension': self.dimension,
            'index_type': self.index_type,
            'document_types': doc_types,
            'total_characters': total_chars,
            'total_words': total_words,
            'average_chars_per_chunk': total_chars / max(1, self.index.ntotal),
            'average_words_per_chunk': total_words / max(1, self.index.ntotal)
        }


class HybridRetriever:
    """Enhanced retriever that combines vector search with keyword matching"""
    
    def __init__(self, vector_db: VectorDatabase):
        self.vector_db = vector_db
        logger.info("HybridRetriever initialized")
    
    def retrieve(self, query_embedding: np.ndarray, query_text: str, top_k: int = 10) -> List[Dict]:
        """Retrieve relevant documents using hybrid approach"""
        try:
            # Get vector search results
            vector_results = self.vector_db.search(query_embedding, top_k * 2)  # Get more for filtering
            
            # Apply keyword boosting
            boosted_results = self._apply_keyword_boosting(vector_results, query_text)
            
            # Re-rank and return top_k
            final_results = sorted(boosted_results, key=lambda x: x['final_score'], reverse=True)[:top_k]
            
            logger.info(f"HybridRetriever returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}")
            return self.vector_db.search(query_embedding, top_k)  # Fallback to vector search
    
    def _apply_keyword_boosting(self, results: List[Dict], query_text: str) -> List[Dict]:
        """Apply keyword-based boosting to vector search results"""
        query_words = set(query_text.lower().split())
        
        for result in results:
            text = result.get('text', '').lower()
            text_words = set(text.split())
            
            # Calculate keyword overlap
            overlap = len(query_words.intersection(text_words))
            overlap_ratio = overlap / len(query_words) if query_words else 0
            
            # Boost similarity score based on keyword overlap
            vector_score = result.get('similarity_score', 0)
            keyword_boost = overlap_ratio * 0.3  # 30% boost maximum
            result['final_score'] = vector_score + keyword_boost
            result['keyword_overlap'] = overlap
            result['keyword_boost'] = keyword_boost
        
        return results