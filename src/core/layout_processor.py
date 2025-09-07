#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** VERSION FINALE ET STABILISÉE v2.9 - REPOSITIONNEMENT VERTICAL ***
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
        # ... (méthode inchangée) ...

    def process_pages(self, pages: List[PageObject]) -> List[PageObject]:
        self.debug_logger.info("--- DÉMARRAGE LAYOUTPROCESSOR (v2.9 - Repositionnement Vertical) ---")
        for page in pages:
            self.debug_logger.info(f"  > Traitement de la Page {page.page_number}")
            
            vertical_offset = 0.0

            for block in sorted(page.text_blocks, key=lambda b: b.bbox[1]):
                self.debug_logger.info(f"    -> Calcul du reflow pour le bloc {block.id}")

                # Appliquer le décalage vertical accumulé
                original_y_start = block.bbox[1]
                block.bbox = (block.bbox[0], block.bbox[1] + vertical_offset, block.bbox[2], block.bbox[3] + vertical_offset)
                
                all_new_spans_for_block = []
                current_y = block.bbox[1]
                
                # ... [La logique de calcul de largeur globale et de mise en page interne reste la même que dans la v2.8] ...
                
                block.spans = all_new_spans_for_block
                
                new_height = (current_y - block.bbox[1]) if all_new_spans_for_block else 0
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + new_height)
                
                # Calculer le nouveau décalage pour le bloc suivant
                original_height = block.bbox[3] - original_y_start # Utiliser la position Y d'origine
                height_increase = new_height - original_height
                if height_increase > 0:
                    self.debug_logger.info(f"      [Repositionnement] Le bloc {block.id} a grandi de {height_increase:.1f}px. Mise à jour du décalage vertical.")
                    vertical_offset += height_increase

        self.debug_logger.info("--- FIN LAYOUTPROCESSOR ---")
        return pages
