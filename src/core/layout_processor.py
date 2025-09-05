#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** VERSION DE TEST BRUTAL - BOÎTES GIGANTESQUES ***
"""
import logging
from typing import List
from core.data_model import PageObject
from utils.font_manager import FontManager
from fontTools.ttLib import TTFont

class LayoutProcessor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager
        # NOTE: Le reste de la classe (_get_font, _get_text_width) n'est plus utilisé dans ce test.

    def process_pages(self, pages: List[PageObject]) -> List[PageObject]:
        self.debug_logger.info("--- LayoutProcessor (Mode TEST BRUTAL) ---")
        
        for page in pages:
            for block in page.text_blocks:
                # --- MODIFICATION RADICALE ---
                # On ignore tous les calculs. On crée une boîte gigantesque.
                # On prend la largeur originale et on lui donne une hauteur fixe et énorme de 300 points.
                
                original_bbox = block.bbox
                new_height = 300.0 # Hauteur arbitraire, très grande.
                
                block.final_bbox = (
                    original_bbox[0], 
                    original_bbox[1], 
                    original_bbox[2], 
                    original_bbox[1] + new_height
                )
                
                self.debug_logger.info(f"  - Bloc {block.id}: Bbox forcée à une hauteur de {new_height}pt.")
        
        self.debug_logger.info("--- LayoutProcessor (Mode TEST BRUTAL) Terminé ---")
        return pages
