#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** NOUVELLE VERSION - MOTEUR DE REFLOW AVEC CALCUL DE COORDONNÉES ***
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
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if font_path and font_path.exists():
            try:
                font_buffer = font_path.read_bytes()
                font = fitz.Font(fontbuffer=font_buffer)
                return font.text_length(text, fontsize=font_size)
            except Exception as e:
                self.debug_logger.error(f"Erreur de mesure Fitz pour la police {font_path}: {e}")
        # Fallback si la police n'est pas trouvée
        return len(text) * font_size * 0.6

    def process_pages(self, pages: List[PageObject]) -> List[PageObject]:
        self.debug_logger.info("--- DÉMARRAGE LAYOUTPROCESSOR (v2 - Calcul de Coordonnées) ---")
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
                
                for i, span in enumerate(block.spans):
                    if not span.text or not span.text.strip():
                        continue
                        
                    self.debug_logger.info(f"       - Traitement du span original #{i} (ID: {span.id}) avec texte: '{span.text[:50]}...'")
                    words = span.text.split(' ')
                    
                    for j, word in enumerate(words):
                        if not word:
                            continue

                        # Le dernier mot d'un span n'a pas d'espace après lui
                        word_with_space = word if j == len(words) - 1 else word + ' '
                        word_width = self._get_text_width(word_with_space, span.font.name, span.font.size)
                        
                        line_height = span.font.size * 1.2 # Hauteur de ligne estimée
                        
                        # Si le mot dépasse, on passe à la ligne suivante
                        if current_x + word_width > x_start + original_width and current_x > x_start:
                            self.debug_logger.info(f"         ! Saut de ligne: '{word}' dépasse. current_x={current_x:.2f}, word_width={word_width:.2f}, block_width={original_width:.2f}")
                            current_y += max_font_size_in_line * 1.2
                            current_x = x_start
                            max_font_size_in_line = span.font.size

                        # Mise à jour de la hauteur max de la ligne
                        if span.font.size > max_font_size_in_line:
                            max_font_size_in_line = span.font.size

                        # Créer un nouveau span pour ce mot avec ses coordonnées finales
                        new_span = copy.deepcopy(span)
                        new_span.text = word_with_space
                        # La bbox finale est (x0, y0, x1, y1)
                        new_span.final_bbox = (current_x, current_y, current_x + word_width, current_y + line_height)
                        new_spans_for_block.append(new_span)
                        
                        self.debug_logger.info(f"           > Mot '{word}' positionné à bbox: {tuple(f'{c:.2f}' for c in new_span.final_bbox)}")

                        # Avancer sur la ligne
                        current_x += word_width

                # Remplacer les anciens spans par les nouveaux, positionnés
                block.spans = new_spans_for_block
                
                # Mettre à jour la hauteur finale du bloc
                final_height = (current_y + max_font_size_in_line * 1.2) - y_start
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + final_height)
                self.debug_logger.info(f"    <- Fin du bloc {block.id}. Nouvelle hauteur: {final_height:.2f}px. final_bbox: {tuple(f'{c:.2f}' for c in block.final_bbox)}")

        self.debug_logger.info("--- FIN LAYOUTPROCESSOR ---")
        return pages
