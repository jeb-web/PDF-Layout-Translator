#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION DE DIAGNOSTIC - JALON 1.6 (Rollback + Traces) ***
Revient à une méthode de rendu stable et l'instrumente pour analyse.
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

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Rollback + Diagnostic Jalon 1.6) ---")
        doc = fitz.open()

        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            # --- TRACE POINT 1: Enregistrement des polices ---
            self.debug_logger.info("  -> Étape 1: Identification et enregistrement des polices pour la page.")
            fonts_on_page = {span.font.name for block in page_data.text_blocks for span in block.spans}
            self.debug_logger.info(f"    - Polices uniques requises : {fonts_on_page}")
            for font_name in fonts_on_page:
                font_path = self.font_manager.get_replacement_font_path(font_name)
                if font_path and font_path.exists():
                    try:
                        page.insert_font(fontname=font_name, fontfile=str(font_path))
                        self.debug_logger.info(f"      - SUCCÈS : Police '{font_name}' enregistrée depuis '{font_path}'.")
                    except Exception as e:
                        self.debug_logger.error(f"      - ÉCHEC : Erreur d'enregistrement pour la police '{font_name}': {e}")
                else:
                    self.debug_logger.warning(f"      - ATTENTION : Chemin non trouvé pour la police '{font_name}'.")
            self.debug_logger.info("  -> Fin de l'enregistrement des polices.")

            for block in page_data.text_blocks:
                self.debug_logger.info(f"  > Traitement du TextBlock ID: {block.id}")
                if not block.final_bbox or not block.spans:
                    self.debug_logger.warning("    !! BLOC IGNORÉ : final_bbox manquant ou spans vides.")
                    continue
                
                rect = fitz.Rect(block.final_bbox)
                if rect.is_empty:
                    self.debug_logger.error("    !! BLOC IGNORÉ : Rectangle invalide.")
                    continue

                # Création d'un TextWriter pour calculer le reflow
                writer = fitz.TextWriter(page.rect)
                for span in block.spans:
                    font = fitz.Font(fontname=span.font.name) # Utilise la police maintenant enregistrée
                    writer.append((0,0), span.text, font=font, fontsize=span.font.size)
                
                # Simuler le rendu pour obtenir les lignes calculées
                _, _, line_data = writer.fill_textbox(rect, text=None, align=block.alignment)

                # Dessiner le texte ligne par ligne, span par span, avec les bons styles
                shape = page.new_shape()
                for line in line_data["lines"]:
                    for span_info in line["spans"]:
                        # --- TRACE POINT 2 & 3: Vérification des données avant rendu ---
                        try:
                            point = span_info["bbox"].bl
                            text = span_info["text"]
                            fontname = span_info["font"]
                            fontsize = float(span_info["size"])
                            color_hex = span_info["color"]
                            color_rgb = self._hex_to_rgb(color_hex)
                            
                            self.debug_logger.info(f"    - Rendu du span : text='{text}', fontname='{fontname}', fontsize={fontsize}, color={color_rgb}")
                            
                            shape.insert_text(
                                point,
                                text,
                                fontname=fontname,
                                fontsize=fontsize,
                                color=color_rgb
                            )
                        except Exception as e:
                            self.debug_logger.error(f"    !! ERREUR lors de l'appel à shape.insert_text : {e}")
                
                shape.commit()
                self.debug_logger.info(f"    -> Bloc {block.id} dessiné.")

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
