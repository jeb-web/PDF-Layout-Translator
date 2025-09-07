#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** NOUVELLE VERSION - DESSINATEUR DE SPANS PRÉ-POSITIONNÉS ***
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
        if len(hex_color) == 3: hex_color = "".join([c * 2 for c in hex_color])
        if len(hex_color) != 6: return (0, 0, 0)
        try:
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError: return (0, 0, 0)

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (v2 - Mode Dessinateur) ---")
        doc = fitz.open()

        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            # Enregistrer les polices nécessaires
            fonts_on_page = {span.font.name for block in page_data.text_blocks for span in block.spans}
            for font_name in fonts_on_page:
                font_path = self.font_manager.get_replacement_font_path(font_name)
                if font_path and font_path.exists():
                    try:
                        page.insert_font(fontname=font_name, fontfile=str(font_path))
                    except Exception as e:
                        self.debug_logger.error(f"  -> ERREUR enregistrement police '{font_name}': {e}")

            for block in page_data.text_blocks:
                self.debug_logger.info(f"  > Dessin du TextBlock ID: {block.id}")
                if not block.spans: continue
                
                for span in block.spans:
                    if not span.text or not span.final_bbox:
                        if not span.final_bbox:
                             self.debug_logger.warning(f"    ! Span ignoré (ID: {span.id}) car `final_bbox` est manquant.")
                        continue

                    span_rect = fitz.Rect(span.final_bbox)
                    text = span.text
                    fontname = span.font.name
                    fontsize = span.font.size
                    color_rgb = self._hex_to_rgb(span.font.color)

                    self.debug_logger.info(f"    - Rendu du mot/span : '{text}'")
                    self.debug_logger.info(f"      -> rect={span_rect}, font='{fontname}', size={fontsize}, color={color_rgb}")
                    
                    try:
                        # Utiliser insert_textbox qui gère bien le clipping et l'alignement vertical
                        rc = page.insert_textbox(
                            span_rect,
                            text,
                            fontname=fontname,
                            fontsize=fontsize,
                            color=color_rgb,
                            align=block.alignment
                        )
                        if rc < 0:
                             self.debug_logger.warning(f"      !! ATTENTION : Le texte '{text}' a débordé du rectangle alloué de {abs(rc):.2f} unités.")
                        
                    except Exception as e:
                        self.debug_logger.error(f"    !! ERREUR sur insert_textbox pour span {span.id}: {e}")

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
