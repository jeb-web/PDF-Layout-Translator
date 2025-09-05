#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION DE PREUVE FINALE DIAGNOSTIC ***
"""
import logging
from pathlib import Path
from typing import List, Tuple
import fitz  # PyMuPDF
from core.data_model import PageObject
from utils.font_manager import FontManager
from fontTools.ttLib import TTFont # On importe l'outil de test

class PDFReconstructor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager

    def _hex_to_rgb(self, hex_color: str) -> Tuple[float, float, float]:
        hex_color = hex_color.lstrip('#')
        # ... (le reste de la fonction est inchangé) ...
        try:
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError:
            return (0, 0, 0)

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- Début du Rendu PDF (Mode PREUVE FINALE) ---")
        doc = fitz.open()
        
        if not pages:
            doc.new_page(); doc.save(output_path); doc.close()
            return

        page_width, page_height = pages[0].dimensions
        page = doc.new_page(width=page_width, height=page_height)
        
        current_y = 20
        all_blocks = [block for page_data in pages for block in page_data.text_blocks]

        for block in all_blocks:
            if not block.final_bbox or not block.spans:
                continue

            block_height = block.final_bbox[3] - block.final_bbox[1]
            if block_height <= 0: continue

            if current_y + block_height + 60 > page_height: # Marge pour le texte de debug
                page = doc.new_page(width=page_width, height=page_height)
                current_y = 20

            debug_bbox = fitz.Rect(block.bbox[0], current_y, block.bbox[0] + (block.final_bbox[2] - block.final_bbox[0]), current_y + block_height)

            page.draw_rect(debug_bbox, color=(1, 0, 0), width=0.5)
            
            # --- TEST DE DIAGNOSTIC INTÉGRÉ ---
            font_path = self.font_manager.get_replacement_font_path(block.spans[0].font.name)
            diagnostic_message = ""
            diagnostic_color = (1, 0, 0) # Rouge par défaut (échec)

            if font_path and font_path.exists():
                try:
                    # On simule ici l'analyse exacte que fait le LayoutProcessor
                    font = TTFont(font_path)
                    diagnostic_message = f"SUCCÈS: fontTools a analysé '{font_path.name}'."
                    diagnostic_color = (0, 0, 1) # Bleu pour succès
                except Exception as e:
                    diagnostic_message = f"ÉCHEC: fontTools n'a pas pu analyser '{font_path.name}'. Erreur: {e}"
            else:
                diagnostic_message = "ÉCHEC: Aucune police de remplacement trouvée."
            # --- FIN DU TEST ---

            full_text = "".join([s.text for s in block.spans])
            
            diagnostic_text_block = (
                f"ID: {block.id}\n"
                f"Taille Calculée: {debug_bbox.width:.1f}w x {debug_bbox.height:.1f}h\n"
                f"Contenu Tenté: \"{full_text}\"\n"
                f"--- DIAGNOSTIC ---\n{diagnostic_message}"
            )
            
            diag_pos = fitz.Point(debug_bbox.x1 + 5, debug_bbox.y0)
            page.insert_textbox(
                fitz.Rect(diag_pos, diag_pos + (250, 60)),
                diagnostic_text_block,
                fontsize=6,
                fontname="helv",
                color=diagnostic_color
            )
            
            # On tente toujours d'insérer le texte pour voir le résultat
            try:
                if diagnostic_color == (0, 0, 1): # Si le test a réussi
                    page.insert_textbox(debug_bbox, full_text, fontsize=block.spans[0].font.size, fontfile=str(font_path))
            except Exception as e:
                self.debug_logger.error(f"Erreur d'insertion pour {block.id}: {e}")

            current_y += max(block_height, 60) + 15

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"--- Rendu PDF de PREUVE FINALE terminé. Fichier: {output_path} ---")
