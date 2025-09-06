#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** VERSION FINALE - Jalon 3.0 (Stratégie de Préservation de Hauteur) ***
"""
import logging
from typing import List
import fitz
from core.data_model import PageObject, TextBlock
from utils.font_manager import FontManager

class LayoutProcessor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager
        self._font_cache = {}

    def _get_font(self, font_name: str) -> fitz.Font:
        if font_name in self._font_cache:
            return self._font_cache[font_name]
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if font_path and font_path.exists():
            try:
                font_buffer = font_path.read_bytes()
                font = fitz.Font(fontbuffer=font_buffer)
                self._font_cache[font_name] = font
                return font
            except Exception as e:
                self.debug_logger.error(f"Erreur de mesure Fitz pour la police {font_path}: {e}")
        return fitz.Font()

    def _get_text_width(self, text: str, font_name: str, font_size: float) -> float:
        font = self._get_font(font_name)
        return font.text_length(text, fontsize=font_size)

    def _calculate_text_height(self, block: TextBlock, width: float) -> float:
        if not block.spans or width <= 0:
            return 0

        all_words = []
        for span in block.spans:
            if span.text:
                words = span.text.replace('\n', ' <PARA_BREAK> ').split(' ')
                for word in words:
                    if word: all_words.append((word, span))
        
        if not all_words: return 0

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
            
            if current_x > 0 and current_x + word_width > width:
                current_x = 0
                total_height += max_font_size_in_line * 1.2
                max_font_size_in_line = span.font.size
            
            if span.font.size > max_font_size_in_line:
                max_font_size_in_line = span.font.size

            current_x += word_width
        
        return total_height

    def process_pages(self, pages: List[PageObject]) -> List[PageObject]:
        self.debug_logger.info("--- DÉMARRAGE LAYOUTPROCESSOR (Stratégie de Préservation de Hauteur) ---")
        self._font_cache.clear()

        for page in pages:
            self.debug_logger.info(f"Traitement de la Page {page.page_number}")
            sorted_blocks = sorted(page.text_blocks, key=lambda b: (b.bbox[1], b.bbox[0]))
            
            for i, block in enumerate(sorted_blocks):
                original_height = block.bbox[3] - block.bbox[1]
                original_width = block.bbox[2] - block.bbox[0]

                if original_width <= 0 or not block.spans:
                    block.final_bbox = block.bbox
                    continue

                # Règle A: Le texte tient-il dans la boîte d'origine ?
                height_at_original_width = self._calculate_text_height(block, original_width)
                
                if height_at_original_width <= original_height * 1.05: # Tolérance de 5%
                    self.debug_logger.info(f"  - Bloc {block.id}: CONSERVÉ. Le texte tient dans les dimensions originales.")
                    block.final_bbox = block.bbox
                    continue

                # Règle B: Tenter d'élargir horizontalement
                # Calcul de la largeur nécessaire par approximation
                ratio = height_at_original_width / original_height
                required_width = original_width * ratio 
                
                right_boundary = page.dimensions[0] - 5 # Marge de sécurité
                for other_block in sorted_blocks:
                    if other_block.id != block.id and other_block.bbox[0] > block.bbox[0]:
                        # Check for vertical overlap
                        if max(block.bbox[1], other_block.bbox[1]) < min(block.bbox[3], other_block.bbox[3]):
                            right_boundary = min(right_boundary, other_block.bbox[0] - 5) # Marge de sécurité

                if block.bbox[0] + required_width < right_boundary:
                    height_at_new_width = self._calculate_text_height(block, required_width)
                    if height_at_new_width <= original_height:
                        self.debug_logger.info(f"  - Bloc {block.id}: ÉLARGI. Nouvelle largeur: {required_width:.2f}")
                        block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[0] + required_width, block.bbox[3])
                        continue

                # Règle E (Fallback): Étendre verticalement
                self.debug_logger.warning(f"  - Bloc {block.id}: ÉTENDU VERTICALEMENT. L'élargissement a échoué ou était insuffisant.")
                new_height = self._calculate_text_height(block, original_width)
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + new_height)
                block.is_vertically_extended = True

        return pages
