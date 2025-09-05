#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
Calcule le "reflow" du texte et ajuste les boîtes de délimitation.

Auteur: L'OréalGPT
Version: 2.0.1 (Correction des imports)
"""
import logging
from typing import List, Dict, Tuple
# CORRECTION: Import absolu depuis la racine 'src'
from core.data_model import PageObject
from utils.font_manager import FontManager
from fontTools.ttLib import TTFont

class LayoutProcessor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.font_manager = font_manager
        self.font_cache = {}

    def _get_font(self, font_name: str):
        """Met en cache les objets TTFont pour la mesure."""
        if font_name in self.font_cache:
            return self.font_cache[font_name]
        
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
        """Calcule la largeur d'une chaîne de texte avec une police donnée."""
        font = self._get_font(font_name)
        if not font:
            return len(text) * font_size * 0.6  # Estimation grossière

        cmap = font.getBestCmap()
        glyph_set = font.getGlyphSet()
        total_width = 0
        for char in text:
            if ord(char) in cmap:
                glyph_name = cmap[ord(char)]
                if glyph_name in glyph_set:
                    total_width += glyph_set[glyph_name].width
        
        return (total_width / font['head'].unitsPerEm) * font_size

    def process_pages(self, pages: List[PageObject], translations: Dict[str, str]) -> List[PageObject]:
        """Met à jour le DOM avec les traductions et calcule le reflow."""
        self.logger.info("Début du traitement de la mise en page (reflow).")
        
        # Étape 1: Mettre à jour le texte des spans
        for page in pages:
            for block in page.text_blocks:
                for span in block.spans:
                    if span.id in translations:
                        span.translated_text = translations[span.id]

        # Étape 2: Calculer le reflow pour chaque bloc
        for page in pages:
            for block in page.text_blocks:
                # Cette partie est très complexe et nécessite un algorithme de reflow complet.
                # Pour cette phase, nous allons adopter une stratégie simple :
                # - On calcule la nouvelle hauteur nécessaire.
                # - On met à jour la bbox finale.
                
                original_width = block.bbox[2] - block.bbox[0]
                if original_width <= 0:
                    block.final_bbox = block.bbox
                    continue

                current_x = 0
                current_y = block.spans[0].font.size if block.spans else 0
                line_height_factor = 1.2
                
                for span in block.spans:
                    text_to_process = span.translated_text if span.translated_text else span.text
                    words = text_to_process.split(' ')
                    
                    for i, word in enumerate(words):
                        # Ajouter un espace sauf pour le dernier mot d'un span
                        word_with_space = word + (' ' if i < len(words) - 1 else '')
                        word_width = self._get_text_width(word_with_space, span.font.name, span.font.size)
                        
                        if current_x + word_width > original_width and current_x > 0:
                            current_x = 0
                            current_y += span.font.size * line_height_factor
                        
                        current_x += word_width
                
                new_height = current_y
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + new_height)
        
        self.logger.info("Traitement de la mise en page terminé.")
        return pages
