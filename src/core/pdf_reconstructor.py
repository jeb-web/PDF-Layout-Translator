#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION FINALE - Simple et Robuste ***
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
        self.debug_logger.info("--- Début du Rendu PDF (Mode Simple et Robuste) ---")
        doc = fitz.open()
        
        for page_data in pages:
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            for block in page_data.text_blocks:
                if not block.final_bbox or not block.spans:
                    continue

                # On assemble le texte correctement, avec des espaces.
                full_text = " ".join([s.text.strip() for s in block.spans if s.text])
                
                # On utilise le style du premier span comme style principal pour le bloc.
                # C'est une simplification, mais elle évitera les bugs.
                main_span = block.spans[0]
                font_path = self.font_manager.get_replacement_font_path(main_span.font.name)
                font_size = main_span.font.size
                color_rgb = self._hex_to_rgb(main_span.font.color)

                if not font_path or not font_path.exists():
                    self.logger.warning(f"Police de remplacement non trouvée pour '{main_span.font.name}', bloc {block.id} ignoré.")
                    continue
                
                try:
                    # On utilise la fonction la plus simple et la plus fiable : insert_textbox
                    page.insert_textbox(
                        block.final_bbox,
                        full_text,
                        fontsize=font_size,
                        fontfile=str(font_path),
                        color=color_rgb,
                        align=fitz.TEXT_ALIGN_LEFT
                    )
                except Exception as e:
                    self.logger.error(f"Erreur d'insertion pour le bloc {block.id}: {e}")

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"--- Rendu PDF (Mode Simple et Robuste) Terminé. ---")
