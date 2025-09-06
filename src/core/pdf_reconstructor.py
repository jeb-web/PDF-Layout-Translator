#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION CORRIGÉE - Jalon 2.3 (Utilisation du BBox final) ***
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
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Jalon 2.3) ---")
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
                
                rect = fitz.Rect(block.final_bbox)
                if rect.is_empty: continue
                
                self.debug_logger.info(f"    - Utilisation du rectangle final_bbox: {rect}")
                
                # Créer un TextWriter pour assembler le contenu du bloc
                writer = fitz.TextWriter(rect)

                for span in block.spans:
                    # On ne charge plus la police ici, on utilise le nom enregistré
                    writer.append(
                        (rect.x0, rect.y0), # La position initiale est gérée par fill_textbox
                        span.text, 
                        font=fitz.Font(fontname=span.font.name), 
                        fontsize=span.font.size
                    )
                
                # Utiliser une Shape pour dessiner le contenu du TextWriter
                shape = page.new_shape()
                try:
                    # La couleur est définie au niveau de la shape, on prend la couleur du premier span
                    shape.text_writer(
                        color=self._hex_to_rgb(block.spans[0].font.color)
                    )
                    shape.run_text_writer(writer)
                    shape.commit()
                    self.debug_logger.info(f"    -> Bloc {block.id} dessiné.")
                except Exception as e:
                    self.debug_logger.error(f"    !! ERREUR lors du dessin du bloc {block.id}: {e}")


        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
