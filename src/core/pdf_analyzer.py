#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Analyseur de PDF
*** VERSION AVEC CORRECTION DE LA LOGIQUE DE FUSION SÉMANTIQUE ***
"""
import logging
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any
import fitz
import copy
from core.data_model import PageObject, TextBlock, TextSpan, FontInfo, Paragraph

class PDFAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')

    def _normalize_font_name(self, font_name: str) -> str:
        return re.sub(r"^[A-Z]{6}\+", "", font_name)

    def _get_logical_reading_order(self, blocks: List[TextBlock], page_width: float) -> List[TextBlock]:
        # ... (cette méthode reste inchangée)
        if not blocks:
            return []

        wide_blocks = []
        normal_blocks = []
        for block in blocks:
            block_width = block.bbox[2] - block.bbox[0]
            if block_width > (page_width * 0.60):
                wide_blocks.append(block)
            else:
                normal_blocks.append(block)

        if not normal_blocks:
            wide_blocks.sort(key=lambda b: b.bbox[1])
            return wide_blocks

        columns: List[Tuple[float, float, List[TextBlock]]] = []
        sorted_normal_blocks_by_x = sorted(normal_blocks, key=lambda b: b.bbox[0])

        for block in sorted_normal_blocks_by_x:
            block_center_x = (block.bbox[0] + block.bbox[2]) / 2
            found_column = False
            tolerance = page_width * 0.05
            for i, (col_x1, col_x2, col_blocks) in enumerate(columns):
                if (col_x1 - tolerance) <= block_center_x <= (col_x2 + tolerance):
                    col_blocks.append(block)
                    new_x1 = min(col_x1, block.bbox[0])
                    new_x2 = max(col_x2, block.bbox[2])
                    columns[i] = (new_x1, new_x2, col_blocks)
                    found_column = True
                    break
            
            if not found_column:
                columns.append((block.bbox[0], block.bbox[2], [block]))

        columns.sort(key=lambda c: c[0])
        for _, _, col_blocks in columns:
            col_blocks.sort(key=lambda b: b.bbox[1])

        sorted_blocks = [block for _, _, col_blocks in columns for block in col_blocks]

        if wide_blocks:
            final_list = []
            wide_blocks.sort(key=lambda b: b.bbox[1])
            
            wide_idx, sorted_idx = 0, 0
            while wide_idx < len(wide_blocks) and sorted_idx < len(sorted_blocks):
                if wide_blocks[wide_idx].bbox[1] < sorted_blocks[sorted_idx].bbox[1]:
                    final_list.append(wide_blocks[wide_idx])
                    wide_idx += 1
                else:
                    final_list.append(sorted_blocks[sorted_idx])
                    sorted_idx += 1
            
            final_list.extend(wide_blocks[wide_idx:])
            final_list.extend(sorted_blocks[sorted_idx:])
            sorted_blocks = final_list

        return sorted_blocks

    def _should_merge(self, block_a: TextBlock, block_b: TextBlock) -> Tuple[bool, str]:
        # ... (cette méthode reste inchangée)
        if not all([
            block_a.paragraphs, block_a.paragraphs[-1].spans,
            block_b.paragraphs, block_b.paragraphs[0].spans
        ]):
            return False, "Bloc ou paragraphe vide, fusion impossible"
            
        last_span_a = block_a.paragraphs[-1].spans[-1]

        vertical_gap = block_b.bbox[1] - block_a.bbox[3]
        line_height_threshold = last_span_a.font.size * 1.5 
        if vertical_gap >= line_height_threshold:
            return False, f"Écart vertical trop grand ({vertical_gap:.1f} >= {line_height_threshold:.1f})"

        horizontal_alignment_gap = abs(block_a.bbox[0] - block_b.bbox[0])
        if horizontal_alignment_gap > 25.0:
            return False, f"Désalignement de colonne significatif ({horizontal_alignment_gap:.1f} > 25.0)"

        last_line_text_a = "".join(s.text for s in block_a.paragraphs[-1].spans).strip()
        first_span_text_b = block_b.paragraphs[0].spans[0].text.strip()

        if last_line_text_a.endswith(('.', '!', '?')):
             return False, "Le bloc A se termine par une ponctuation finale."

        if first_span_text_b and first_span_text_b[0].isupper():
            if not last_line_text_a.endswith((',', ';', ':')):
                return False, "Le bloc B commence par une majuscule, suggérant une nouvelle phrase."

        return True, "Règles de fusion équilibrées respectées"

    def _unify_text_blocks(self, blocks: List[TextBlock]) -> List[TextBlock]:
        # ... (cette méthode reste inchangée)
        if not blocks: return []

        self.debug_logger.info("    > Démarrage de la phase d'unification des blocs...")
        unified_blocks = []
        current_block = copy.deepcopy(blocks[0])

        for next_block in blocks[1:]:
            should_merge, reason = self._should_merge(current_block, next_block)
            if should_merge:
                last_paragraph = current_block.paragraphs[-1]
                for para in next_block.paragraphs:
                    last_paragraph.spans.extend(para.spans)
                
                current_block.bbox = (min(current_block.bbox[0], next_block.bbox[0]), min(current_block.bbox[1], next_block.bbox[1]), max(current_block.bbox[2], next_block.bbox[2]), max(current_block.bbox[3], next_block.bbox[3]))
                self.debug_logger.info(f"      - Fusion du bloc {next_block.id} dans {current_block.id}. Raison: {reason}")
            else:
                self.debug_logger.info(f"      - Finalisation du bloc unifié {current_block.id}. Raison de la rupture: {reason}")
                unified_blocks.append(current_block)
                current_block = copy.deepcopy(next_block)
        
        unified_blocks.append(current_block)
        self.debug_logger.info(f"    > Unification terminée. Nombre de blocs: {len(blocks)} -> {len(unified_blocks)}")
        return unified_blocks

    def apply_grouping_instructions(self, raw_pages: List[PageObject], instructions: Dict[str, Any]) -> List[PageObject]:
        """
        Applique les instructions de regroupement de l'IA pour fusionner les TextBlocks.
        C'est le constructeur déterministe du "fichier 1".
        """
        self.debug_logger.info("--- Application des instructions de regroupement sémantique de l'IA ---")
        
        # Créer une copie profonde pour travailler dessus sans modifier l'original
        working_pages = copy.deepcopy(raw_pages)

        all_blocks_map: Dict[str, TextBlock] = {
            block.id: block for page in working_pages for block in page.text_blocks
        }
        
        merged_block_ids = set()

        grouping_list = instructions.get("grouping_instructions", [])
        for group in grouping_list:
            ids_to_merge = group.get("ids_to_merge", [])
            if not ids_to_merge or len(ids_to_merge) < 2:
                continue

            primary_block_id = ids_to_merge[0]
            if primary_block_id not in all_blocks_map:
                self.debug_logger.warning(f"ID de bloc principal non trouvé : {primary_block_id}")
                continue
                
            primary_block = all_blocks_map[primary_block_id]
            self.debug_logger.info(f"  > Fusion dans le bloc {primary_block_id}. Raison: {group.get('reason', 'N/A')}")

            for block_id_to_merge in ids_to_merge[1:]:
                if block_id_to_merge not in all_blocks_map:
                    self.debug_logger.warning(f"ID de bloc à fusionner non trouvé : {block_id_to_merge}")
                    continue

                block_to_merge = all_blocks_map[block_id_to_merge]
                
                # --- CORRECTION CRUCIALE ---
                # Au lieu d'ajouter des objets Paragraph, on fusionne leur contenu (spans).
                if primary_block.paragraphs and block_to_merge.paragraphs:
                    last_para_in_primary = primary_block.paragraphs[-1]
                    for para_to_merge in block_to_merge.paragraphs:
                        last_para_in_primary.spans.extend(para_to_merge.spans)
                elif block_to_merge.paragraphs:
                    primary_block.paragraphs.extend(block_to_merge.paragraphs)
                # --- FIN DE LA CORRECTION ---
                
                px0, py0, px2, py2 = primary_block.bbox
                mx0, my0, mx2, my2 = block_to_merge.bbox
                primary_block.bbox = (min(px0, mx0), min(py0, my0), max(px2, mx2), max(py2, my2))
                
                merged_block_ids.add(block_id_to_merge)
                self.debug_logger.info(f"    - Bloc {block_id_to_merge} fusionné.")

        semantically_grouped_pages: List[PageObject] = []
        for page in working_pages:
            grouped_page = PageObject(page_number=page.page_number, dimensions=page.dimensions)
            
            grouped_page.text_blocks = [
                block for block in page.text_blocks if block.id not in merged_block_ids
            ]
            
            grouped_page.text_blocks.sort(key=lambda b: b.bbox[1])
            semantically_grouped_pages.append(grouped_page)

        self.debug_logger.info("--- Fin de l'application des instructions de regroupement. ---")
        return semantically_grouped_pages

    def analyze_pdf(self, pdf_path: Path) -> List[PageObject]:
        # ... (cette méthode reste inchangée)
        self.logger.info(f"Début de l'analyse architecturale (logique hiérarchique simplifiée) de {pdf_path}")
        doc = fitz.open(pdf_path)
        pages = []

        for page_num, page in enumerate(doc):
            page_dimensions = (page.rect.width, page.rect.height)
            page_obj = PageObject(page_number=page_num + 1, dimensions=page_dimensions)
            blocks_data = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]
            
            raw_text_blocks = []
            block_counter = 0
            for block_data in [b for b in blocks_data if b['type'] == 0]:
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
                        
                        next_line_text = next_line['spans'][0].text.strip()
                        
                        line_height = line['bbox'][3] - line['bbox'][1] or 10
                        vertical_gap = next_line['bbox'][1] - line['bbox'][3]
                        if vertical_gap > line_height * 0.4:
                            force_break = True
                            reason = f"Écart vertical large ({vertical_gap:.1f})"

                        if not force_break:
                            current_text = "".join(s.text for s in line['spans']).strip()
                            is_title_style = current_text.isupper() and all(s.font.is_bold for s in line['spans'])
                            is_next_line_body = not next_line['spans'][0].font.is_bold
                            
                            if is_title_style and is_next_line_body:
                                force_break = True
                                reason = "Titre détecté (MAJUSCULES/Gras -> Normal)"

                        if not force_break:
                            if next_line_text.startswith(('•', '-', '–')) or re.match(r'^\s*\d+\.\s', next_line_text):
                                force_break = True
                                reason = "Nouvel item de liste explicite"
                    
                    if is_last_line_of_block or force_break:
                        if current_paragraph_spans:
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

            logically_sorted_blocks = self._get_logical_reading_order(raw_text_blocks, page.rect.width)
            page_obj.text_blocks = self._unify_text_blocks(logically_sorted_blocks)
            
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

    def analyze_pdf_raw_blocks(self, pdf_path: Path) -> List[PageObject]:
        # ... (cette méthode reste inchangée)
        self.logger.info(f"Début de l'analyse architecturale BRUTE de {pdf_path}")
        doc = fitz.open(pdf_path)
        pages = []

        for page_num, page in enumerate(doc):
            page_dimensions = (page.rect.width, page.rect.height)
            page_obj = PageObject(page_number=page_num + 1, dimensions=page_dimensions)
            blocks_data = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)["blocks"]
            
            raw_text_blocks = []
            block_counter = 0
            for block_data in [b for b in blocks_data if b['type'] == 0]:
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
                
                temp_paragraphs = []
                para_counter = 1
                for line_key in sorted(lines.keys()):
                    line_spans = lines[line_key]['spans']
                    if line_spans:
                        para_id = f"{block_id}_P{para_counter}"
                        paragraph = Paragraph(id=para_id, spans=list(line_spans))
                        temp_paragraphs.append(paragraph)
                        para_counter += 1
                
                text_block.paragraphs = temp_paragraphs
                if text_block.paragraphs:
                    raw_text_blocks.append(text_block)

            page_obj.text_blocks = raw_text_blocks
            pages.append(page_obj)
            
        doc.close()
        return pages
