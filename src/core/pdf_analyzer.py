#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Analyseur de PDF
Analyse approfondie de la structure et du contenu des documents PDF

Auteur: L'OréalGPT
Version: 1.0.0
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
        self.list_patterns = [r'^[\s]*[•·‣⁃]\s+', r'^[\s]*[\d]+[.)]\s+', r'^[\s]*[a-zA-Z][.)]\s+', r'^[\s]*[-*+]\s+']
        self.logger.info("PDFAnalyzer initialisé")
    
    def analyze_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        try:
            self.logger.info(f"Début de l'analyse de {pdf_path}")
            self.doc = fitz.open(pdf_path)
            if self.doc.is_encrypted: raise ValueError("Document PDF chiffré non supporté")
            
            # --- MODIFICATION MAJEURE : Utilisation de l'extraction logique ---
            logical_text_elements = self._extract_logical_text_elements()

            analysis_result = {
                'document_info': self._analyze_document_info(),
                'page_structure': self._analyze_page_structure(),
                'text_elements': logical_text_elements, # Utilisation des nouveaux éléments logiques
                'fonts_used': self._analyze_fonts(),
                'metadata': self.doc.metadata,
                'analysis_timestamp': datetime.now().isoformat()
            }
            analysis_result['statistics'] = self._calculate_statistics(analysis_result)
            self.logger.info(f"Analyse terminée: {len(analysis_result['text_elements'])} éléments logiques trouvés")
            return analysis_result
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse PDF: {e}", exc_info=True)
            raise
        finally:
            if self.doc: self.doc.close(); self.doc = None

    def _extract_logical_text_elements(self) -> List[Dict[str, Any]]:
        """
        Nouvel algorithme qui fusionne les blocs adjacents en paragraphes logiques
        et encode les styles en Markdown.
        """
        logical_elements = []
        element_counter = 0

        for page_num, page in enumerate(self.doc):
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_INHIBIT_SPACES)["blocks"]
            if not blocks: continue

            # Trier les blocs par ordre de lecture
            sorted_blocks = sorted(blocks, key=lambda b: (b['bbox'][1], b['bbox'][0]))

            current_paragraph_blocks = []
            for block in sorted_blocks:
                if block['type'] != 0: continue # Ignorer les blocs d'images

                if not current_paragraph_blocks or self._should_merge(current_paragraph_blocks[-1], block):
                    current_paragraph_blocks.append(block)
                else:
                    # Finaliser le paragraphe précédent
                    element_counter += 1
                    logical_elements.append(self._finalize_paragraph(current_paragraph_blocks, element_counter, page_num + 1))
                    current_paragraph_blocks = [block]
            
            # Finaliser le dernier paragraphe de la page
            if current_paragraph_blocks:
                element_counter += 1
                logical_elements.append(self._finalize_paragraph(current_paragraph_blocks, element_counter, page_num + 1))

        return logical_elements

    def _should_merge(self, prev_block: Dict, current_block: Dict) -> bool:
        """Détermine si deux blocs consécutifs doivent être fusionnés."""
        px0, py0, px1, py1 = prev_block['bbox']
        cx0, cy0, cx1, cy1 = current_block['bbox']
        
        # Heuristique simple : vérifier la proximité verticale et l'alignement horizontal
        # (peut être affinée)
        vertical_distance = cy0 - py1
        is_close_vertically = 0 <= vertical_distance < 10 # 10 pixels de marge
        is_aligned_horizontally = abs(cx0 - px0) < 10

        # Vérifier si le texte précédent se termine par une ponctuation finale
        last_line_text = ""
        if prev_block['lines']:
             if prev_block['lines'][-1]['spans']:
                 last_line_text = prev_block['lines'][-1]['spans'][-1]['text'].strip()

        ends_with_punctuation = last_line_text.endswith(('.', '!', '?', ':', '•'))

        return is_close_vertically and is_aligned_horizontally and not ends_with_punctuation

    def _finalize_paragraph(self, blocks: List[Dict], element_id: int, page_num: int) -> Dict[str, Any]:
        """Crée un élément logique à partir d'une liste de blocs fusionnés."""
        # Calculer le rectangle englobant
        min_x0 = min(b['bbox'][0] for b in blocks)
        min_y0 = min(b['bbox'][1] for b in blocks)
        max_x1 = max(b['bbox'][2] for b in blocks)
        max_y1 = max(b['bbox'][3] for b in blocks)
        combined_bbox = (min_x0, min_y0, max_x1, max_y1)

        # Générer le contenu avec Markdown pour les styles
        markdown_content = ""
        for i, block in enumerate(blocks):
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    text = span['text']
                    flags = span['flags']
                    is_bold = flags & 2**4
                    is_italic = flags & 2**1
                    
                    if is_bold and is_italic:
                        markdown_content += f"***{text}***"
                    elif is_bold:
                        markdown_content += f"**{text}**"
                    elif is_italic:
                        markdown_content += f"*{text}*"
                    else:
                        markdown_content += text
                markdown_content += " " # Espace entre les lignes
            if i < len(blocks) - 1:
                markdown_content += "\n" # Nouveau paragraphe dans le bloc logique

        # Utiliser les informations du premier span comme référence
        first_span = blocks[0]['lines'][0]['spans'][0]
        font_info = self._extract_font_info(first_span)
        content_type = self._classify_content(markdown_content, font_info)
        
        return {
            'id': f"T{element_id:03d}",
            'content': markdown_content.strip(),
            'page_number': page_num,
            'bbox': combined_bbox,
            'font_info': font_info.__dict__,
            'content_type': content_type.value,
            'reading_order': element_id
        }

    def _extract_font_info(self, span: Dict[str, Any]) -> FontInfo:
        flags = span.get("flags", 0)
        return FontInfo(
            name=span.get("font", "Unknown"), size=span.get("size", 12.0), flags=flags,
            is_bold=bool(flags & 2**4), is_italic=bool(flags & 2**1), is_mono=bool(flags & 2**0),
            encoding=span.get("encoding", "utf-8")
        )

    def _classify_content(self, text: str, font_info: FontInfo) -> ContentType:
        # Logique de classification simplifiée pour le bloc
        if font_info.size >= self.title_size_threshold: return ContentType.TITLE
        if font_info.size >= self.subtitle_size_threshold: return ContentType.SUBTITLE
        for pattern in self.list_patterns:
            if re.match(pattern, text.strip()): return ContentType.LIST_ITEM
        return ContentType.PARAGRAPH

    # Les autres fonctions (analyze_document_info, etc.) restent les mêmes
    # Elles sont nécessaires pour la complétude du fichier.
    def _analyze_document_info(self) -> Dict[str, Any]:
        return { 'page_count': len(self.doc), 'pdf_version': self.doc.metadata.get('format', 'Inconnue') }
    def _analyze_page_structure(self) -> Dict[int, Dict[str, Any]]:
        return { i+1: {'dimensions': {'width': p.rect.width, 'height': p.rect.height}} for i, p in enumerate(self.doc) }
    def _analyze_fonts(self) -> List[Dict[str, Any]]:
        fonts = set()
        for page in self.doc: fonts.update(f[3] for f in page.get_fonts())
        return [{'name': f} for f in fonts]
    def _extract_metadata(self) -> Dict[str, Any]:
        return self.doc.metadata
    def _calculate_statistics(self, res: Dict[str, Any]) -> Dict[str, Any]:
        return {'total_text_elements': len(res['text_elements'])}
