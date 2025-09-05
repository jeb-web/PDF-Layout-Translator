#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION CORRIGÉE ***
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
        self.debug_logger.info("--- Début du Rendu PDF (Avec Correction du Texte) ---")
        doc = fitz.open()
        for page_data in pages:
            self.debug_logger.info(f"Rendu de la page {page_data.page_number}...")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            for block in page_data.text_blocks:
                if not block.final_bbox: 
                    self.debug_logger.warning(f"  - Bloc {block.id} ignoré : pas de Bbox finale.")
                    continue

                # --- CORRECTION FINALE : Joindre les textes avec un espace ---
                full_text = " ".join([s.text.strip() for s in block.spans if s.text])
                # --- FIN DE LA CORRECTION ---

                self.debug_logger.info(f"  -> Rendu du bloc {block.id} avec texte: '{full_text[:70]}...'")
                
                if block.spans:
                    main_span = block.spans[0]
                    font_path = self.font_manager.get_replacement_font_path(main_span.font.name)
                    color_rgb = self._hex_to_rgb(main_span.font.color)

                    if font_path and font_path.exists():
                        font_internal_name = f"F-{font_path.stem.replace(' ', '')}"
                        try:
                            # Utilisation de la final_bbox maintenant que le texte est correct
                            page.insert_textbox(block.final_bbox, full_text, fontsize=main_span.font.size,
                                                fontname=font_internal_name, fontfile=str(font_path), color=color_rgb)
                            self.debug_logger.info(f"     Bloc inséré avec police '{font_path.name}' et couleur {color_rgb}.")
                        except Exception as e:
                             self.logger.error(f"Erreur d'insertion texte bloc {block.id}: {e}")
                             self.debug_logger.error(f"     ERREUR d'insertion texte bloc {block.id}: {e}")
                    else:
                        self.logger.warning(f"Police de remplacement non trouvée pour '{main_span.font.name}', utilisant Helvetica.")
                        self.debug_logger.warning(f"     Police de remplacement non trouvée pour '{main_span.font.name}', utilisant Helvetica.")
                        page.insert_textbox(block.final_bbox, full_text, fontsize=main_span.font.size,
                                            fontname="helv", color=color_rgb)
        
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"--- Rendu PDF CORRIGÉ Terminé. Fichier sauvegardé: {output_path} ---")
