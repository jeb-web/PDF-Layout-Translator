#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** VERSION SIMPLIFIÉE - Estimation de hauteur généreuse ***
"""
import logging
from typing import List
from core.data_model import PageObject
from utils.font_manager import FontManager

class LayoutProcessor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager

    def process_pages(self, pages: List[PageObject]) -> List[PageObject]:
        self.debug_logger.info("LayoutProcessor: Démarrage du calcul du reflow (Mode Simplifié).")
        for page in pages:
            for block in page.text_blocks:
                if not block.spans:
                    block.final_bbox = block.bbox
                    continue

                # On estime une hauteur TRES généreuse pour éviter tout problème
                # 30 points par span, ce qui devrait être largement suffisant
                estimated_height = len(block.spans) * 30.0
                
                block.final_bbox = (
                    block.bbox[0], 
                    block.bbox[1], 
                    block.bbox[2], 
                    block.bbox[1] + estimated_height
                )
                self.debug_logger.info(f"  - Bloc {block.id}: Bbox forcée à une hauteur de {estimated_height}pt.")
        
        self.debug_logger.info("LayoutProcessor: Calcul du reflow (Mode Simplifié) terminé.")
        return pages
