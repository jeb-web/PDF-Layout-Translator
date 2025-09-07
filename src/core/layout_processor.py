#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** VERSION FINALE ET STABILISÉE v2.6 - MISE EN PAGE DYNAMIQUE ***
"""
import logging
import re
from typing import List
import fitz
import copy
from core.data_model import PageObject
from utils.font_manager import FontManager

class LayoutProcessor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager

    def _get_text_width(self, text: str, font_name: str, font_size: float) -> float:
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if font_path and font_path.exists():
            try:
                font_buffer = font_path.read_bytes()
                font = fitz.Font(fontbuffer=font_buffer)
                return font.text_length(text, fontsize=font_size)
            except Exception as e:
                self.debug_logger.error(f"Erreur de mesure Fitz pour la police {font_path}: {e}")
        return len(text) * font_size * 0.6

    def process_pages(self, pages: List[PageObject]) -> List[PageObject]:
        self.debug_logger.info("--- DÉMARRAGE LAYOUTPROCESSOR (v2.6 - Mise en Page Dynamique) ---")
        for page in pages:
            self.debug_logger.info(f"  > Traitement de la Page {page.page_number}")
            for block in page.text_blocks:
                self.debug_logger.info(f"    -> Calcul du reflow pour le bloc {block.id}")
                
                all_new_spans_for_block = []
                current_y = block.bbox[1]
                
                for para in block.paragraphs:
                    self.debug_logger.info(f"       - Traitement du paragraphe {para.id} (Liste: {para.is_list_item})")
                    if not para.spans:
                        continue

                    spans_to_process = list(para.spans)
                    all_words_info = []

                    if para.is_list_item and spans_to_process:
                        first_span = spans_to_process.pop(0)
                        match = re.match(r'^(\s*[•\-–]\s*|\s*\d+\.?\s*)', first_span.text)
                        if match:
                            marker_end_pos = match.end()
                            marker_text = first_span.text[:marker_end_pos]
                            content_text = first_span.text[marker_end_pos:]
                            
                            all_words_info.append((marker_text, first_span, 'marker'))
                            
                            if content_text:
                                all_words_info.extend([(word, first_span, 'content') for word in content_text.split(' ') if word])
                    
                    for span in spans_to_process:
                        if span.text:
                            all_words_info.extend([(word, span, 'content') for word in span.text.split(' ') if word])
                    
                    # --- DÉBUT DE LA LOGIQUE DE MISE EN PAGE DYNAMIQUE (v2.6) ---
                    full_para_text_for_measure = " ".join([word for word, span, word_type in all_words_info])
                    ideal_width = 0
                    if para.spans:
                        representative_span = para.spans[0]
                        ideal_width = self._get_text_width(full_para_text_for_measure, representative_span.font.name, representative_span.font.size)

                    original_block_width = block.bbox[2] - block.bbox[0]
                    max_available_width = block.available_width if block.available_width > 5 else original_block_width

                    self.debug_logger.info(f"         [Layout v2.6] Largeur originale={original_block_width:.1f}, "
                                           f"Largeur traduite idéale={ideal_width:.1f}, "
                                           f"Largeur max disponible={max_available_width:.1f}")

                    block_width_for_reflow = original_block_width
                    if ideal_width > original_block_width:
                        if ideal_width <= (max_available_width + 1.0): # Ajout d'une petite tolérance
                            block_width_for_reflow = ideal_width
                            self.debug_logger.info(f"         [Layout Decision] DÉCISION : Expansion de la boîte à {block_width_for_reflow:.1f}px.")
                        else:
                            block_width_for_reflow = max_available_width
                            self.debug_logger.warning(f"         [Layout Decision] Expansion impossible ({ideal_width:.1f} > {max_available_width:.1f}). DÉCISION : Retour à la ligne forcé.")
                    else:
                        self.debug_logger.info("         [Layout Decision] Le texte tient dans la boîte originale. Pas de changement.")
                    # --- FIN DE LA LOGIQUE DE MISE EN PAGE DYNAMIQUE ---

                    x_start = block.bbox[0]
                    block_width = block_width_for_reflow
                    current_x = x_start
                    x_text_start = x_start
                    max_font_size_in_line = para.spans[0].font.size if para.spans else 10.0
                    
                    is_first_word_of_line = True
                    for i, (word, span, word_type) in enumerate(all_words_info):
                        is_last_word = (i == len(all_words_info) - 1)
                        word_with_space = word if is_last_word and word_type == 'marker' else word + ' '
                        
                        if '\n' in word_with_space:
                            current_y += max_font_size_in_line * 1.2
                            current_x = x_text_start
                            is_first_word_of_line = True
                            continue

                        if word_type == 'marker':
                            x_text_start = para.text_indent
                            current_x = x_start
                        elif is_first_word_of_line:
                            current_x = x_text_start

                        word_width = self._get_text_width(word_with_space, span.font.name, span.font.size)
                        line_height = span.font.size * 1.2
                        
                        if current_x + word_width > x_start + block_width and not is_first_word_of_line:
                            current_y += max_font_size_in_line * 1.2
                            current_x = x_text_start
                            max_font_size_in_line = span.font.size
                            is_first_word_of_line = True

                        if span.font.size > max_font_size_in_line:
                            max_font_size_in_line = span.font.size
                        
                        new_span = copy.deepcopy(span)
                        new_span.text = word_with_space
                        new_span.final_bbox = (current_x, current_y, current_x + word_width, current_y + line_height)
                        all_new_spans_for_block.append(new_span)
                        
                        current_x += word_width
                        is_first_word_of_line = False
                    
                    current_y += max_font_size_in_line * 1.2

                block.spans = all_new_spans_for_block
                final_height = (current_y - block.bbox[1]) if all_new_spans_for_block else 0
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + final_height)

        self.debug_logger.info("--- FIN LAYOUTPROCESSOR ---")
        return pages
