#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION DE DÉBOGAGE - JALON 1.9 (Méthode Sûre et Traces) ***
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
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Jalon 1.9) ---")
        doc = fitz.open()

        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            # Enregistrer les polices nécessaires pour la page
            fonts_on_page = {span.font.name for block in page_data.text_blocks for span in block.spans}
            for font_name in fonts_on_page:
                font_path = self.font_manager.get_replacement_font_path(font_name)
                if font_path and font_path.exists():
                    try:
                        page.insert_font(fontname=font_name, fontfile=str(font_path))
                        self.debug_logger.info(f"  -> Police '{font_name}' enregistrée pour la page.")
                    except Exception as e:
                        self.debug_logger.error(f"  -> ERREUR enregistrement police '{font_name}': {e}")

            for block in page_data.text_blocks:
                self.debug_logger.info(f"  > Traitement du TextBlock ID: {block.id}")
                if not block.final_bbox or not block.spans: continue
                
                # On utilise un shape pour dessiner, ce qui est plus fiable
                shape = page.new_shape()
                
                # Logique de positionnement manuel à l'intérieur du bloc
                current_y = block.final_bbox[1]
                
                for para in block.paragraphs:
                    line_height = max(span.font.size for span in para.spans) * 1.2 if para.spans else 12
                    
                    # Définir un rectangle pour ce paragraphe
                    para_rect = fitz.Rect(block.final_bbox[0], current_y, block.final_bbox[2], current_y + (line_height * 50)) # Hauteur arbitrairement grande

                    # On utilise un TextWriter juste pour le calcul du reflow de ce paragraphe
                    writer = fitz.TextWriter(para_rect)
                    for span in para.spans:
                        font = fitz.Font(fontname=span.font.name)
                        writer.append(pos=(block.final_bbox[0], current_y), text=span.text, font=font, fontsize=span.font.size)
                    
                    try:
                        # On utilise write_text qui ne retourne pas d'erreur si la boîte est trop petite
                        writer.write_text(page, rect=para_rect, align=block.alignment)
                        
                        # TRACE : Afficher ce qui a été tenté
                        self.debug_logger.info(f"    - Tentative d'écriture du bloc {block.id} dans le rect {para_rect}")
                        for span in para.spans:
                             self.debug_logger.info(f"      - Span : '{span.text}', Font: '{span.font.name}'")
                        
                        # Approximation de la hauteur utilisée pour le prochain paragraphe
                        # Ceci sera à affiner au prochain jalon
                        current_y += writer.text_rect.height if writer.text_rect else line_height

                    except Exception as e:
                        self.debug_logger.error(f"    !! ERREUR dans writer.write_text pour bloc {block.id}: {e}")

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
