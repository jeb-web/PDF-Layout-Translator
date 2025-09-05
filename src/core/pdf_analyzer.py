#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Analyseur de PDF
Construit un DOM de la page à partir du fichier PDF.

Auteur: L'OréalGPT
Version: 2.0.1 (Correction des imports)
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Any
import fitz  # PyMuPDF
# CORRECTION: Import absolu depuis la racine 'src'
from core.data_model import PageObject, TextBlock, TextSpan, FontInfo

class PDFAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _normalize_font_name(self, font_name: str) -> str:
        """Supprime le préfixe de sous-ensemble 'ABCDEE+' d'un nom de police."""
        return re.sub(r"^[A-Z]{6}\+", "", font_name)

    def analyze_pdf(self, pdf_path: Path) -> List[PageObject]:
        """Analyse l'intégralité du PDF et retourne une liste d'objets PageObject."""
        self.logger.info(f"Début de l'analyse architecturale de {pdf_path}")
        doc = fitz.open(pdf_path)
        pages = []

        for page_num, page in enumerate(doc):
            width, height = page.rect.width, page.rect.height
            page_obj = PageObject(page_number=page_num + 1, dimensions=(width, height))
            
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_INHIBIT_SPACES)["blocks"]
            
            block_counter = 0
            for block in sorted([b for b in blocks if b['type'] == 0], key=lambda b: (b['bbox'][1], b['bbox'][0])):
                block_counter += 1
                block_id = f"P{page_num+1}_B{block_counter}"
                
                text_block = TextBlock(id=block_id, bbox=block['bbox'])
                
                span_counter = 0
                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        span_counter += 1
                        span_id = f"{block_id}_S{span_counter}"
                        
                        color_int = span['color']
                        color_hex = f"#{color_int>>16:02x}{(color_int>>8)&0xFF:02x}{color_int&0xFF:02x}"
                        
                        font_name = self._normalize_font_name(span['font'])
                        flags = span['flags']
                        is_bold = "bold" in font_name.lower() or bool(flags & 2**4)
                        is_italic = "italic" in font_name.lower() or bool(flags & 2**1)

                        font_info = FontInfo(
                            name=font_name,
                            size=span['size'],
                            color=color_hex,
                            is_bold=is_bold,
                            is_italic=is_italic
                        )
                        
                        text_span = TextSpan(
                            id=span_id,
                            text=span['text'],
                            font=font_info,
                            bbox=span['bbox']
                        )
                        text_block.spans.append(text_span)
                
                if text_block.spans:
                    page_obj.text_blocks.append(text_block)

            pages.append(page_obj)

        doc.close()
        self.logger.info(f"Analyse terminée. {len(pages)} pages converties en DOM.")
        return pages
