#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** NOUVELLE VERSION v2.1 - GESTION DES SAUTS DE LIGNE EXPLICITES ***
"""
import logging
from typing import List
import fitz
import copy
from core.data_model import PageObject, TextSpan
from utils.font_manager import FontManager

class LayoutProcessor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager

    def _get_text_width(self, text: str, font_name: str, font_size: float) -> float:
        # ... (cette méthode reste inchangée)
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
        self.debug_logger.info("--- DÉMARRAGE LAYOUTPROCESSOR (v2.1 - Gestion des Newlines) ---")
        for page in pages:
            self.debug_logger.info(f"  > Traitement de la Page {page.page_number}")
            for block in page.text_blocks:
                self.debug_logger.info(f"    -> Calcul du reflow pour le bloc {block.id}")
                
                original_width = block.bbox[2] - block.bbox[0]
                if original_width <= 0 or not block.spans:
                    self.debug_logger.warning(f"       ! Bloc {block.id} ignoré (largeur nulle ou pas de spans).")
                    block.final_bbox = block.bbox
                    continue

                x_start, y_start = block.bbox[0], block.bbox[1]
                current_x, current_y = x_start, y_start
                max_font_size_in_line = block.spans[0].font.size if block.spans else 10.0
                
                new_spans_for_block = []
                
                all_words = []
                for span in block.spans:
                    if span.text:
                        # --- CORRECTION : Remplacer \n par un marqueur pour le traiter séparément ---
                        text_with_markers = span.text.replace('\n', ' <LINE_BREAK> ')
                        words = text_with_markers.split(' ')
                        for word in words:
                            # On ajoute le mot et le span d'origine pour conserver le style
                            all_words.append((word, span))

                for word, span in all_words:
                    if not word:
                        continue
                    
                    # --- CORRECTION : Gérer le marqueur de saut de ligne ---
                    if word == '<LINE_BREAK>':
                        self.debug_logger.info("         * Saut de ligne explicite (\\n) détecté.")
                        current_y += max_font_size_in_line * 1.2
                        current_x = x_start
                        max_font_size_in_line = span.font.size
                        continue

                    word_with_space = word + ' '
                    word_width = self._get_text_width(word_with_space, span.font.name, span.font.size)
                    line_height = span.font.size * 1.2
                    
                    if current_x + word_width > x_start + original_width and current_x > x_start:
                        self.debug_logger.info(f"         ! Saut de ligne: '{word}' dépasse.")
                        current_y += max_font_size_in_line * 1.2
                        current_x = x_start
                        max_font_size_in_line = span.font.size

                    if span.font.size > max_font_size_in_line:
                        max_font_size_in_line = span.font.size

                    new_span = copy.deepcopy(span)
                    new_span.text = word_with_space
                    new_span.final_bbox = (current_x, current_y, current_x + word_width, current_y + line_height)
                    new_spans_for_block.append(new_span)
                    
                    self.debug_logger.info(f"           > Mot '{word}' positionné à bbox: {tuple(f'{c:.2f}' for c in new_span.final_bbox)}")
                    current_x += word_width

                block.spans = new_spans_for_block
                
                final_height = (current_y + max_font_size_in_line * 1.2) - y_start if new_spans_for_block else 0
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + final_height)
                self.debug_logger.info(f"    <- Fin du bloc {block.id}. Nouvelle hauteur: {final_height:.2f}px.")

        self.debug_logger.info("--- FIN LAYOUTPROCESSOR ---")
        return pages
