#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION FINALE - JALON 1.7 (Correction chargement Font) ***
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
        self.font_object_cache: Dict[str, fitz.Font] = {}

    def _hex_to_rgb(self, hex_color: str) -> Tuple[float, float, float]:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])
        if len(hex_color) != 6:
            return (0, 0, 0)
        try:
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError:
            return (0, 0, 0)

    def _get_font(self, font_name: str) -> fitz.Font:
        """Charge une police depuis le cache ou le disque via son nom."""
        if font_name in self.font_object_cache:
            self.debug_logger.info(f"      -> Police '{font_name}' trouvée dans le cache.")
            return self.font_object_cache[font_name]
        
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if not (font_path and font_path.exists()):
            self.debug_logger.error(f"      !! ÉCHEC _get_font: Chemin non trouvé pour la police '{font_name}'.")
            return None
        
        try:
            self.debug_logger.info(f"      -> Chargement de la police '{font_name}' depuis '{font_path}'.")
            font = fitz.Font(fontfile=str(font_path))
            self.font_object_cache[font_name] = font
            return font
        except Exception as e:
            self.debug_logger.error(f"      !! ÉCHEC _get_font: Erreur de chargement pour la police '{font_name}': {e}")
            return None

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Jalon 1.7) ---")
        doc = fitz.open()
        self.font_object_cache.clear()

        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            for block in page_data.text_blocks:
                self.debug_logger.info(f"  > Traitement du TextBlock ID: {block.id}")
                if not block.final_bbox or not block.spans:
                    self.debug_logger.warning("    !! BLOC IGNORÉ : final_bbox manquant ou spans vides.")
                    continue
                
                rect = fitz.Rect(block.final_bbox)
                if rect.is_empty:
                    self.debug_logger.error("    !! BLOC IGNORÉ : Rectangle invalide.")
                    continue

                writer = fitz.TextWriter(page.rect)
                for span in block.spans:
                    font = self._get_font(span.font.name)
                    if font:
                        writer.append(pos=(0,0), text=span.text, font=font, fontsize=span.font.size)
                
                # Vider le buffer dans la boîte pour le rendu final
                writer.fill_textbox(rect, text=None, align=block.alignment)

                self.debug_logger.info(f"    -> Bloc {block.id} dessiné.")

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
