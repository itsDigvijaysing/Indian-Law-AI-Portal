"""
Vector Database Module

Handles storage and retrieval of document embeddings using FAISS.
"""

import os
import re
import pickle
import numpy as np
from typing import List, Dict, Any
import faiss
from rank_bm25 import BM25Okapi
from loguru import logger

try:
    from .document_registry import get_doc_meta, norm_doc_key as _norm_doc
except ImportError:
    from document_registry import get_doc_meta, norm_doc_key as _norm_doc

_TOKEN_RE = re.compile(r'\w+')


class VectorDatabase:
    """FAISS-based vector database for storing and retrieving document embeddings"""
    
    METADATA_VERSION = 2

    def __init__(self, dimension: int, index_type: str = "flat", embedding_model: str = ""):
        self.dimension = dimension
        self.index_type = index_type
        self.embedding_model = embedding_model
        self.index = None
        self.chunks = []  # Store original chunk data
        self.metadata = []  # Store chunk metadata
        self._bm25 = None  # Keyword index over metadata texts, rebuilt on add/load
        self._initialize_index()
        logger.info(f"VectorDatabase initialized with dimension={dimension}, type={index_type}")
    
    def _initialize_index(self):
        """Initialize FAISS index (flat L2; ivf/hnsw kept for larger corpora)"""
        try:
            if self.index_type == "flat":
                self.index = faiss.IndexFlatL2(self.dimension)
            elif self.index_type == "ivf":
                nlist = 100  # cluster count
                quantizer = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            elif self.index_type == "hnsw":
                self.index = faiss.IndexHNSWFlat(self.dimension, 32)
            else:
                self.index = faiss.IndexFlatL2(self.dimension)

            logger.info(f"FAISS index initialized: {self.index_type}")

        except Exception as e:
            logger.error(f"Error initializing FAISS index: {e}")
            self.index = faiss.IndexFlatL2(self.dimension)

    def add_documents(self, chunks: List[Dict]):
        """Add document chunks with embeddings to the vector database"""
        if not chunks:
            logger.warning("No chunks provided to add to vector database")
            return

        try:
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
                # Legal-hierarchy metadata (category / era / law_type / area)
                # from the registry, keyed by document stem.
                reg = get_doc_meta(chunk.get('document', ''))
                metadata.append({
                    'chunk_id': chunk.get('chunk_id', ''),
                    'document': chunk.get('document', ''),
                    'document_title': chunk.get('document_title', ''),
                    'section': chunk.get('section', ''),
                    'part': chunk.get('part', 1),
                    'legal_sections': chunk.get('legal_sections', []),
                    'page_start': chunk.get('page_start', 0),
                    'page_end': chunk.get('page_end', 0),
                    'category': reg.get('category', 'General'),
                    'era': reg.get('era', 'current'),
                    'law_type': reg.get('law_type', ''),
                    'law_area': reg.get('law_area', ''),
                    'text': chunk.get('text', ''),
                    'word_count': chunk.get('word_count', 0),
                    'char_count': chunk.get('char_count', 0)
                })
                if chunk.get('embedding_model'):
                    self.embedding_model = chunk['embedding_model']

            if not embeddings:
                logger.warning("No valid embeddings found in chunks")
                return

            embeddings_array = np.vstack(embeddings).astype('float32')

            if self.index_type == "ivf" and not self.index.is_trained:
                logger.info("Training IVF index...")
                self.index.train(embeddings_array)

            self.index.add(embeddings_array)

            # Store metadata; chunks mirror the same dicts (embeddings live only in
            # the FAISS index — keeping them here doubled the pickle for no reader)
            self.chunks.extend(metadata)
            self.metadata.extend(metadata)
            self._rebuild_bm25()
            
            logger.info(f"Added {len(embeddings)} documents to vector database. Total: {self.index.ntotal}")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}")
    
    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> List[Dict]:
        """Search for similar documents using query embedding"""
        try:
            if self.index.ntotal == 0:
                logger.warning("Vector database is empty")
                return []

            if isinstance(query_embedding, list):
                query_embedding = np.array(query_embedding)

            query_embedding = query_embedding.astype('float32').reshape(1, -1)

            distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.metadata):
                    result = self.metadata[idx].copy()
                    result['similarity_score'] = float(1 / (1 + distance))  # L2 distance -> 0..1
                    result['rank'] = i + 1
                    result['type'] = 'pdf'
                    results.append(result)

            logger.info(f"Found {len(results)} similar documents")
            return results

        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            return []

    def _rebuild_bm25(self):
        """Rebuild the BM25 keyword index over all chunks (sub-second at this scale).

        The document title and section label are indexed WITH the text: statute
        body text never names its own act or section ("103. Punishment for
        murder…" doesn't contain "Bharatiya Nyaya Sanhita" or "Order VII"), so
        queries like "murder under BNS" or "Order VII Rule 11" can only
        keyword-match via the label metadata.
        """
        try:
            corpus = [
                _TOKEN_RE.findall(
                    f"{m.get('document_title', '')} {m.get('section', '')} {m.get('text', '')}".lower()
                )
                for m in self.metadata
            ]
            self._bm25 = BM25Okapi(corpus) if corpus else None
            if self._bm25:
                logger.info(f"BM25 keyword index built over {len(corpus)} chunks")
        except Exception as e:
            logger.error(f"Error building BM25 index: {e}")
            self._bm25 = None

    @staticmethod
    def _int_to_roman(n: int) -> str:
        pairs = [(100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
        out = []
        for value, numeral in pairs:
            while n >= value:
                out.append(numeral)
                n -= value
        return ''.join(out)

    def label_search(self, query_text: str, top_k: int = 10) -> List[Dict]:
        """Exact section-label lookup for queries that NAME a provision.

        "What does Order VII Rule 11 provide?" or "Section 302 IPC" should hit
        the chunk labeled exactly that — regardless of how the fuzzy retrievers
        rank it. Returns [] fast when the query names nothing.
        """
        try:
            from .document_processor import TextPreprocessor
            from .document_registry import concept_sections
            refs = TextPreprocessor.extract_legal_references(query_text)

            # Lay-concept → exact (document, section) pairs (e.g. "anticipatory
            # bail" → BNSS 482 + CrPC 438), so the right provision surfaces even
            # when the statute text never uses the lay phrase.
            concept_pairs = concept_sections(query_text)

            if not refs and not concept_pairs:
                return []
            if not self.metadata:
                return []

            wanted = set()
            for ref in refs:
                wanted.add(ref.lower())
                # Users write "Order 7 Rule 11"; CPC labels use roman numerals
                arabic = re.match(r'(?i)order\s+(\d+)(?:\s+rule\s+(\d+[A-Z]{0,2}))?$', ref)
                if arabic:
                    roman = self._int_to_roman(int(arabic.group(1)))
                    wanted.add(f"order {roman} rule {arabic.group(2)}".lower()
                               if arabic.group(2) else f"order {roman}".lower())
            concept_wanted = {(_norm_doc(d), s.lower()) for d, s in concept_pairs}

            matches = [
                meta for meta in self.metadata
                if meta.get('section', '').lower() in wanted
                or (_norm_doc(meta.get('document', '')), meta.get('section', '').lower()) in concept_wanted
            ]
            # A bare section number can exist in MANY acts ("Section 138" is in 10
            # of the 25 docs). Such an ambiguous ref must NOT force-pin all of them
            # (it floods the cited slots and defeats the category boost). Count the
            # distinct documents each wanted-section matches; a section in >2 docs
            # is ambiguous → returned as a candidate but NOT force-pinned, so the
            # reranker + category boost pick the right act. Concept hits (exact
            # doc+section, e.g. "cheque bounce" → NI Act 138) are ALWAYS specific.
            docs_per_section = {}
            for meta in matches:
                s = meta.get('section', '').lower()
                docs_per_section.setdefault(s, set()).add(_norm_doc(meta.get('document', '')))
            ambiguous = {s for s, docs in docs_per_section.items() if len(docs) > 2}

            # Drop TOC stubs when a longer chunk for the same (doc, section) exists.
            longest = {}
            for meta in matches:
                key = (meta.get('document', ''), meta.get('section', ''))
                if len(meta.get('text', '')) > len(longest.get(key, {}).get('text', '')):
                    longest[key] = meta

            results = []
            # Concept-specific matches first (guaranteed), then the rest by length.
            def _sort_key(m):
                is_concept = (_norm_doc(m.get('document', '')), m.get('section', '').lower()) in concept_wanted
                return (0 if is_concept else 1, -len(m.get('text', '')))
            for meta in sorted(matches, key=_sort_key):
                key = (meta.get('document', ''), meta.get('section', ''))
                if longest.get(key) is not meta and len(meta.get('text', '')) < 120:
                    continue  # skip TOC stub, keep the substantive chunk
                section = meta.get('section', '').lower()
                is_concept = (_norm_doc(meta.get('document', '')), section) in concept_wanted
                result = meta.copy()
                result['similarity_score'] = 1.0  # exact label / concept match
                result['rank'] = len(results) + 1
                result['type'] = 'pdf'
                # Force-pin only SPECIFIC matches (concept hit, or a section that
                # names ≤2 acts). Ambiguous bare refs stay reranker-eligible.
                result['label_hit'] = is_concept or section not in ambiguous
                results.append(result)
                if len(results) >= top_k + 4:  # allow both eras + a couple
                    break
            if results:
                pinned = sum(1 for r in results if r.get('label_hit'))
                logger.info(f"Label lookup matched {len(results)} chunks ({pinned} pinned; "
                            f"refs={refs}, concepts={len(concept_pairs)})")
            return results

        except Exception as e:
            logger.error(f"Error in label search: {e}")
            return []

    def keyword_search(self, query_text: str, top_k: int = 10) -> List[Dict]:
        """BM25 keyword search. Returns the same result-dict shape as search().

        Legal queries are keyword-heavy ("Section 302 IPC") — exact term matches
        that dense embeddings often rank below thematically-similar text.
        """
        try:
            if self._bm25 is None or not self.metadata:
                return []
            tokens = _TOKEN_RE.findall(query_text.lower())
            if not tokens:
                return []

            scores = self._bm25.get_scores(tokens)
            order = np.argsort(scores)[::-1][:top_k]

            results = []
            for rank, idx in enumerate(order, start=1):
                score = float(scores[idx])
                if score <= 0:  # no query-term overlap at all
                    break
                result = self.metadata[idx].copy()
                # Bounded squash, NOT self-max normalization — dividing by the
                # top score would report every rank-1 keyword hit as 1.0 and
                # out-scale the dense scores in displays and confidence math.
                result['similarity_score'] = score / (score + 10.0)
                result['rank'] = rank
                result['type'] = 'pdf'
                results.append(result)

            logger.info(f"BM25 found {len(results)} keyword matches")
            return results

        except Exception as e:
            logger.error(f"Error in BM25 keyword search: {e}")
            return []
    
    def get_document_count(self) -> int:
        """Get total number of documents in the database"""
        return self.index.ntotal if self.index else 0
    
    def save_index(self, filepath: str):
        """Save the vector index and metadata to disk (atomically — a crash
        mid-save must not leave a readable .index paired with a torn .metadata)"""
        try:
            index_path = f"{filepath}.index"
            faiss.write_index(self.index, f"{index_path}.tmp")

            metadata_path = f"{filepath}.metadata"
            with open(f"{metadata_path}.tmp", 'wb') as f:
                pickle.dump({
                    'chunks': self.chunks,
                    'metadata': self.metadata,
                    'dimension': self.dimension,
                    'index_type': self.index_type,
                    'metadata_version': self.METADATA_VERSION,
                    'embedding_model': self.embedding_model
                }, f)

            os.replace(f"{index_path}.tmp", index_path)
            os.replace(f"{metadata_path}.tmp", metadata_path)
            
            logger.info(f"Saved vector database to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving vector database: {e}")
    
    def load_index(self, filepath: str) -> bool:
        """Load vector index and metadata from disk.

        Any failure resets to a clean empty state — a half-loaded index (FAISS
        vectors without their metadata) would silently misalign every future
        search after auto-ingest appends fresh vectors on top of stale ones.
        """
        try:
            index_path = f"{filepath}.index"
            if os.path.exists(index_path):
                self.index = faiss.read_index(index_path)
            else:
                logger.error(f"Index file not found: {index_path}")
                self.clear()
                return False

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
                self.clear()
                return False

            stored_version = data.get('metadata_version', 1)
            stored_model = data.get('embedding_model', '')
            if stored_version < self.METADATA_VERSION:
                logger.warning(
                    f"Vector DB at {filepath} uses old metadata schema v{stored_version} "
                    f"(no page numbers / real sections). Citations will be degraded. "
                    f"Fix: stop the backend, delete {filepath}.index and {filepath}.metadata, "
                    f"then restart — auto-ingest rebuilds with the new schema."
                )
            if self.embedding_model and stored_model and stored_model != self.embedding_model:
                logger.warning(
                    f"Vector DB was built with embedding model '{stored_model}' but the configured "
                    f"model is '{self.embedding_model}' — retrieval will be garbage. "
                    f"Fix: delete {filepath}.index and {filepath}.metadata and restart to rebuild."
                )

            self._rebuild_bm25()
            logger.info(f"Loaded vector database from {filepath}. Documents: {self.index.ntotal}")
            return True

        except Exception as e:
            logger.error(f"Error loading vector database: {e}")
            self.clear()
            return False
    
    def clear(self):
        """Clear all data from the vector database"""
        self._initialize_index()
        self.chunks = []
        self.metadata = []
        self._bm25 = None
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


