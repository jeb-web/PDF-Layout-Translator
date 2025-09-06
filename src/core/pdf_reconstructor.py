#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION FINALE - CORRECTION DE LA RÉGRESSION DE MESURE ***
"""
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import fitz
from core.data_model import PageObject
from utils.font_manager import FontManager

class PDFReconstructor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager
        # Cache pour les objets Font, essentiel pour la performance de la mesure
        self.font_object_cache: Dict[Path, fitz.Font] = {}

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
        self.debug_logger.info("--- Début du Rendu PDF (v2.1 Corrigé) ---")
        doc = fitz.open()
        self.font_object_cache.clear()
        
        for page_data in pages:
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            for block in page_data.text_blocks:
                if not block.final_bbox or not block.spans: continue
                
                shape = page.new_shape()
                block_bbox = fitz.Rect(block.final_bbox)
                
                max_line_height = 0
                if block.spans:
                    max_line_height = block.spans[0].font.size * 1.2
                
                current_pos = fitz.Point(block_bbox.x0, block_bbox.y0 + max_line_height)

                for span in block.spans:
                    if not span.text: continue
                    
                    if span.font.size * 1.2 > max_line_height:
                        max_line_height = span.font.size * 1.2
                    
                    font_path = self.font_manager.get_replacement_font_path(span.font.name)
                    if not (font_path and font_path.exists()):
                        self.logger.warning(f"Police non trouvée pour '{span.font.name}', rendu ignoré.")
                        continue
                    
                    # --- CORRECTION DE LA RÉGRESSION ---
                    # On utilise la méthode de mesure prouvée et fiable.
                    try:
                        if font_path not in self.font_object_cache:
                            font_buffer = font_path.read_bytes()
                            self.font_object_cache[font_path] = fitz.Font(fontbuffer=font_buffer)
                        font_object = self.font_object_cache[font_path]
                    except Exception as e:
                        self.logger.error(f"Impossible de charger la police {font_path} pour la mesure: {e}")
                        continue
                    # -----------------------------------
                    
                    words = span.text.strip().split(' ')
                    for i, word in enumerate(words):
                        word_to_draw = word + (' ' if i < len(words) - 1 else '')
                        
                        # On utilise l'objet Font pour mesurer, pas la fonction globale.
                        word_width = font_object.text_length(word_to_draw, fontsize=span.font.size)
                        
                        if current_pos.x + word_width > block_bbox.x1 and current_pos.x > block_bbox.x0:
                            current_pos.x = block_bbox.x0
                            current_pos.y += max_line_height
                            max_line_height = span.font.size * 1.2
                        
                        if current_pos.y > block_bbox.y1 + 5: break

                        # Le dessin, lui, peut utiliser 'fontfile' directement.
                        shape.insert_text(
                            current_pos,
                            word_to_draw,
                            fontfile=str(font_path),
                            fontsize=span.font.size,
                            color=self._hex_to_rgb(span.font.color)
                        )
                        current_pos.x += word_width

                    if span.is_last_in_line:
                        current_pos.x = block_bbox.x0
                        current_pos.y += max_line_height
                        if block.spans:
                            next_span_index = block.spans.index(span) + 1
                            if next_span_index < len(block.spans):
                                max_line_height = block.spans[next_span_index].font.size * 1.2
                    
                    if current_pos.y > block_bbox.y1 + 5: break
                
                shape.commit()

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"--- Rendu PDF (v2.1 Corrigé) Terminé. ---")
