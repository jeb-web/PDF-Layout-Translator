#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Analyseur de PDF
Construit un DOM de la page à partir du fichier PDF.
"""
import logging
import re
from pathlib import Path
from typing import List
import fitz
from core.data_model import PageObject, TextBlock, TextSpan, FontInfo

class PDFAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _normalize_font_name(self, font_name: str) -> str:
        return re.sub(r"^[A-Z]{6}\+", "", font_name)

    def analyze_pdf(self, pdf_path: Path) -> List[PageObject]:
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
                    spans_in_line = line.get('spans', [])
                    for i, span in enumerate(spans_in_line):
                        span_counter += 1
                        span_id = f"{block_id}_S{span_counter}"
                        
                        color_int = span['color']
                        color_hex = f"#{color_int>>16:02x}{(color_int>>8)&0xFF:02x}{color_int&0xFF:02x}"
                        
                        font_name = self._normalize_font_name(span['font'])
                        flags = span['flags']
                        is_bold = "bold" in font_name.lower() or bool(flags & 2**4)
                        is_italic = "italic" in font_name.lower() or bool(flags & 2**1)

                        font_info = FontInfo(name=font_name, size=span['size'], color=color_hex, is_bold=is_bold, is_italic=is_italic)
                        
                        # --- MODIFICATION CLÉ : Détecter le dernier span de la ligne ---
                        is_last_in_line = (i == len(spans_in_line) - 1)
                        
                        text_span = TextSpan(
                            id=span_id, 
                            text=span['text'], 
                            font=font_info, 
                            bbox=span['bbox'],
                            is_last_in_line=is_last_in_line
                        )
                        text_block.spans.append(text_span)
                
                if text_block.spans:
                    page_obj.text_blocks.append(text_block)

            pages.append(page_obj)

        doc.close()
        self.logger.info(f"Analyse terminée. {len(pages)} pages converties en DOM.")
        return pages
