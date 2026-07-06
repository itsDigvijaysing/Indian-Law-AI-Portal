"""
Document Processing Module

Handles PDF extraction, text cleaning, and chunking of legal documents.
Chunks carry real provenance: page ranges, actual legal section labels,
and the legal references found in their text.
"""

import os
import re
from bisect import bisect_right
from typing import List, Dict, Tuple
from pathlib import Path
import PyPDF2
from loguru import logger


class DocumentProcessor:
    """Processes legal documents (PDFs) into clean, structured chunks"""

    # Heading patterns tried against a document; the one with the most hits wins.
    _SECTION_PATTERNS = [
        r'(?:Section|SECTION)\s+\d+[A-Z]{0,2}',
        r'(?:Article|ARTICLE)\s+\d+[A-Z]{0,2}',
        r'(?:Order|ORDER)\s+(?:[IVXLC]+|\d+)(?:\s*,?\s*(?:Rule|RULE)\s+\d+)?',
        r'(?:Chapter|CHAPTER)\s+(?:[IVXLC]+|\d+)',
        r'\d+[A-Z]{0,2}\.\s+[A-Z][a-z]+'  # Bare numbered headings: "302. Punishment…", "498A. Husband…"
    ]

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.info(f"DocumentProcessor initialized with chunk_size={chunk_size}, overlap={chunk_overlap}")

    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, List[Tuple[int, int]]]:
        """Extract text from a PDF, cleaned per page so char offsets stay valid.

        Returns (text, page_offsets) where page_offsets is a list of
        (char_start_in_text, page_number) tuples, page numbers 1-based.
        """
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pages = []
                page_offsets = []
                cursor = 0

                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    page_text = self.clean_text(page.extract_text() or "")
                    if not page_text:
                        continue
                    page_offsets.append((cursor, page_num))
                    pages.append(page_text)
                    cursor += len(page_text) + 1  # +1 for the joining space

                text = " ".join(pages)
                logger.info(f"Extracted text from {pdf_path}: {len(text)} characters, {len(pdf_reader.pages)} pages")
                return text, page_offsets

        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return "", []

    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove page numbers and headers/footers before whitespace collapsing
        # (these patterns rely on line boundaries)
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)  # Remove standalone page numbers
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Fix common OCR errors in non-numeric contexts
        text = re.sub(r'(?<![0-9])\|(?![0-9])', 'I', text)  # '|' → 'I' only outside numbers

        # Normalize section references
        text = re.sub(r'Section\s+(\d+)', r'Section \1', text, flags=re.IGNORECASE)
        text = re.sub(r'Article\s+(\d+)', r'Article \1', text, flags=re.IGNORECASE)

        # Remove extra spaces and normalize
        text = ' '.join(text.split())

        logger.debug(f"Text cleaned: {len(text)} characters")
        return text.strip()

    def create_chunks(self, text: str, document_name: str,
                      page_offsets: List[Tuple[int, int]] = None) -> List[Dict]:
        """Split text into chunks along real section boundaries, with page metadata"""
        page_offsets = page_offsets or []
        page_starts = [start for start, _ in page_offsets]
        page_numbers = [page for _, page in page_offsets]
        document_title = self._derive_title(document_name)

        chunks = []
        for label, sec_start, sec_end in self._split_by_sections(text, document_name):
            section_chunks = self._chunk_text(
                text[sec_start:sec_end], document_name, label, base_offset=sec_start
            )
            chunks.extend(section_chunks)

        for running_index, chunk in enumerate(chunks, start=1):
            chunk['chunk_id'] = f"{document_name}::{running_index}"
            chunk['document_title'] = document_title
            chunk['page_start'] = self._page_for_offset(page_starts, page_numbers, chunk['char_start'])
            chunk['page_end'] = self._page_for_offset(page_starts, page_numbers, max(chunk['char_start'], chunk['char_end'] - 1))
            refs = TextPreprocessor.extract_legal_references(chunk['text'])
            chunk['legal_sections'] = refs[:8]

        logger.info(f"Created {len(chunks)} chunks from {document_name}")
        return chunks

    @staticmethod
    def _page_for_offset(page_starts: List[int], page_numbers: List[int], char_pos: int) -> int:
        """Map a char offset in the concatenated text to its 1-based PDF page (0 if unknown)."""
        if not page_starts:
            return 0
        idx = bisect_right(page_starts, char_pos) - 1
        return page_numbers[max(0, idx)]

    # Words kept as-is (not title-cased) when cleaning ALL-CAPS statute names
    _TITLE_KEEP = {'of', 'and', 'the', 'for', 'to', 'on', 'in', 'a'}

    @staticmethod
    def _derive_title(stem: str) -> str:
        """Human title from a filename stem, robust to the 25-doc naming mix.

        'Bharatiya_Nyaya_Sanhita_2023'            → 'Bharatiya Nyaya Sanhita, 2023'
        'THE NEGOTIABLE INSTRUMENTS ACT, 1881'    → 'Negotiable Instruments Act, 1881'
        'THE INDIAN EVIDENCE ACT, 1872 '          → 'Indian Evidence Act, 1872'
        'The Digital ... Act, Extra Added 2025'   → 'Digital Personal Data Protection Rules, 2025'
        """
        title = stem.replace('_', ' ').strip()

        # Filename artifact: this file is actually the DPDP Rules 2025
        if 'extra added' in title.lower():
            return 'Digital Personal Data Protection Rules, 2025'

        # Drop a leading "The " (statute titles read better without it)
        title = re.sub(r'^(?i:the)\s+', '', title)

        # Title-case ALL-CAPS names; leave already-mixed-case names alone
        if title.isupper():
            words = []
            for i, w in enumerate(title.split()):
                lw = w.lower()
                words.append(lw if (i > 0 and lw in DocumentProcessor._TITLE_KEEP) else w.capitalize())
            title = ' '.join(words)

        # Comma before a trailing year, but not if one is already there
        title = re.sub(r',?\s+(\d{4})$', r', \1', title)
        return title.strip()

    @staticmethod
    def _normalize_heading(heading: str) -> str:
        heading = re.sub(r'\s+', ' ', heading).strip().rstrip('.,')
        for word in ('Section', 'Article', 'Chapter', 'Order', 'Rule'):
            heading = re.sub(rf'(?i)\b{word}\b', word, heading)
        return heading

    @staticmethod
    def _heading_number(heading: str) -> int:
        """Leading numeric part of a heading's identifier, or -1 if none (e.g. roman numerals)."""
        match = re.search(r'\b(\d+)', heading)
        return int(match.group(1)) if match else -1

    # India Code PDFs carry amendment footnotes ("1. Subs. by Act 10 of 1886…",
    # "2. The words 'X' omitted by…") that look exactly like numbered headings.
    # "The" alone is NOT enough to reject — Constitution articles read
    # "14. The State shall not deny…" — only "The words/figures/…" is footnote-speak.
    _FOOTNOTE_START = re.compile(
        r'\d+[A-Z]{0,2}\.\s+(?:Subs|Ins|Rep|Added|Omitted|Substituted|Inserted|Repealed'
        r'|The\s+(?:words?|figures?|letters?|brackets?|proviso|Explanation))\b',
        re.IGNORECASE
    )

    # Schedule headings are printed in caps in the body ("THE FIRST SCHEDULE");
    # without them, everything after a document's last numbered section (offence
    # classification tables, forms) inherits that last section's label.
    _SCHEDULE_RE = re.compile(r'THE\s+([A-Z]+)\s+SCHEDULE')

    @classmethod
    def _monotonic_headings(cls, matches: List) -> List:
        """Keep matches that behave like real statute headings: numbers go upward.

        A match whose number is not greater than the previous kept heading is a
        body-text cross-reference or footnote, not a heading — except number 1,
        which is allowed to reset the sequence (table-of-contents → body
        transition, schedules, appendices). Amendment-footnote lookalikes are
        dropped outright.
        """
        kept = []
        last_num = -1
        for match in matches:
            heading = match.group(0)
            if cls._FOOTNOTE_START.match(heading):
                continue
            num = cls._heading_number(heading)
            if num > 999:  # years ("2023. The …") — no Indian code has 4-digit sections
                continue
            if num == -1 or num > last_num or num == 1:
                kept.append(match)
                if num != -1:
                    last_num = num
        return kept

    def _split_by_sections(self, text: str, document_name: str = "") -> List[Tuple[str, int, int]]:
        """Split text on real legal-heading boundaries.

        Returns (label, char_start, char_end) tuples. Every pattern's matches are
        filtered for monotonic-heading behavior first, and the pattern with the most
        SURVIVING matches wins — true headings number upward and survive the filter,
        while scattered cross-references collapse. Bare numbered headings
        ("302. Punishment…") get a document-aware prefix (Article for the
        Constitution, Section otherwise).
        """
        kept = []
        for pattern in self._SECTION_PATTERNS:
            matches = self._monotonic_headings(list(re.finditer(pattern, text, re.IGNORECASE)))
            if len(matches) > len(kept):
                kept = matches

        if len(kept) <= 2:
            return [("Full-Document", 0, len(text))]

        bare_prefix = "Article" if "constitution" in document_name.lower() else "Section"
        order_positions = self._order_heading_positions(text)

        # Boundary list: kept section headings + schedule headings, by position
        boundaries = []
        for match in kept:
            heading = match.group(0)
            bare = re.match(r'^(\d+[A-Z]{0,2})\.\s', heading)
            if bare:
                order = self._governing_order(order_positions, match.start())
                label = f"{order} Rule {bare.group(1)}" if order else f"{bare_prefix} {bare.group(1)}"
            else:
                label = self._normalize_heading(heading)
            boundaries.append((match.start(), label))
        for smatch in self._SCHEDULE_RE.finditer(text):
            boundaries.append((smatch.start(), f"The {smatch.group(1).title()} Schedule"))
        boundaries.sort(key=lambda b: b[0])

        sections = []
        if boundaries[0][0] > 100:
            sections.append(("Front matter", 0, boundaries[0][0]))
        for i, (start, label) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            # Keep even very short sections (repealed stubs like "303. [Repealed]"
            # are legally meaningful); only drop heading-only fragments
            if end - start > 50:
                sections.append((label, start, end))

        return sections or [("Full-Document", 0, len(text))]

    @classmethod
    def _order_heading_positions(cls, text: str) -> List[Tuple[int, str]]:
        """Positions of schedule Order headings (CPC First Schedule).

        India Code prints schedule headings in caps ("ORDER VII") while body
        cross-references are mixed case ("Order VII, rule 1") — so a
        case-sensitive match isolates the real headings. Numbered rules that
        follow an ORDER heading are cited "Order VII Rule 11", not "Section 11".
        """
        positions = []
        last = 0
        for match in re.finditer(r'ORDER\s+([IVXLC]+)\b', text):
            value = cls._roman_to_int(match.group(1))
            if value == 1 or value > last:
                positions.append((match.start(), f"Order {match.group(1)}"))
                last = value
        return positions if len(positions) > 5 else []

    @staticmethod
    def _governing_order(order_positions: List[Tuple[int, str]], char_pos: int) -> str:
        """Label of the last Order heading before char_pos, or '' if none."""
        governing = ""
        for pos, label in order_positions:
            if pos > char_pos:
                break
            governing = label
        return governing

    @staticmethod
    def _roman_to_int(roman: str) -> int:
        values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
        total = 0
        for i, ch in enumerate(roman):
            v = values.get(ch, 0)
            if i + 1 < len(roman) and values.get(roman[i + 1], 0) > v:
                total -= v
            else:
                total += v
        return total

    def _chunk_text(self, text: str, document_name: str, section_name: str,
                    base_offset: int = 0) -> List[Dict]:
        """Create overlapping chunks from text, tracking char offsets"""
        chunks = []
        words = text.split()
        if not words:
            return chunks

        # Char offset of each word within text (text is single-space normalized)
        word_offsets = []
        pos = 0
        for word in words:
            idx = text.find(word, pos)
            word_offsets.append(idx)
            pos = idx + len(word)

        step = max(1, self.chunk_size - self.chunk_overlap)
        part = 0
        for i in range(0, len(words), step):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)

            # Skip very short chunks
            if len(chunk_text.strip()) < 50:
                continue

            part += 1
            last = min(i + self.chunk_size, len(words)) - 1
            chunks.append({
                'text': chunk_text,
                'document': document_name,
                'section': section_name,
                'part': part,
                'char_start': base_offset + word_offsets[i],
                'char_end': base_offset + word_offsets[last] + len(words[last]),
                'word_count': len(chunk_words),
                'char_count': len(chunk_text)
            })

        return chunks

    def process_document(self, pdf_path: str) -> List[Dict]:
        """Complete pipeline: extract, clean, and chunk a PDF document"""
        document_name = Path(pdf_path).stem

        # Extract text (cleaned per page so page offsets stay accurate)
        text, page_offsets = self.extract_text_from_pdf(pdf_path)
        if not text.strip():
            logger.warning(f"No text extracted from {pdf_path}")
            return []

        # Create chunks
        chunks = self.create_chunks(text, document_name, page_offsets)

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

        # Section references (incl. letter suffixes like 498A and sub-clauses)
        section_matches = re.findall(r'Section\s+(\d+[A-Z]{0,2}(?:\([0-9a-zA-Z]+\))*)', text, re.IGNORECASE)
        references.extend([f"Section {match}" for match in section_matches])

        # Article references
        article_matches = re.findall(r'Article\s+(\d+[A-Z]{0,2}(?:\([0-9a-zA-Z]+\))*)', text, re.IGNORECASE)
        references.extend([f"Article {match}" for match in article_matches])

        # Order/Rule references (CPC schedules)
        order_matches = re.findall(r'Order\s+([IVXLC]+|\d+)(?:\s*,?\s*Rule\s+(\d+))?', text, re.IGNORECASE)
        for order, rule in order_matches:
            references.append(f"Order {order} Rule {rule}" if rule else f"Order {order}")

        # Chapter references
        chapter_matches = re.findall(r'Chapter\s+([IVXLC]+|\d+)', text, re.IGNORECASE)
        references.extend([f"Chapter {match}" for match in chapter_matches])

        # Deduplicate preserving first-occurrence order
        return list(dict.fromkeys(references))

    @staticmethod
    def identify_document_type(text: str) -> str:
        """Identify the type of legal document based on content"""
        text_lower = text.lower()

        if any(term in text_lower for term in ['indian penal code', 'ipc', 'punishment', 'offense', 'bharatiya nyaya sanhita', 'bns', 'bharatiya nagarik suraksha', 'bnss']):
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
