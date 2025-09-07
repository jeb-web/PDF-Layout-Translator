#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Analyseur de PDF
*** VERSION FINALE ET STABILISÉE v1.8 - UNIFICATION DES BLOCS CORRIGÉE ***
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
        # Vérification de robustesse
        if not all([block_a.paragraphs, block_a.paragraphs[-1].spans, block_b.paragraphs, block_b.paragraphs[0].spans]):
            return False, "Bloc ou paragraphe vide, fusion impossible"
            
        last_span_a = block_a.paragraphs[-1].spans[-1]
        first_span_b = block_b.paragraphs[0].spans[0]

        # Règle 1: Proximité Verticale
        vertical_gap = block_b.bbox[1] - block_a.bbox[3]
        line_height_threshold = last_span_a.font.size * 1.5
        if vertical_gap >= line_height_threshold:
            return False, f"Écart vertical trop grand ({vertical_gap:.1f} >= {line_height_threshold:.1f})"

        # Règle 2: Alignement Horizontal (assouplie)
        horizontal_gap = abs(last_span_a.bbox[0] - first_span_b.bbox[0])
        if horizontal_gap > 10:
            return False, f"Désalignement horizontal significatif ({horizontal_gap:.1f} > 10)"

        # Règle 3: Cohérence Stylistique (assouplie)
        style_a = last_span_a.font
        style_b = first_span_b.font
        font_name_a = style_a.name.split('-')[0]
        font_name_b = style_b.name.split('-')[0]
        if font_name_a != font_name_b:
            return False, f"Changement de police ({style_a.name} -> {style_b.name})"
        if abs(style_a.size - style_b.size) > 0.5:
            return False, f"Changement de taille ({style_a.size:.1f} -> {style_b.size:.1f})"
            
        return True, "Règles de fusion respectées"

    def _unify_text_blocks(self, blocks: List[TextBlock]) -> List[TextBlock]:
        if not blocks: return []

        self.debug_logger.info("    > Démarrage de la phase d'unification des blocs...")
        unified_blocks = []
        current_block = copy.deepcopy(blocks[0])

        for next_block in blocks[1:]:
            should_merge, reason = self._should_merge(current_block, next_block)
            if should_merge:
                current_block.paragraphs.extend(next_block.paragraphs)
                current_block.bbox = (min(current_block.bbox[0], next_block.bbox[0]), min(current_block.bbox[1], next_block.bbox[1]), max(current_block.bbox[2], next_block.bbox[2]), max(current_block.bbox[3], next_block.bbox[3]))
                self.debug_logger.info(f"      - Fusion du bloc {next_block.id} dans {current_block.id}. Raison: {reason}")
            else:
                self.debug_logger.info(f"      - Finalisation du bloc unifié {current_block.id}. Raison de la rupture: {reason}")
                unified_blocks.append(current_block)
                current_block = copy.deepcopy(next_block)
        
        unified_blocks.append(current_block)
        self.debug_logger.info(f"    > Unification terminée. Nombre de blocs: {len(blocks)} -> {len(unified_blocks)}")
        return unified_blocks

    def analyze_pdf(self, pdf_path: Path) -> List[PageObject]:
        self.logger.info(f"Début de l'analyse architecturale (v1.8 - Unification Robuste) de {pdf_path}")
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
                for i, line in enumerate(sorted_lines):
                    if not line['spans']: continue
                    current_paragraph_spans.extend(line['spans'])
                    is_last_line_of_block = (i == len(sorted_lines) - 1)
                    force_break = False
                    if not is_last_line_of_block:
                        next_line = sorted_lines[i+1]
                        if not next_line['spans']: continue
                        next_starts_with_bullet = next_line['spans'][0].text.strip().startswith(('•', '-', '–'))
                        next_starts_with_number = re.match(r'^\s*\d+\.?', next_line['spans'][0].text.strip())
                        if next_starts_with_bullet or next_starts_with_number: force_break = True
                        if not force_break:
                            line_height = line['bbox'][3] - line['bbox'][1]
                            if line_height <= 0: line_height = 10 
                            vertical_gap = next_line['bbox'][1] - line['bbox'][3]
                            if vertical_gap > line_height * 0.4: force_break = True
                        if not force_break:
                            last_span_style = current_paragraph_spans[-1].font
                            next_span_style = next_line['spans'][0].font
                            if last_span_style.name != next_span_style.name or abs(last_span_style.size - next_span_style.size) > 0.5: force_break = True
                        if not force_break:
                            full_line_text = "".join(s.text for s in line['spans']).strip()
                            if full_line_text.endswith(('.', '!', '?', ':')): force_break = True
                    if is_last_line_of_block or force_break:
                        if current_paragraph_spans:
                            para_id = f"{block_id}_P{para_counter}"
                            paragraph = Paragraph(id=para_id, spans=list(current_paragraph_spans))
                            text_block.paragraphs.append(paragraph)
                            para_counter += 1
                            current_paragraph_spans.clear()
                
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
        return pages
