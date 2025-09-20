"""
Document Processing Module

Handles PDF extraction, text cleaning, and chunking of legal documents.
"""

import os
import re
from typing import List, Dict, Tuple
from pathlib import Path
import PyPDF2
from loguru import logger


class DocumentProcessor:
    """Processes legal documents (PDFs) into clean, structured chunks"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(f"DocumentProcessor initialized with chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    text += page_text + "\n"
                    
                logger.info(f"Extracted text from {pdf_path}: {len(text)} characters, {len(pdf_reader.pages)} pages")
                return text
                
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers (basic patterns)
        text = re.sub(r'\n\d+\n', '\n', text)  # Remove standalone page numbers
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        
        # Fix common OCR errors
        text = text.replace('|', 'I')  # Common OCR error
        text = text.replace('0', 'O', )  # Only in certain contexts
        
        # Normalize section references
        text = re.sub(r'Section\s+(\d+)', r'Section \1', text, flags=re.IGNORECASE)
        text = re.sub(r'Article\s+(\d+)', r'Article \1', text, flags=re.IGNORECASE)
        
        # Remove extra spaces and normalize
        text = ' '.join(text.split())
        
        logger.info(f"Text cleaned: {len(text)} characters")
        return text.strip()
    
    def create_chunks(self, text: str, document_name: str) -> List[Dict]:
        """Split text into overlapping chunks with metadata"""
        chunks = []
        
        # Try to split by sections first (legal documents often have clear sections)
        section_splits = self._split_by_sections(text)
        
        if len(section_splits) > 1:
            # Process each section separately
            for section_num, section_text in enumerate(section_splits):
                section_chunks = self._chunk_text(section_text, document_name, f"Section-{section_num+1}")
                chunks.extend(section_chunks)
        else:
            # Fallback to simple chunking
            chunks = self._chunk_text(text, document_name, "Full-Document")
        
        logger.info(f"Created {len(chunks)} chunks from {document_name}")
        return chunks
    
    def _split_by_sections(self, text: str) -> List[str]:
        """Split text by legal sections if possible"""
        # Look for section patterns in legal documents
        section_patterns = [
            r'(?:Section|SECTION)\s+\d+',
            r'(?:Article|ARTICLE)\s+\d+',
            r'(?:Chapter|CHAPTER)\s+\d+',
            r'\d+\.\s+[A-Z][a-z]+'  # Numbered headings
        ]
        
        for pattern in section_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if len(matches) > 2:  # Found multiple sections
                sections = []
                for i, match in enumerate(matches):
                    start = match.start()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                    section_text = text[start:end].strip()
                    if len(section_text) > 100:  # Only include substantial sections
                        sections.append(section_text)
                
                if sections:
                    return sections
        
        return [text]  # Return as single section if no clear splits found
    
    def _chunk_text(self, text: str, document_name: str, section_name: str) -> List[Dict]:
        """Create overlapping chunks from text"""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            # Skip very short chunks
            if len(chunk_text.strip()) < 50:
                continue
            
            chunk_data = {
                'text': chunk_text,
                'document': document_name,
                'section': section_name,
                'chunk_id': f"{document_name}_{section_name}_{i//self.chunk_size}",
                'word_count': len(chunk_words),
                'char_count': len(chunk_text)
            }
            
            chunks.append(chunk_data)
        
        return chunks
    
    def process_document(self, pdf_path: str) -> List[Dict]:
        """Complete pipeline: extract, clean, and chunk a PDF document"""
        document_name = Path(pdf_path).stem
        
        # Extract text
        raw_text = self.extract_text_from_pdf(pdf_path)
        if not raw_text.strip():
            logger.warning(f"No text extracted from {pdf_path}")
            return []
        
        # Clean text
        clean_text = self.clean_text(raw_text)
        
        # Create chunks
        chunks = self.create_chunks(clean_text, document_name)
        
        logger.info(f"Processed {pdf_path}: {len(chunks)} chunks created")
        return chunks
    
    def process_directory(self, directory_path: str) -> Dict[str, List[Dict]]:
        """Process all PDF files in a directory"""
        results = {}
        pdf_files = list(Path(directory_path).glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {directory_path}")
            return results
        
        for pdf_file in pdf_files:
            try:
                chunks = self.process_document(str(pdf_file))
                results[pdf_file.name] = chunks
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                results[pdf_file.name] = []
        
        total_chunks = sum(len(chunks) for chunks in results.values())
        logger.info(f"Processed {len(pdf_files)} PDF files, created {total_chunks} total chunks")
        
        return results


class TextPreprocessor:
    """Additional text preprocessing utilities for legal documents"""
    
    @staticmethod
    def extract_legal_references(text: str) -> List[str]:
        """Extract legal references like section numbers, article numbers"""
        references = []
        
        # Section references
        section_matches = re.findall(r'Section\s+(\d+(?:\([a-z]+\))?)', text, re.IGNORECASE)
        references.extend([f"Section {match}" for match in section_matches])
        
        # Article references  
        article_matches = re.findall(r'Article\s+(\d+(?:\([a-z]+\))?)', text, re.IGNORECASE)
        references.extend([f"Article {match}" for match in article_matches])
        
        # Chapter references
        chapter_matches = re.findall(r'Chapter\s+(\d+)', text, re.IGNORECASE)
        references.extend([f"Chapter {match}" for match in chapter_matches])
        
        return list(set(references))  # Remove duplicates
    
    @staticmethod
    def identify_document_type(text: str) -> str:
        """Identify the type of legal document based on content"""
        text_lower = text.lower()
        
        if any(term in text_lower for term in ['indian penal code', 'ipc', 'punishment', 'offense']):
            return "Criminal Law"
        elif any(term in text_lower for term in ['civil procedure', 'cpc', 'suit', 'decree']):
            return "Civil Law"  
        elif any(term in text_lower for term in ['constitution', 'fundamental rights', 'directive principles']):
            return "Constitutional Law"
        elif any(term in text_lower for term in ['income tax', 'gst', 'taxation']):
            return "Tax Law"
        else:
            return "General Law"
    
    @staticmethod
    def extract_key_terms(text: str) -> List[str]:
        """Extract important legal terms and concepts"""
        # Common legal terms to identify
        legal_terms = [
            'jurisdiction', 'precedent', 'statute', 'regulation', 'ordinance',
            'plaintiff', 'defendant', 'appellant', 'respondent', 'magistrate',
            'tribunal', 'court', 'judge', 'justice', 'advocate', 'counsel',
            'evidence', 'witness', 'testimony', 'affidavit', 'petition',
            'writ', 'appeal', 'revision', 'review', 'bail', 'custody'
        ]
        
        found_terms = []
        text_lower = text.lower()
        
        for term in legal_terms:
            if term in text_lower:
                found_terms.append(term)
        
        return found_terms