#!/usr/bin/env python3
# -*- a: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION 1.1 - GESTION DES PARAGRAPHES (\n) ***
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
        self.debug_logger.info("="*50); self.debug_logger.info(" DÉBUT DU RENDU PDF (v1.1 - Mode Paragraphe) "); self.debug_logger.info("="*50)
        doc = fitz.open()
        self.font_object_cache.clear()

        for page_data in pages:
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            for block in page_data.text_blocks:
                if not block.final_bbox or not block.spans: continue
                
                shape = page.new_shape()
                block_bbox = fitz.Rect(block.final_bbox)
                
                main_span = block.spans[0]
                full_text = main_span.text
                font_path = self.font_manager.get_replacement_font_path(main_span.font.name)

                if not (font_path and font_path.exists()): continue

                self.debug_logger.info(f"  - [BLOC {block.id}] Rendu avec la police '{font_path.name}'.")

                # PyMuPDF a une fonction parfaite pour ça : insert_textbox
                # Elle gère le reflow et les sauts de ligne (\n) automatiquement.
                # C'est la solution la plus robuste.
                try:
                    shape.insert_textbox(
                        block_bbox,
                        full_text,
                        fontname=main_span.font.name, # Nom de fallback
                        fontfile=str(font_path),      # Fichier prioritaire
                        fontsize=main_span.font.size,
                        color=self._hex_to_rgb(main_span.font.color),
                        # On ne spécifie pas l'alignement pour l'instant
                    )
                    self.debug_logger.info(f"    -> Texte inséré dans le bloc via insert_textbox.")
                except Exception as e:
                    self.debug_logger.error(f"    -> ERREUR lors de l'utilisation de insert_textbox pour le bloc {block.id}: {e}", exc_info=True)

                shape.commit()

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"\n--- RENDU TERMINÉ ---")
