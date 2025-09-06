!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION DE DÉBOGAGE - JALON 2.1 (Méthode Directe) ***
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
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Jalon 2.1) ---")
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
                self.debug_logger.info(f"  > Traitement du TextBlock ID: {block.id}")
                if not block.final_bbox or not block.spans: continue
                
                shape = page.new_shape()
                
                # Suivre la position verticale
                current_y = block.final_bbox[1]
                
                for span in block.spans:
                    if not span.text.strip(): continue

                    # Calcul du rectangle pour ce span
                    span_rect = fitz.Rect(
                        block.final_bbox[0], 
                        current_y, 
                        block.final_bbox[2], 
                        current_y + span.font.size * 1.5 # Estimation de la hauteur
                    )
                    
                    text = span.text
                    fontname = span.font.name
                    fontsize = span.font.size
                    color_rgb = self._hex_to_rgb(span.font.color)

                    self.debug_logger.info(f"    - Rendu du span : text='{text}'")
                    self.debug_logger.info(f"      -> rect={span_rect}, font='{fontname}', size={fontsize}, color={color_rgb}")
                    
                    try:
                        # Utiliser insert_textbox pour chaque span
                        rc = shape.insert_textbox(
                            span_rect,
                            text,
                            fontname=fontname,
                            fontsize=fontsize,
                            color=color_rgb,
                            align=block.alignment
                        )
                        self.debug_logger.info(f"      -> Texte inséré. Surplus de texte : {rc:.2f}")
                        if rc < 0:
                             self.debug_logger.warning("      !! ATTENTION : Le texte a débordé du rectangle alloué.")
                        
                        # Mettre à jour la position y pour le prochain span
                        # Ceci est une simplification et devra être amélioré
                        current_y += fontsize * 1.2

                    except Exception as e:
                        self.debug_logger.error(f"    !! ERREUR sur insert_textbox pour span {span.id}: {e}")

                shape.commit()

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
