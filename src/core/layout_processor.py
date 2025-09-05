#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** VERSION 1.1 - GESTION DES PARAGRAPHES (\n) ***
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
        
        # Fallback très simple si la mesure échoue
        return len(text) * font_size * 0.6

    def process_pages(self, pages: List[PageObject]) -> List[PageObject]:
        self.debug_logger.info("="*50)
        self.debug_logger.info(" DÉBUT DU CALCUL DE REFLOW (v1.1 - Mode Paragraphe) ")
        self.debug_logger.info("="*50)

        for page in pages:
            for block in page.text_blocks:
                original_width = block.bbox[2] - block.bbox[0]
                
                if original_width <= 0 or not block.spans:
                    block.final_bbox = block.bbox
                    self.debug_logger.info(f"  - Bloc {block.id}: Ignoré (largeur nulle ou pas de spans).")
                    continue
                
                # Le texte complet avec les \n se trouve dans le premier (et unique) span
                full_text = block.spans[0].text
                main_span = block.spans[0]
                
                # Diviser le texte en paragraphes basés sur les sauts de ligne
                paragraphs = full_text.split('\n')
                self.debug_logger.info(f"  - Bloc {block.id}: Calcul pour {len(paragraphs)} paragraphe(s).")

                total_height = 0
                for i, para_text in enumerate(paragraphs):
                    if not para_text.strip():
                        # Gérer les lignes vides : ajouter la hauteur d'une ligne standard.
                        total_height += main_span.font.size * 1.2
                        self.debug_logger.info(f"    -> Paragraphe {i+1} (vide): Hauteur ajoutée: {main_span.font.size * 1.2:.2f}pt.")
                        continue

                    words = para_text.strip().split(' ')
                    
                    current_x = 0
                    # La hauteur de ligne est déterminée par la police principale du bloc
                    line_height = main_span.font.size * 1.2
                    para_height = line_height
                    
                    for word in words:
                        # On ajoute un espace pour la mesure, sauf pour le dernier mot
                        word_to_measure = word + " "
                        word_width = self._get_text_width(word_to_measure, main_span.font.name, main_span.font.size)
                        
                        if current_x + word_width > original_width and current_x > 0:
                            # Saut de ligne "naturel"
                            current_x = 0
                            para_height += line_height
                        
                        current_x += word_width
                    
                    total_height += para_height
                    self.debug_logger.info(f"    -> Paragraphe {i+1}: Hauteur calculée: {para_height:.2f}pt.")

                new_height = total_height
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + new_height)
                self.debug_logger.info(f"  - Bloc {block.id}: Nouvelle hauteur totale calculée: {new_height:.2f}pt.")
        
        self.debug_logger.info("="*50); self.debug_logger.info(" FIN DU CALCUL DE REFLOW "); self.debug_logger.info("="*50)
        return pages
