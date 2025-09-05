#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION FINALE - Rendu Multi-Style Fiable ***
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
        self.debug_logger.info("--- Début du Rendu PDF (Mode Multi-Style) ---")
        doc = fitz.open()
        
        for page_data in pages:
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            for block in page_data.text_blocks:
                if not block.final_bbox or not block.spans:
                    continue
                
                # On utilise TextWriter pour un contrôle précis du placement du texte
                tw = fitz.TextWriter(page.rect)
                
                block_bbox = fitz.Rect(block.final_bbox)
                current_x = block_bbox.x0
                
                if not block.spans: continue
                
                max_font_size_in_line = block.spans[0].font.size
                # La position Y de la ligne de base pour la première ligne
                current_y = block_bbox.y0 + max_font_size_in_line

                for span in block.spans:
                    if not span.text: continue
                    
                    font_path = self.font_manager.get_replacement_font_path(span.font.name)
                    if not (font_path and font_path.exists()):
                        self.logger.warning(f"Police non trouvée pour '{span.font.name}', rendu ignoré.")
                        continue
                    
                    words = span.text.strip().split(' ')
                    for i, word in enumerate(words):
                        word_to_draw = word + (' ' if i < len(words) - 1 else '')
                        
                        word_width = fitz.get_text_length(word_to_draw, fontfile=str(font_path), fontsize=span.font.size)
                        
                        # Si le mot dépasse la boîte, on passe à la ligne
                        if current_x + word_width > block_bbox.x1 and current_x > block_bbox.x0:
                            current_x = block_bbox.x0
                            current_y += max_font_size_in_line * 1.2 # Interlignage
                            max_font_size_in_line = span.font.size
                        
                        # Si un mot avec une police plus grande est sur la même ligne, on ajuste
                        if span.font.size > max_font_size_in_line:
                            max_font_size_in_line = span.font.size

                        # Si on dépasse la hauteur de la boîte, on arrête
                        if current_y > block_bbox.y1:
                            self.debug_logger.warning(f"Bloc {block.id}: Dépassement de hauteur.")
                            break

                        # On ajoute le texte au TextWriter avec son propre style
                        tw.append(
                            (current_x, current_y),
                            word_to_draw,
                            font=fitz.Font(fontfile=str(font_path)),
                            fontsize=span.font.size,
                            color=self._hex_to_rgb(span.font.color)
                        )
                        current_x += word_width
                    
                    if current_y > block_bbox.y1: break
                
                # On écrit tout le texte du bloc sur la page
                tw.write_text(page)

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"--- Rendu PDF (Mode Multi-Style) Terminé. ---")
