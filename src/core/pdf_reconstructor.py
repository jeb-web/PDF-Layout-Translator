#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION FINALE - Rendu Span par Span (Corrigé) ***
"""
import logging
from pathlib import Path
from typing import List, Tuple
import fitz
from core.data_model import PageObject
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
        self.debug_logger.info("--- Début du Rendu PDF (Mode Span-par-Span Corrigé) ---")
        doc = fitz.open()
        
        for page_data in pages:
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            for block in page_data.text_blocks:
                if not block.final_bbox or not block.spans:
                    continue
                
                with page.new_shape() as shape:
                    block_bbox = fitz.Rect(block.final_bbox)
                    current_x = block_bbox.x0
                    
                    # Commencer à dessiner à partir du haut du bloc
                    # La ligne de base de la première ligne est à (hauteur de la police) du haut
                    max_font_size_in_line = block.spans[0].font.size if block.spans else 10
                    current_y = block_bbox.y0 + max_font_size_in_line

                    all_words = []
                    for span in block.spans:
                        words = span.text.split(' ')
                        for i, word in enumerate(words):
                            word_with_space = word + (' ' if i < len(words) - 1 else '')
                            all_words.append((word_with_space, span))

                    if not all_words: continue

                    for word, span in all_words:
                        font_path = self.font_manager.get_replacement_font_path(span.font.name)
                        if not (font_path and font_path.exists()):
                            self.logger.warning(f"Police non trouvée pour '{span.font.name}', rendu ignoré.")
                            continue
                        
                        # --- CORRECTION DE L'ERREUR LAMBDA ---
                        # Remplacer 'fontname' par 'fontfile'
                        word_width = fitz.get_text_length(word, fontfile=str(font_path), fontsize=span.font.size)
                        
                        if current_x + word_width > block_bbox.x1:
                            current_x = block_bbox.x0
                            current_y += max_font_size_in_line * 1.2 # Interlignage
                            max_font_size_in_line = span.font.size
                        
                        if span.font.size > max_font_size_in_line:
                             max_font_size_in_line = span.font.size

                        # Vérifier si on dépasse la hauteur du bloc
                        if current_y > block_bbox.y1:
                            self.debug_logger.warning(f"  - Bloc {block.id}: Dépassement de la hauteur calculée. Le texte sera tronqué.")
                            break # Arrêter de dessiner ce bloc

                        shape.insert_text(
                            (current_x, current_y),
                            word,
                            fontfile=str(font_path),
                            fontsize=span.font.size,
                            color=self._hex_to_rgb(span.font.color)
                        )
                        current_x += word_width

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"--- Rendu PDF (Mode Span-par-Span Corrigé) Terminé. ---")
