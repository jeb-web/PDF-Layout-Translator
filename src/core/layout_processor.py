#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** VERSION FINALE - GESTION DES PARAGRAPHES ET STYLES ***
"""
import logging
from typing import List
import fitz
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
        self.debug_logger.info("LayoutProcessor: Démarrage du calcul du reflow (Finale).")
        for page in pages:
            for block in page.text_blocks:
                original_width = block.bbox[2] - block.bbox[0]
                if original_width <= 0 or not block.spans:
                    block.final_bbox = block.bbox
                    continue

                all_words = []
                for span in block.spans:
                    if span.text:
                        # Remplacer les sauts de ligne par un marqueur spécial
                        text_with_markers = span.text.replace('\n', ' <PARA_BREAK> ')
                        words = text_with_markers.split(' ')
                        for i, word in enumerate(words):
                            all_words.append((word, span))
                
                if not all_words:
                    block.final_bbox = block.bbox
                    continue

                current_x = 0
                max_font_size_in_line = all_words[0][1].font.size
                total_height = max_font_size_in_line * 1.2
                
                for word, span in all_words:
                    if word == '<PARA_BREAK>':
                        current_x = 0
                        total_height += max_font_size_in_line * 1.2
                        max_font_size_in_line = span.font.size
                        continue

                    word_width = self._get_text_width(word + ' ', span.font.name, span.font.size)
                    
                    if current_x + word_width > original_width and current_x > 0:
                        current_x = 0
                        total_height += max_font_size_in_line * 1.2
                        max_font_size_in_line = span.font.size
                    
                    if span.font.size > max_font_size_in_line:
                        max_font_size_in_line = span.font.size

                    current_x += word_width
                
                new_height = total_height
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + new_height)
        return pages
