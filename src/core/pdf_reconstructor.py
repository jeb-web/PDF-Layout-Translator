#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
Dessine le DOM finalisé dans un nouveau fichier PDF.

Auteur: L'OréalGPT
Version: 2.0.1 (Correction des imports)
"""
import logging
from pathlib import Path
from typing import List
import fitz  # PyMuPDF
# CORRECTION: Import absolu depuis la racine 'src'
from core.data_model import PageObject, TextSpan
from utils.font_manager import FontManager

class PDFReconstructor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.font_manager = font_manager

    def render_pages(self, pages: List[PageObject], output_path: Path):
        """Crée un PDF à partir de la liste d'objets PageObject."""
        self.logger.info(f"Début du rendu vers le fichier PDF : {output_path}")
        doc = fitz.open()

        for page_data in pages:
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            for block in page_data.text_blocks:
                if not block.final_bbox: continue

                # Stratégie simple : on concatène le texte et on utilise le style du premier span.
                # Une version future plus avancée pourrait dessiner span par span.
                full_text = "".join([s.translated_text if s.translated_text else s.text for s in block.spans])
                
                if block.spans:
                    main_span = block.spans[0]
                    font_path = self.font_manager.get_replacement_font_path(main_span.font.name)
                    
                    if font_path and font_path.exists():
                        font_internal_name = f"F-{font_path.stem.replace(' ', '')}"
                        try:
                            page.insert_textbox(
                                block.final_bbox,
                                full_text,
                                fontsize=main_span.font.size,
                                fontname=font_internal_name,
                                fontfile=str(font_path),
                                color=fitz.utils.hex_color_to_rgb(main_span.font.color)
                            )
                        except Exception as e:
                             self.logger.error(f"Erreur d'insertion de texte pour bloc {block.id}: {e}")
                    else:
                        self.logger.warning(f"Police de remplacement non trouvée pour '{main_span.font.name}', utilisation de Helvetica.")
                        page.insert_textbox(
                            block.final_bbox,
                            full_text,
                            fontsize=main_span.font.size,
                            fontname="helv",
                            color=fitz.utils.hex_color_to_rgb(main_span.font.color)
                        )
        
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.logger.info("Rendu PDF terminé.")
