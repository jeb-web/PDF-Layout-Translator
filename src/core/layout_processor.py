#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
Calcule le "reflow" du texte et ajuste les boîtes de délimitation.
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
        self.font_cache = {}

    def _get_font(self, font_name: str):
        if font_name in self.font_cache: return self.font_cache[font_name]
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if font_path and font_path.exists():
            try:
                font = TTFont(font_path)
                self.font_cache[font_name] = font
                return font
            except Exception as e:
                self.logger.error(f"Impossible de charger la police {font_path}: {e}")
        return None

    def _get_text_width(self, text: str, font_name: str, font_size: float) -> float:
        font = self._get_font(font_name)
        if not font: return len(text) * font_size * 0.6
        cmap = font.getBestCmap()
        glyph_set = font.getGlyphSet()
        total_width = 0
        if cmap:
            for char in text:
                if ord(char) in cmap:
                    glyph_name = cmap[ord(char)]
                    if glyph_name in glyph_set:
                        total_width += glyph_set[glyph_name].width
        return (total_width / font['head'].unitsPerEm) * font_size

    def process_pages(self, pages: List[PageObject]) -> List[PageObject]:
        self.debug_logger.info("LayoutProcessor: Démarrage du calcul du reflow.")
        for page in pages:
            for block in page.text_blocks:
                original_width = block.bbox[2] - block.bbox[0]
                if original_width <= 0 or not block.spans:
                    block.final_bbox = block.bbox
                    continue

                current_x = 0
                line_height = block.spans[0].font.size * 1.2
                current_y = line_height
                
                self.debug_logger.info(f"  - Calcul du bloc {block.id} (largeur: {original_width:.2f}pt)")
                
                for span in block.spans:
                    words = span.text.split(' ')
                    for i, word in enumerate(words):
                        word_with_space = word + (' ' if i < len(words) - 1 else '')
                        word_width = self._get_text_width(word_with_space, span.font.name, span.font.size)
                        
                        if current_x + word_width > original_width and current_x > 0:
                            current_x = 0
                            current_y += line_height
                        
                        current_x += word_width
                
                new_height = current_y
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + new_height)
                self.debug_logger.info(f"    -> Nouvelle hauteur: {new_height:.2f}pt. Bbox finale: {block.final_bbox}")
        
        self.debug_logger.info("LayoutProcessor: Calcul du reflow terminé.")
        return pages
