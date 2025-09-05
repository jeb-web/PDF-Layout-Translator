#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** VERSION FINALE - Calcul de largeur fiable avec Fitz ***
"""
import logging
from typing import List
import fitz # Utilisation de fitz pour la mesure
from core.data_model import PageObject
from utils.font_manager import FontManager

class LayoutProcessor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager

    def _get_text_width(self, text: str, font_name: str, font_size: float) -> float:
        # --- LOGIQUE DE MESURE CORRIGÉE ---
        # On utilise maintenant PyMuPDF (fitz) pour mesurer, comme pour le rendu.
        # C'est la source unique de vérité.
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if font_path and font_path.exists():
            try:
                # get_text_length attend 'fontname' pour le chemin, contrairement à insert_text
                return fitz.get_text_length(text, fontname=str(font_path), fontsize=font_size)
            except Exception as e:
                self.debug_logger.error(f"Erreur de mesure Fitz pour la police {font_path}: {e}")
        
        # Fallback si la police n'est pas trouvée ou si la mesure échoue
        self.debug_logger.warning(f"Calcul de secours pour la largeur du texte '{text}'")
        return len(text) * font_size * 0.6

    def process_pages(self, pages: List[PageObject]) -> List[PageObject]:
        self.debug_logger.info("LayoutProcessor: Démarrage du calcul du reflow.")
        for page in pages:
            for block in page.text_blocks:
                original_width = block.bbox[2] - block.bbox[0]
                if original_width <= 0 or not block.spans:
                    block.final_bbox = block.bbox
                    continue

                all_words = []
                for span in block.spans:
                    if span.text:
                        words = span.text.strip().split(' ')
                        for i, word in enumerate(words):
                            # Ajouter les espaces comme des "mots" distincts pour une mesure précise
                            all_words.append((word, span))
                            if i < len(words) - 1:
                                all_words.append((' ', span))
                
                if not all_words:
                    block.final_bbox = block.bbox
                    continue

                current_x = 0
                max_font_size_in_line = all_words[0][1].font.size
                current_y = max_font_size_in_line * 1.2 # Hauteur de la première ligne
                
                for word, span in all_words:
                    word_width = self._get_text_width(word, span.font.name, span.font.size)
                    
                    if current_x + word_width > original_width and current_x > 0:
                        current_x = 0
                        current_y += max_font_size_in_line * 1.2 # Interlignage
                        max_font_size_in_line = span.font.size
                    
                    if span.font.size > max_font_size_in_line:
                        max_font_size_in_line = span.font.size

                    current_x += word_width
                
                new_height = current_y
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + new_height)
                self.debug_logger.info(f"  - Bloc {block.id}: Nouvelle hauteur: {new_height:.2f}pt.")
        
        self.debug_logger.info("LayoutProcessor: Calcul du reflow terminé.")
        return pages
