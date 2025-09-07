#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Analyseur de PDF
*** VERSION 2.1 - ALGORITHME D'UNIFICATION ITÉRATIF ***
"""
import logging
import re
from pathlib import Path
from typing import List, Tuple
import fitz
import copy
from core.data_model import PageObject, TextBlock, TextSpan, FontInfo, Paragraph

class PDFAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')

    def _normalize_font_name(self, font_name: str) -> str:
        return re.sub(r"^[A-Z]{6}\+", "", font_name)

    def _should_merge(self, block_a: TextBlock, block_b: TextBlock) -> Tuple[bool, str]:
        if not all([
            block_a.paragraphs,
            block_a.paragraphs[-1].spans,
            block_b.paragraphs,
            block_b.paragraphs[0].spans
        ]):
            return False, "Bloc ou paragraphe vide, fusion impossible"
            
        last_span_a = block_a.paragraphs[-1].spans[-1]
        first_span_b = block_b.paragraphs[0].spans[0]

        vertical_gap = block_b.bbox[1] - block_a.bbox[3]
        line_height_threshold = last_span_a.font.size * 2.5
        if vertical_gap >= line_height_threshold:
            return False, f"Écart vertical trop grand ({vertical_gap:.1f} >= {line_height_threshold:.1f})"

        a_x1, _, a_x2, _ = block_a.bbox
        b_x1, _, b_x2, _ = block_b.bbox
        if (a_x2 < b_x1) or (b_x2 < a_x1):
            return False, f"Pas de chevauchement horizontal (A_x2:{a_x2:.1f} < B_x1:{b_x1:.1f} ou B_x2:{b_x2:.1f} < A_x1:{a_x1:.1f})"
        
        style_a = last_span_a.font
        style_b = first_span_b.font
        
        # On ne fusionne pas si le style change drastiquement (suggérant un titre)
        is_title_change = (style_b.is_bold and not style_a.is_bold) or (style_b.size > style_a.size + 1)
        
        # On ne fusionne pas non plus si la phrase semble terminée et que le style change un peu
        text_a = "".join(s.text for s in block_a.paragraphs[-1].spans).strip()
        ends_with_punctuation = text_a.endswith(('.', '!', '?', ':'))
        
        style_is_different = (style_a.name != style_b.name or abs(style_a.size - style_b.size) > 0.5)

        if is_title_change or (ends_with_punctuation and style_is_different):
             return False, f"Changement de style sémantique (titre ou fin de phrase)"
            
        return True, "Règles de fusion respectées"

    def _unify_text_blocks(self, blocks: List[TextBlock]) -> List[TextBlock]:
        if not blocks: return []
        self.debug_logger.info("    > Démarrage de la phase d'unification des blocs (v2.1 - Itératif)...")
        
        # --- DÉBUT DE LA CORRECTION v2.1 ---
        # Remplacement de l'algorithme à passage unique par un algorithme itératif.
        
        work_list = copy.deepcopy(blocks)
        
        while True:
            merged_in_pass = False
            next_pass_list = []
            
            i = 0
            while i < len(work_list):
                current_block = work_list[i]
                
                # Chercher le meilleur candidat pour la fusion
                best_candidate_index = -1
                min_distance = float('inf')

                for j in range(len(work_list)):
                    if i == j: continue
                    candidate_block = work_list[j]
                    
                    # On ne fusionne que des blocs verticalement proches
                    if candidate_block.bbox[1] > current_block.bbox[3]:
                        should_merge, reason = self._should_merge(current_block, candidate_block)
                        if should_merge:
                            distance = candidate_block.bbox[1] - current_block.bbox[3]
                            if distance < min_distance:
                                min_distance = distance
                                best_candidate_index = j

                if best_candidate_index != -1:
                    merged_in_pass = True
                    candidate_to_merge = work_list.pop(best_candidate_index)
                    
                    self.debug_logger.info(f"      - Fusion du bloc {candidate_to_merge.id} dans {current_block.id}.")
                    
                    current_block.paragraphs.extend(candidate_to_merge.paragraphs)
                    current_block.bbox = (
                        min(current_block.bbox[0], candidate_to_merge.bbox[0]),
                        min(current_block.bbox[1], candidate_to_merge.bbox[1]),
                        max(current_block.bbox[2], candidate_to_merge.bbox[2]),
                        max(current_block.bbox[3], candidate_to_merge.bbox[3])
                    )
                    # On reste sur le même 'current_block' pour voir s'il peut absorber d'autres blocs
                    continue 
                
                next_pass_list.append(current_block)
                i += 1
            
            work_list = next_pass_list
            if not merged_in_pass:
                break # Aucune fusion n'a eu lieu pendant toute la passe, le processus est stable.

        self.debug_logger.info(f"    > Unification terminée. Nombre de blocs: {len(blocks)} -> {len(work_list)}")
        return work_list
        # --- FIN DE LA CORRECTION ---


    def analyze_pdf(self, pdf_path: Path) -> List[PageObject]:
        self.logger.info(f"Début de l'analyse architecturale (v2.1 - Unification Itérative) de {pdf_path}")
        doc = fitz.open(pdf_path)
        pages = []

        for page_num, page in enumerate(doc):
            page_dimensions = (page.rect.width, page.rect.height)
            page_obj = PageObject(page_number=page_num + 1, dimensions=page_dimensions)
            blocks_data = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]
            
            raw_text_blocks = []
            block_counter = 0
            for block_data in sorted([b for b in blocks_data if b['type'] == 0], key=lambda b: (b['bbox'][1], b['bbox'][0])):
                block_counter += 1
                block_id = f"P{page_num+1}_B{block_counter}"
                text_block = TextBlock(id=block_id, bbox=block_data['bbox'])
                
                lines = {}
                span_counter = 0
                for line_data in block_data.get('lines', []):
                    line_key = round(line_data['bbox'][1], 1)
                    if line_key not in lines: lines[line_key] = {'spans': [], 'bbox': line_data['bbox']}
                    for span_data in sorted(line_data.get('spans', []), key=lambda s: s['bbox'][0]):
                        span_counter += 1
                        span_id = f"{block_id}_S{span_counter}"
                        font_name = self._normalize_font_name(span_data['font'])
                        font_info = FontInfo(name=font_name, size=span_data['size'], color=f"#{span_data['color']:06x}", is_bold="bold" in font_name.lower() or "black" in font_name.lower(), is_italic="italic" in font_name.lower())
                        span_text = span_data['text'].replace('\t', '    ')
                        if lines[line_key]['spans'] and not lines[line_key]['spans'][-1].text.endswith(' '):
                           if span_data['bbox'][0] > (lines[line_key]['spans'][-1].bbox[2] + 0.5):
                                lines[line_key]['spans'][-1].text += " "
                        new_span = TextSpan(id=span_id, text=span_text, font=font_info, bbox=span_data['bbox'])
                        lines[line_key]['spans'].append(new_span)
                if not lines: continue
                sorted_lines = [lines[key] for key in sorted(lines.keys())]
                
                current_paragraph_spans = []
                para_counter = 1
                temp_paragraphs = []
                for i, line in enumerate(sorted_lines):
                    if not line['spans']: continue
                    current_paragraph_spans.extend(line['spans'])
                    is_last_line_of_block = (i == len(sorted_lines) - 1)
                    force_break = False
                    reason = ""
                    if not is_last_line_of_block:
                        next_line = sorted_lines[i+1]
                        if not next_line['spans']: continue

                        next_starts_with_bullet = next_line['spans'][0].text.strip().startswith(('•', '-', '–'))
                        next_starts_with_number = re.match(r'^\s*\d+\.?', next_line['spans'][0].text.strip())
                        if next_starts_with_bullet or next_starts_with_number:
                            force_break = True
                            reason = "Nouvel item de liste"
                        
                        if not force_break:
                            line_height = line['bbox'][3] - line['bbox'][1]
                            if line_height <= 0: line_height = 10 
                            vertical_gap = next_line['bbox'][1] - line['bbox'][3]
                            if vertical_gap > line_height * 0.4:
                                force_break = True
                                reason = f"Écart vertical large ({vertical_gap:.1f} > {line_height * 0.4:.1f})"

                        if not force_break:
                            last_span_style = current_paragraph_spans[-1].font
                            next_span_style = next_line['spans'][0].font
                            style_changed = (last_span_style.name != next_span_style.name or 
                                             abs(last_span_style.size - next_span_style.size) > 0.1)
                            
                            next_line_text = next_line['spans'][0].text.strip()
                            starts_with_uppercase = next_line_text and next_line_text[0].isupper()

                            if style_changed and starts_with_uppercase:
                                force_break = True
                                reason = "Changement de style et début par majuscule"
                        
                        if not force_break:
                            full_line_text = "".join(s.text for s in line['spans']).strip()
                            next_line_text = "".join(s.text for s in next_line['spans']).strip()
                            
                            ends_with_punctuation = full_line_text.endswith(('.', '!', '?', ':'))
                            next_starts_with_uppercase = next_line_text and next_line_text[0].isupper()

                            if ends_with_punctuation and next_starts_with_uppercase:
                                force_break = True
                                reason = "Ponctuation de fin de phrase + Majuscule"

                    if is_last_line_of_block or force_break:
                        if current_paragraph_spans:
                            self.debug_logger.info(f"        -> Rupture de paragraphe. Raison : {reason if force_break else 'Fin du bloc'}")
                            para_id = f"{block_id}_P{para_counter}"
                            paragraph = Paragraph(id=para_id, spans=list(current_paragraph_spans))
                            temp_paragraphs.append(paragraph)
                            para_counter += 1
                            current_paragraph_spans.clear()
                
                for para in temp_paragraphs:
                    if para.spans:
                        first_span = para.spans[0]
                        match = re.match(r'^(\s*[•\-–]\s*|\s*\d+\.?\s*)', first_span.text)
                        if match:
                            para.is_list_item = True
                            marker_end_pos = match.end()
                            marker_text = first_span.text[:marker_end_pos]
                            content_text = first_span.text[marker_end_pos:]
                            para.list_marker_text = marker_text.strip()
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
                                para.spans.insert(1, new_span)
                            if len(para.spans) > 1:
                                para.text_indent = para.spans[1].bbox[0]
                            else:
                                para.text_indent = first_span.bbox[0] + (first_span.font.size * 2)
                
                text_block.paragraphs = temp_paragraphs
                if text_block.paragraphs:
                    raw_text_blocks.append(text_block)

            page_obj.text_blocks = self._unify_text_blocks(raw_text_blocks)
            
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
        return pages```
