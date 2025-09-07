#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** NOUVELLE VERSION v2.5 - LOGIQUE DE TRAITEMENT FIABILISÉE ***
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
        # ... (inchangé) ...
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
        self.debug_logger.info("--- DÉMARRAGE LAYOUTPROCESSOR (v2.5 - Logique fiabilisée) ---")
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

                    x_start = block.bbox[0]
                    block_width = block.bbox[2] - x_start
                    current_x = x_start
                    x_text_start = x_start
                    max_font_size_in_line = para.spans[0].font.size
                    
                    spans_to_process = list(para.spans)
                    
                    # --- NOUVELLE LOGIQUE DE PRÉPARATION ---
                    # On prépare une liste unique de tous les mots à traiter pour ce paragraphe.
                    all_words_info = []

                    if para.is_list_item and spans_to_process:
                        first_span = spans_to_process.pop(0) # On retire le premier span
                        match = re.match(r'^(\s*[•\-–]\s*|\s*\d+\.?\s*)', first_span.text)
                        if match:
                            marker_end_pos = match.end()
                            marker_text = first_span.text[:marker_end_pos]
                            content_text = first_span.text[marker_end_pos:]
                            
                            self.debug_logger.info(f"         > Logique de liste appliquée. Marqueur: '{marker_text.strip()}'")
                            
                            # Ajouter le marqueur à la liste des mots (avec un flag spécial)
                            all_words_info.append((marker_text, first_span, 'marker'))
                            
                            # Ajouter le reste du texte du premier span
                            if content_text:
                                all_words_info.extend([(word, first_span, 'content') for word in content_text.split(' ') if word])
                    
                    # Ajouter les mots des spans restants
                    for span in spans_to_process:
                        if span.text:
                            all_words_info.extend([(word, span, 'content') for word in span.text.split(' ') if word])

                    # --- BOUCLE DE MISE EN PAGE UNIQUE ET FIABLE ---
                    is_first_word_of_line = True
                    for i, (word, span, word_type) in enumerate(all_words_info):
                        is_last_word = (i == len(all_words_info) - 1)
                        word_with_space = word if is_last_word else word + ' '
                        
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
                        
                        self.debug_logger.info(f"           > Mot '{word}' ({word_type}) positionné à bbox: {tuple(f'{c:.2f}' for c in new_span.final_bbox)}")
                        
                        current_x += word_width
                        is_first_word_of_line = False

                    current_y += max_font_size_in_line * 1.2

                block.spans = all_new_spans_for_block
                final_height = (current_y - block.bbox[1]) if all_new_spans_for_block else 0
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + final_height)
                self.debug_logger.info(f"    <- Fin du bloc {block.id}. Nouvelle hauteur: {final_height:.2f}px.")

        self.debug_logger.info("--- FIN LAYOUTPROCESSOR ---")
        return pages
