#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Analyseur de PDF
*** VERSION FINALE ET STABILISÉE v1.6 - ANALYSE HEURISTIQUE AVANCÉE ***
"""
import logging
import re
from pathlib import Path
from typing import List
import fitz
import copy
from core.data_model import PageObject, TextBlock, TextSpan, FontInfo, Paragraph

class PDFAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')

    def _normalize_font_name(self, font_name: str) -> str:
        return re.sub(r"^[A-Z]{6}\+", "", font_name)

    def analyze_pdf(self, pdf_path: Path) -> List[PageObject]:
        self.logger.info(f"Début de l'analyse architecturale (v1.6 - Heuristique Avancée) de {pdf_path}")
        doc = fitz.open(pdf_path)
        pages = []

        for page_num, page in enumerate(doc):
            page_dimensions = (page.rect.width, page.rect.height)
            page_obj = PageObject(page_number=page_num + 1, dimensions=page_dimensions)
            
            blocks_data = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]
            
            block_counter = 0
            for block_data in sorted([b for b in blocks_data if b['type'] == 0], key=lambda b: (b['bbox'][1], b['bbox'][0])):
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
                        # On préserve les espaces en début de span pour une analyse plus fine
                        if lines[line_key]['spans'] and not lines[line_key]['spans'][-1].text.endswith(' '):
                           if span_data['bbox'][0] > (lines[line_key]['spans'][-1].bbox[2] + 0.5):
                                lines[line_key]['spans'][-1].text += " "

                        new_span = TextSpan(id=span_id, text=span_text, font=font_info, bbox=span_data['bbox'])
                        lines[line_key]['spans'].append(new_span)

                if not lines: continue
                sorted_lines = [lines[key] for key in sorted(lines.keys())]
                
                current_paragraph_spans = []
                para_counter = 1
                for i, line in enumerate(sorted_lines):
                    if not line['spans']: continue
                    
                    current_paragraph_spans.extend(line['spans'])
                    
                    # --- DÉBUT DE LA LOGIQUE HEURISTIQUE AVANCÉE (v2.4) ---
                    force_break = False
                    reason = ""
                    
                    is_last_line_of_block = (i == len(sorted_lines) - 1)
                    
                    if not is_last_line_of_block:
                        next_line = sorted_lines[i+1]
                        if not next_line['spans']: continue
                        
                        # Règle 1: Détection de Marqueurs de Liste
                        next_starts_with_bullet = next_line['spans'][0].text.strip().startswith(('•', '-', '–'))
                        next_starts_with_number = re.match(r'^\s*\d+\.?', next_line['spans'][0].text.strip())
                        if next_starts_with_bullet or next_starts_with_number:
                            force_break = True
                            reason = "Nouvel item de liste"
                        
                        # Règle 2: Détection par Écart Vertical
                        if not force_break:
                            line_height = line['bbox'][3] - line['bbox'][1]
                            if line_height <= 0: line_height = 10 
                            vertical_gap = next_line['bbox'][1] - line['bbox'][3]
                            if vertical_gap > line_height * 0.4:
                                force_break = True
                                reason = f"Écart vertical large ({vertical_gap:.1f} > {line_height * 0.4:.1f})"

                        # Règle 3: Détection par Changement de Style (simplifiée)
                        if not force_break:
                            last_span_style = current_paragraph_spans[-1].font
                            next_span_style = next_line['spans'][0].font
                            if last_span_style.name != next_span_style.name or abs(last_span_style.size - next_span_style.size) > 0.5:
                                force_break = True
                                reason = "Changement de police/taille"
                        
                        # Règle 4: Détection par Ponctuation Finale
                        if not force_break:
                            full_line_text = "".join(s.text for s in line['spans']).strip()
                            if full_line_text.endswith(('.', '!', '?', ':')):
                                force_break = True
                                reason = "Ponctuation de fin de ligne"
                    
                    if force_break:
                        self.debug_logger.info(f"    - Paragraphe P{para_counter} terminé. Raison: {reason}.")
                    # --- FIN DE LA LOGIQUE HEURISTIQUE ---

                    if is_last_line_of_block or force_break:
                        if current_paragraph_spans:
                            para_id = f"{block_id}_P{para_counter}"
                            paragraph = Paragraph(id=para_id, spans=list(current_paragraph_spans))
                            
                            # Logique de gestion des listes à puces (inchangée)
                            if paragraph.spans:
                                first_span = paragraph.spans[0]
                                match = re.match(r'^(\s*[•\-–]\s*|\s*\d+\.?\s*)', first_span.text)
                                if match:
                                    paragraph.is_list_item = True
                                    marker_end_pos = match.end()
                                    marker_text = first_span.text[:marker_end_pos]
                                    content_text = first_span.text[marker_end_pos:]
                                    
                                    paragraph.list_marker_text = marker_text.strip()
                                    first_span.text = marker_text
                                    
                                    if content_text.strip():
                                        new_span = copy.deepcopy(first_span)
                                        new_span.id = f"{first_span.id}_cont"
                                        new_span.text = content_text
                                        
                                        marker_width_ratio = len(marker_text) / len(first_span.text) if len(first_span.text) > 0 else 0.5
                                        marker_width = (first_span.bbox[2] - first_span.bbox[0]) * marker_width_ratio
                                        
                                        new_bbox = list(first_span.bbox)
                                        new_bbox[0] = first_span.bbox[0] + marker_width
                                        new_span.bbox = tuple(new_bbox)
                                        paragraph.spans.insert(1, new_span)
                                    
                                    if len(paragraph.spans) > 1:
                                        paragraph.text_indent = paragraph.spans[1].bbox[0]
                                    else:
                                        paragraph.text_indent = first_span.bbox[0] + (first_span.font.size * 2)

                            text_block.paragraphs.append(paragraph)
                            para_counter += 1
                            current_paragraph_spans.clear()
                
                text_block.spans = [span for para in text_block.paragraphs for span in para.spans]
                if text_block.paragraphs:
                    page_obj.text_blocks.append(text_block)

            # Analyse Spatiale Contextuelle (inchangée)
            self.debug_logger.info(f"  > Démarrage de l'analyse spatiale pour la page {page_num + 1}")
            for i, block in enumerate(page_obj.text_blocks):
                right_boundary = page_dimensions[0]
                closest_neighbor_x = right_boundary
                
                for j, other_block in enumerate(page_obj.text_blocks):
                    if i == j: continue
                        
                    if other_block.bbox[0] >= block.bbox[2]:
                        current_top, current_bottom = block.bbox[1], block.bbox[3]
                        other_top, other_bottom = other_block.bbox[1], other_block.bbox[3]
                        
                        if max(current_top, other_top) < min(current_bottom, other_bottom):
                            closest_neighbor_x = min(closest_neighbor_x, other_block.bbox[0])

                block.available_width = closest_neighbor_x - block.bbox[0]
                
                original_width = block.bbox[2] - block.bbox[0]
                self.debug_logger.info(f"    - Bloc {block.id}: Largeur originale={original_width:.1f}, "
                                       f"Largeur max disponible={block.available_width:.1f} "
                                       f"(limité par {'voisin' if closest_neighbor_x != right_boundary else 'marge'})")

            pages.append(page_obj)
        doc.close()
        return pages
