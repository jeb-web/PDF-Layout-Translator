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
from core.data_model import PageObject, TextBlock, TextSpan, FontInfo, Paragraph

class PDFAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _normalize_font_name(self, font_name: str) -> str:
        return re.sub(r"^[A-Z]{6}\+", "", font_name)

    def analyze_pdf(self, pdf_path: Path) -> List[PageObject]:
        self.logger.info(f"Début de l'analyse architecturale (Jalon 1 Corrigé) de {pdf_path}")
        doc = fitz.open(pdf_path)
        pages = []

        for page_num, page in enumerate(doc):
            # --- CORRECTION DE LA FAUTE DE FRAPPE ---
            # L'objet Rect n'a pas d'attribut 'size', mais 'width' et 'height'.
            page_dimensions = (page.rect.width, page.rect.height)
            page_obj = PageObject(page_number=page_num + 1, dimensions=page_dimensions)
            # ------------------------------------
            
            blocks_data = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]
            
            block_counter = 0
            for block_data in sorted([b for b in blocks_data if b['type'] == 0], key=lambda b: (b['bbox'][1], b['bbox'][0])):
                block_counter += 1
                block_id = f"P{page_num+1}_B{block_counter}"
                
                text_block = TextBlock(id=block_id, bbox=block_data['bbox'])
                
                # Étape A: Extraire tous les spans et les regrouper en lignes visuelles
                lines = {}
                span_counter = 0
                for line_data in block_data.get('lines', []):
                    line_key = round(line_data['bbox'][1], 1)
                    if line_key not in lines:
                        lines[line_key] = {'spans': [], 'bbox': line_data['bbox']}
                    
                    for span_data in sorted(line_data.get('spans', []), key=lambda s: s['bbox'][0]):
                        span_counter += 1
                        span_id = f"{block_id}_S{span_counter}"
                        font_name = self._normalize_font_name(span_data['font'])
                        font_info = FontInfo(
                            name=font_name, size=span_data['size'],
                            color=f"#{span_data['color']:06x}",
                            is_bold="bold" in font_name.lower() or "black" in font_name.lower(),
                            is_italic="italic" in font_name.lower()
                        )
                        
                        span_text = span_data['text']
                        if lines[line_key]['spans'] and span_data['bbox'][0] > (lines[line_key]['spans'][-1].bbox[2] + 1):
                            span_text = " " + span_text

                        new_span = TextSpan(id=span_id, text=span_text, font=font_info, bbox=span_data['bbox'])
                        lines[line_key]['spans'].append(new_span)

                # Étape B: Segmenter les lignes en paragraphes en se basant sur l'espacement vertical
                if not lines:
                    continue

                sorted_line_keys = sorted(lines.keys())
                
                current_paragraph_spans = []
                para_counter = 1

                for i, key in enumerate(sorted_line_keys):
                    current_paragraph_spans.extend(lines[key]['spans'])
                    
                    is_last_line_of_block = (i == len(sorted_line_keys) - 1)
                    
                    if is_last_line_of_block:
                        if current_paragraph_spans:
                            para_id = f"{block_id}_P{para_counter}"
                            text_block.paragraphs.append(Paragraph(id=para_id, spans=current_paragraph_spans))
                    else:
                        current_line_bbox = lines[key]['bbox']
                        next_line_bbox = lines[sorted_line_keys[i+1]]['bbox']
                        
                        line_height = current_line_bbox[3] - current_line_bbox[1]
                        if line_height <= 0: line_height = 10 # Fallback pour les lignes de hauteur nulle
                        
                        vertical_gap = next_line_bbox[1] - current_line_bbox[3]
                        
                        if vertical_gap > line_height * 0.4:
                            if current_paragraph_spans:
                                para_id = f"{block_id}_P{para_counter}"
                                text_block.paragraphs.append(Paragraph(id=para_id, spans=current_paragraph_spans))
                                para_counter += 1
                                current_paragraph_spans = []
                
                text_block.spans = [span for para in text_block.paragraphs for span in para.spans]

                if text_block.paragraphs:
                    page_obj.text_blocks.append(text_block)

            pages.append(page_obj)

        doc.close()
        return pages
