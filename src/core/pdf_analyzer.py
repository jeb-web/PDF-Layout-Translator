#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Analyseur de PDF
Analyse approfondie de la structure et du contenu des documents PDF

Auteur: L'OréalGPT
Version: 1.0.2 (Correction de l'harmonisation des noms de police)
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import fitz  # PyMuPDF

class ContentType(Enum):
    TITLE = "title"; SUBTITLE = "subtitle"; PARAGRAPH = "paragraph"; LIST_ITEM = "list_item"
    CAPTION = "caption"; FOOTER = "footer"; HEADER = "header"; TABLE_CELL = "table_cell"
    QUOTE = "quote"; CODE = "code"; UNKNOWN = "unknown"

@dataclass
class FontInfo:
    name: str; size: float; flags: int; is_bold: bool; is_italic: bool; is_mono: bool; encoding: str

@dataclass
class TextElement:
    id: str; content: str; page_number: int; bbox: Tuple[float, float, float, float]
    font_info: FontInfo; content_type: ContentType; reading_order: int

class PDFAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.doc: Optional[fitz.Document] = None
        self.title_size_threshold = 16.0
        self.subtitle_size_threshold = 14.0
        self.paragraph_min_words = 3
        self.list_patterns = [
            r'^[\s]*[•·‣⁃]\s+', r'^[\s]*[\d]+[.)]\s+', r'^[\s]*[a-zA-Z][.)]\s+', r'^[\s]*[-*+]\s+']
        self.logger.info("PDFAnalyzer initialisé")

    def _normalize_font_name(self, font_name: str) -> str:
        """Supprime le préfixe de sous-ensemble 'ABCDEE+' d'un nom de police."""
        return re.sub(r"^[A-Z]{6}\+", "", font_name)

    def _create_font_name_map(self, reliable_names: List[str], unreliable_names: set) -> Dict[str, str]:
        """Crée une carte de correspondance entre les noms de police tronqués et les noms complets et fiables."""
        font_map = {}
        clean_reliable_map = {name.lower().replace("-", ""): name for name in reliable_names}

        for unreliable in unreliable_names:
            clean_unreliable = unreliable.lower().replace("-", "")
            found_match = False
            # Chercher la correspondance la plus longue possible
            best_match = ""
            for clean_reliable, original_reliable in clean_reliable_map.items():
                if clean_reliable.startswith(clean_unreliable):
                    if len(original_reliable) > len(best_match):
                        best_match = original_reliable
                        found_match = True
            
            if found_match:
                font_map[unreliable] = best_match
            else:
                font_map[unreliable] = unreliable # Garder l'original si aucune correspondance n'est trouvée
        return font_map

    def analyze_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        try:
            self.logger.info(f"Début de l'analyse de {pdf_path}")
            self.doc = fitz.open(pdf_path)
            if self.doc.is_encrypted: raise ValueError("Document PDF chiffré non supporté")

            # Étape 1: Extraire les éléments avec leurs noms de police potentiellement incohérents
            logical_text_elements = self._extract_logical_text_elements()
            
            # Étape 2: Extraire la "Source de Vérité" : la liste des polices avec leurs noms complets
            fonts_used_list = self._analyze_fonts()
            reliable_font_names = [font['name'] for font in fonts_used_list]
            
            # Étape 3: Créer la carte d'harmonisation et corriger les éléments de texte
            unreliable_font_names = {elem['font_info']['name'] for elem in logical_text_elements}
            font_name_map = self._create_font_name_map(reliable_font_names, unreliable_font_names)
            
            for element in logical_text_elements:
                unreliable_name = element['font_info']['name']
                if unreliable_name in font_name_map:
                    element['font_info']['name'] = font_name_map[unreliable_name]

            # Le rapport d'analyse est maintenant garanti d'être cohérent
            analysis_result = {
                'document_info': self._analyze_document_info(),
                'page_structure': self._analyze_page_structure(),
                'text_elements': logical_text_elements,
                'fonts_used': fonts_used_list,
                'metadata': self.doc.metadata,
                'analysis_timestamp': datetime.now().isoformat()
            }
            analysis_result['statistics'] = self._calculate_statistics(analysis_result)
            self.logger.info("Analyse terminée et noms de police harmonisés.")
            return analysis_result
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse PDF: {e}", exc_info=True)
            raise
        finally:
            if self.doc: self.doc.close(); self.doc = None

    def _extract_logical_text_elements(self) -> List[Dict[str, Any]]:
        logical_elements = []
        element_counter = 0
        for page_num, page in enumerate(self.doc):
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_INHIBIT_SPACES)["blocks"]
            if not blocks: continue
            sorted_blocks = sorted([b for b in blocks if b['type'] == 0], key=lambda b: (b['bbox'][1], b['bbox'][0]))
            if not sorted_blocks: continue
            current_paragraph_blocks = [sorted_blocks[0]]
            for i in range(1, len(sorted_blocks)):
                prev_block = current_paragraph_blocks[-1]
                current_block = sorted_blocks[i]
                if self._should_merge(prev_block, current_block):
                    current_paragraph_blocks.append(current_block)
                else:
                    element_counter += 1
                    logical_elements.append(self._finalize_paragraph(current_paragraph_blocks, element_counter, page_num + 1))
                    current_paragraph_blocks = [current_block]
            if current_paragraph_blocks:
                element_counter += 1
                logical_elements.append(self._finalize_paragraph(current_paragraph_blocks, element_counter, page_num + 1))
        return logical_elements

    def _should_merge(self, prev_block: Dict, current_block: Dict) -> bool:
        px0, py0, px1, py1 = prev_block['bbox']
        cx0, cy0, cx1, cy1 = current_block['bbox']
        vertical_distance = cy0 - py1
        is_close_vertically = 0 <= vertical_distance < 10
        is_aligned_horizontally = abs(cx0 - px0) < 10
        last_line_text = ""
        if prev_block.get('lines') and prev_block['lines'][-1].get('spans'):
            last_line_text = prev_block['lines'][-1]['spans'][-1]['text'].strip()
        ends_with_punctuation = last_line_text.endswith(('.', '!', '?', ':', '•'))
        return is_close_vertically and is_aligned_horizontally and not ends_with_punctuation

    def _finalize_paragraph(self, blocks: List[Dict], element_id: int, page_num: int) -> Dict[str, Any]:
        min_x0 = min(b['bbox'][0] for b in blocks); min_y0 = min(b['bbox'][1] for b in blocks)
        max_x1 = max(b['bbox'][2] for b in blocks); max_y1 = max(b['bbox'][3] for b in blocks)
        combined_bbox = (min_x0, min_y0, max_x1, max_y1)
        markdown_content = ""
        for block in blocks:
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    text = span['text']
                    is_bold = span['flags'] & 2**4
                    is_italic = span['flags'] & 2**1
                    if is_bold and is_italic: markdown_content += f"***{text}***"
                    elif is_bold: markdown_content += f"**{text}**"
                    elif is_italic: markdown_content += f"*{text}*"
                    else: markdown_content += text
                markdown_content += " "
        first_span = blocks[0]['lines'][0]['spans'][0]
        font_info = self._extract_font_info(first_span)
        content_type = self._classify_content(markdown_content, font_info)
        return {'id': f"T{element_id:03d}", 'content': markdown_content.strip(), 'page_number': page_num, 'bbox': combined_bbox, 'font_info': font_info.__dict__, 'content_type': content_type.value, 'reading_order': element_id}

    def _extract_font_info(self, span: Dict[str, Any]) -> FontInfo:
        flags = span.get("flags", 0)
        original_name = self._normalize_font_name(span.get("font", "Unknown"))
        return FontInfo(name=original_name, size=span.get("size", 12.0), flags=flags, is_bold=bool(flags & 2**4), is_italic=bool(flags & 2**1), is_mono=bool(flags & 2**0), encoding=span.get("encoding", "utf-8"))

    def _classify_content(self, text: str, font_info: FontInfo) -> ContentType:
        if font_info.size >= self.title_size_threshold: return ContentType.TITLE
        if font_info.size >= self.subtitle_size_threshold: return ContentType.SUBTITLE
        for pattern in self.list_patterns:
            if re.match(pattern, text.strip()): return ContentType.LIST_ITEM
        if len(text.split()) < self.paragraph_min_words: return ContentType.CAPTION
        return ContentType.PARAGRAPH

    def _analyze_document_info(self) -> Dict[str, Any]:
        return {'page_count': len(self.doc), 'pdf_version': self.doc.metadata.get('format', 'Inconnue'), 'has_links': any(p.get_links() for p in self.doc), 'has_forms': any(p.widgets() for p in self.doc)}
    
    def _analyze_page_structure(self) -> Dict[int, Dict[str, Any]]:
        return { i+1: {'dimensions': {'width': p.rect.width, 'height': p.rect.height}} for i, p in enumerate(self.doc) }
    
    def _analyze_fonts(self) -> List[Dict[str, Any]]:
        fonts = {}
        for page in self.doc:
            for f in page.get_fonts():
                normalized_name = self._normalize_font_name(f[3])
                if normalized_name not in fonts: fonts[normalized_name] = 0
                fonts[normalized_name] += 1
        return [{'name': name, 'page_count': count} for name, count in fonts.items()]
    
    def _calculate_statistics(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        text_elements = analysis_result['text_elements']
        content_dist = {}
        total_chars = 0
        total_words = 0
        for elem in text_elements:
            ct = elem['content_type']
            if ct not in content_dist: content_dist[ct] = 0
            content_dist[ct] += 1
            total_chars += len(elem['content'])
            total_words += len(elem['content'].split())
        return {'total_text_elements': len(text_elements), 'total_characters': total_chars, 'total_words': total_words, 'average_words_per_element': total_words / max(1, len(text_elements)), 'content_type_distribution': content_dist}
