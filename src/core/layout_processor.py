#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** VERSION AMÉLIORÉE - Calcul précis du reflow avec gestion des débordements ***
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
        """Calcule la largeur précise du texte"""
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if font_path and font_path.exists():
            try:
                font_buffer = font_path.read_bytes()
                font = fitz.Font(fontbuffer=font_buffer)
                return font.text_length(text, fontsize=font_size)
            except Exception as e:
                self.debug_logger.error(f"Erreur de mesure Fitz pour la police {font_path}: {e}")
        return len(text) * font_size * 0.6

    def _calculate_text_height(self, text: str, font_name: str, font_size: float, available_width: float) -> float:
        """Calcule la hauteur nécessaire pour un texte donné dans une largeur donnée"""
        if not text.strip():
            return font_size * 1.2
        
        words = text.split()
        if not words:
            return font_size * 1.2
        
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            test_width = self._get_text_width(test_line, font_name, font_size)
            
            if test_width <= available_width or not current_line:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        line_count = max(len(lines), 1)
        return line_count * font_size * 1.3  # Interlignage de 1.3

    def _process_paragraph_reflow(self, paragraph, available_width: float) -> float:
        """Calcule la hauteur nécessaire pour un paragraphe avec reflow"""
        total_height = 0
        
        # Concatener tout le texte du paragraphe pour un calcul global
        full_text = ""
        representative_font = None
        
        for span in paragraph.spans:
            if span.text.strip():
                full_text += span.text + " "
                if representative_font is None:
                    representative_font = span.font
        
        if not full_text.strip() or not representative_font:
            return 15  # Hauteur minimale
        
        # Calculer la hauteur avec reflow
        paragraph_height = self._calculate_text_height(
            full_text.strip(), 
            representative_font.name, 
            representative_font.size, 
            available_width * 0.95  # Marge de sécurité
        )
        
        return paragraph_height

    def process_pages(self, pages: List[PageObject]) -> List[PageObject]:
        """Traitement principal avec calcul de reflow amélioré"""
        self.debug_logger.info("LayoutProcessor: Démarrage du calcul du reflow (Version Améliorée).")
        
        for page in pages:
            for block in page.text_blocks:
                original_width = block.bbox[2] - block.bbox[0]
                original_height = block.bbox[3] - block.bbox[1]
                
                if original_width <= 0 or not block.paragraphs:
                    block.final_bbox = block.bbox
                    continue

                self.debug_logger.info(f"  -> Traitement du bloc {block.id} (largeur: {original_width:.1f})")
                
                # Calculer la hauteur totale nécessaire
                total_height = 0
                
                for i, paragraph in enumerate(block.paragraphs):
                    paragraph_height = self._process_paragraph_reflow(paragraph, original_width)
                    total_height += paragraph_height
                    
                    # Espacement entre paragraphes (sauf pour le dernier)
                    if i < len(block.paragraphs) - 1:
                        total_height += 8
                
                # Hauteur minimale et maximale
                min_height = original_height * 0.8  # Peut réduire de 20%
                max_height = original_height * 3.0  # Peut tripler au maximum
                
                final_height = max(min_height, min(total_height, max_height))
                
                # Si débordement important, signaler
                if total_height > max_height:
                    self.debug_logger.warning(f"  -> Débordement important pour {block.id}: "
                                            f"nécessaire={total_height:.1f}, max={max_height:.1f}")
                
                # Définir la bbox finale
                block.final_bbox = (
                    block.bbox[0], 
                    block.bbox[1], 
                    block.bbox[2], 
                    block.bbox[1] + final_height
                )
                
                self.debug_logger.info(f"  -> Final bbox: {block.final_bbox} (hauteur: {final_height:.1f})")

        return pages
