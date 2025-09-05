#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION FINALE - Rendu Span par Span ***
"""
import logging
from pathlib import Path
from typing import List, Tuple
import fitz
from core.data_model import PageObject, TextSpan
from utils.font_manager import FontManager

class PDFReconstructor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager

    def _hex_to_rgb(self, hex_color: str) -> Tuple[float, float, float]:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3: hex_color = "".join([c*2 for c in hex_color])
        if len(hex_color) != 6: return (0, 0, 0)
        try:
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError:
            return (0, 0, 0)

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- Début du Rendu PDF (Mode Span-par-Span) ---")
        doc = fitz.open()
        
        for page_data in pages:
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            for block in page_data.text_blocks:
                if not block.final_bbox or not block.spans:
                    continue
                
                # On utilise un "Shape" (canevas) pour un contrôle total sur le dessin
                with page.new_shape(block.final_bbox) as shape:
                    current_x = 0
                    current_y = 0 # Le (0,0) est relatif au coin supérieur gauche de la bbox
                    line_height = 0
                    max_font_size_in_line = 0

                    all_words = []
                    for span in block.spans:
                        words = span.text.split(' ')
                        for i, word in enumerate(words):
                            word_with_space = word + (' ' if i < len(words) - 1 else '')
                            all_words.append((word_with_space, span))

                    if not all_words: continue

                    # La première ligne commence avec la hauteur de la première police
                    max_font_size_in_line = all_words[0][1].font.size
                    line_height = max_font_size_in_line * 1.2
                    current_y = max_font_size_in_line # Position de la ligne de base

                    for word, span in all_words:
                        font_path = self.font_manager.get_replacement_font_path(span.font.name)
                        if not (font_path and font_path.exists()):
                            self.logger.warning(f"Police non trouvée pour '{span.font.name}', rendu du mot '{word}' ignoré.")
                            continue
                        
                        word_width = fitz.get_text_length(word, fontname=str(font_path), fontsize=span.font.size)
                        
                        # Retour à la ligne si le mot dépasse
                        if current_x + word_width > block.final_bbox[2] - block.final_bbox[0] and current_x > 0:
                            current_x = 0
                            current_y += line_height
                            max_font_size_in_line = span.font.size
                            line_height = max_font_size_in_line * 1.2
                        
                        # Mise à jour de la hauteur de ligne si une police plus grande apparaît sur la même ligne
                        if span.font.size > max_font_size_in_line:
                            max_font_size_in_line = span.font.size
                            line_height = max_font_size_in_line * 1.2
                        
                        # Dessin du mot avec son propre style
                        shape.insert_text(
                            (current_x, current_y),
                            word,
                            fontname=str(font_path),
                            fontsize=span.font.size,
                            color=self._hex_to_rgb(span.font.color)
                        )
                        current_x += word_width

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"--- Rendu PDF (Mode Span-par-Span) Terminé. Fichier: {output_path} ---")
