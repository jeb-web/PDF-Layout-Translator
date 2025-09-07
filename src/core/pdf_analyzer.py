#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Analyseur de PDF
*** NOUVELLE VERSION v1.2 - DÉTECTION DE PUCE CORRIGÉE ET ROBUSTE ***
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
        self.logger.info(f"Début de l'analyse architecturale (v1.2 - Détection de puce) de {pdf_path}")
        doc = fitz.open(pdf_path)
        pages = []

        for page_num, page in enumerate(doc):
            # ... (logique de début inchangée) ...
            page_dimensions = (page.rect.width, page.rect.height)
            page_obj = PageObject(page_number=page_num + 1, dimensions=page_dimensions)
            
            blocks_data = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]
            
            block_counter = 0
            for block_data in sorted([b for b in blocks_data if b['type'] == 0], key=lambda b: (b['bbox'][1], b['bbox'][0])):
                # ... (logique de création de spans inchangée) ...
                block_counter += 1
                block_id = f"P{page_num+1}_B{block_counter}"
                
                text_block = TextBlock(id=block_id, bbox=block_data['bbox'])
                
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
                        
                        span_text = span_data['text'].replace('\t', '    ')
                        if lines[line_key]['spans'] and span_data['bbox'][0] > (lines[line_key]['spans'][-1].bbox[2] + 0.5):
                            span_text = " " + span_text

                        new_span = TextSpan(id=span_id, text=span_text, font=font_info, bbox=span_data['bbox'])
                        lines[line_key]['spans'].append(new_span)

                if not lines: continue
                sorted_lines = [lines[key] for key in sorted(lines.keys())]
                
                current_paragraph_spans = []
                para_counter = 1
                for i, line in enumerate(sorted_lines):
                    current_paragraph_spans.extend(line['spans'])
                    
                    is_last_line_of_block = (i == len(sorted_lines) - 1)
                    
                    force_break = False
                    if not is_last_line_of_block:
                        # ... (la logique de détection de fin de paragraphe reste identique) ...
                        next_line = sorted_lines[i+1]
                        next_starts_with_bullet = next_line['spans'][0].text.strip().startswith(('•', '-', '–')) if next_line['spans'] else False
                        next_starts_with_number = re.match(r'^\s*\d+\.?', next_line['spans'][0].text.strip()) is not None if next_line['spans'] else False
                        if next_starts_with_bullet or next_starts_with_number:
                            force_break = True
                        if not force_break:
                            line_height = line['bbox'][3] - line['bbox'][1]
                            if line_height <= 0: line_height = 10 
                            vertical_gap = next_line['bbox'][1] - line['bbox'][3]
                            if vertical_gap > line_height * 0.4:
                                force_break = True
                    
                    if is_last_line_of_block or force_break:
                        if current_paragraph_spans:
                            para_id = f"{block_id}_P{para_counter}"
                            paragraph = Paragraph(id=para_id, spans=current_paragraph_spans)
                            
                            # --- LOGIQUE DE DÉTECTION DE LISTE CORRIGÉE ---
                            if current_paragraph_spans:
                                first_span = current_paragraph_spans[0]
                                # Utiliser une expression régulière pour trouver la puce/numéro au tout début du texte
                                match = re.match(r'^(\s*[•\-–]\s*|\s*\d+\.?\s*)', first_span.text)
                                if match:
                                    paragraph.is_list_item = True
                                    
                                    # Le marqueur est ce que l'expression régulière a capturé
                                    marker_text = match.group(1)
                                    paragraph.list_marker_text = marker_text.strip()
                                    
                                    # Le reste du texte est le contenu
                                    content_text = first_span.text[len(marker_text):]
                                    
                                    # Mettre à jour le premier span pour ne contenir QUE la puce
                                    first_span.text = marker_text

                                    # Créer un nouveau span pour le reste du texte s'il y en a
                                    if content_text:
                                        # Cloner le premier span pour le style, mais ajuster le contenu et la bbox
                                        new_span = copy.deepcopy(first_span)
                                        new_span.id = f"{first_span.id}_cont"
                                        new_span.text = content_text
                                        # On ne peut pas connaître la bbox exacte du nouveau span, mais on peut l'estimer
                                        # Le LayoutProcessor recalculera tout, donc la bbox initiale ici est moins critique.
                                        # On le place juste après la puce.
                                        marker_width = first_span.bbox[2] - first_span.bbox[0]
                                        new_bbox = list(first_span.bbox)
                                        new_bbox[0] += marker_width
                                        new_span.bbox = tuple(new_bbox)
                                        current_paragraph_spans.insert(1, new_span)
                                    
                                    # Définir l'indentation
                                    if len(current_paragraph_spans) > 1:
                                        paragraph.text_indent = current_paragraph_spans[1].bbox[0]
                                    else:
                                        paragraph.text_indent = first_span.bbox[0] + (first_span.font.size * 2)

                            text_block.paragraphs.append(paragraph)
                            para_counter += 1
                            current_paragraph_spans = []

                text_block.spans = [span for para in text_block.paragraphs for span in para.spans]
                if text_block.paragraphs:
                    page_obj.text_blocks.append(text_block)

            pages.append(page_obj)
        doc.close()
        return pages
