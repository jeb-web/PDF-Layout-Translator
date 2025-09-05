#!/usr/bin/env python3
# -*- a: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION DÉFINITIVE - CORRECTION DE LA GESTION DES RESSOURCES DE PAGE ***
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
        # Cache pour les OBJETS Font, utilisés pour la MESURE. C'est le seul cache nécessaire.
        self.font_object_cache: Dict[Path, fitz.Font] = {}

    def _hex_to_rgb(self, hex_color: str) -> Tuple[float, float, float]:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3: hex_color = "".join([c*2 for c in hex_color])
        if len(hex_color) != 6: return (0, 0, 0)
        try:
            r = int(hex_color[0:2], 16) / 255.0; g = int(hex_color[2:4], 16) / 255.0; b = int(hex_color[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError: return (0, 0, 0)
            
    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("="*50); self.debug_logger.info(" NOUVEAU RENDU PDF (VERSION DÉFINITIVE) "); self.debug_logger.info("="*50)
        doc = fitz.open()
        # On ne vide que le cache des objets Font.
        self.font_object_cache.clear()

        for page_data in pages:
            self.debug_logger.info(f"\n--- [PAGE {page_data.page_number}] ---")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            for block in page_data.text_blocks:
                if not block.final_bbox or not block.spans: continue
                
                shape = page.new_shape()
                block_bbox = fitz.Rect(block.final_bbox)
                if not block.spans: continue
                
                max_font_size_in_line = block.spans[0].font.size
                current_pos = fitz.Point(block_bbox.x0, block_bbox.y0 + max_font_size_in_line)

                for span in block.spans:
                    if not span.text or not span.text.strip(): continue
                    
                    font_path = self.font_manager.get_replacement_font_path(span.font.name)
                    if not (font_path and font_path.exists()): continue
                    
                    try:
                        # --- ÉTAPE 1: PRÉPARATION DE LA MESURE (via cache d'objets) ---
                        if font_path not in self.font_object_cache:
                            font_buffer = font_path.read_bytes()
                            self.font_object_cache[font_path] = fitz.Font(fontbuffer=font_buffer)
                        font_object = self.font_object_cache[font_path]

                        # --- ÉTAPE 2: PRÉPARATION DU DESSIN (insertion directe, pas de cache de référence) ---
                        # On insère la police pour chaque span. PyMuPDF gère l'optimisation en interne.
                        # C'est la seule approche qui garantit que la référence est valide pour la PAGE ACTUELLE.
                        font_ref_name = page.insert_font(fontfile=str(font_path), fontname=font_path.stem)
                        self.debug_logger.info(f"    - [SPAN {span.id}] Police '{font_path.name}' insérée sur la page. Réf: '{font_ref_name}'")

                    except Exception as e:
                        self.logger.error(f"Erreur de préparation de la police {font_path.name} pour le span {span.id}: {e}", exc_info=True)
                        continue

                    words = span.text.strip().split(' ')
                    for i, word in enumerate(words):
                        word_to_draw = word + (' ' if i < len(words) - 1 else '')
                        
                        word_width = font_object.text_length(word_to_draw, fontsize=span.font.size)
                        
                        if current_pos.x + word_width > block_bbox.x1 and current_pos.x > block_bbox.x0:
                            current_pos.x = block_bbox.x0; current_pos.y += max_font_size_in_line * 1.2
                            max_font_size_in_line = span.font.size
                        
                        if span.font.size > max_font_size_in_line: max_font_size_in_line = span.font.size
                        if current_pos.y > block_bbox.y1 + 5: break

                        shape.insert_text(
                            current_pos, word_to_draw,
                            fontname=str(font_ref_name), # On s'assure que c'est une string
                            fontsize=span.font.size,
                            color=self._hex_to_rgb(span.font.color)
                        )
                        current_pos.x += word_width
                    
                    if current_pos.y > block_bbox.y1 + 5: break
                
                shape.commit()

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"\nPDF final sauvegardé dans : {output_path}")
