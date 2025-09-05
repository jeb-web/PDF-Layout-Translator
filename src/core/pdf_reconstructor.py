#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION DE PREUVE DIAGNOSTIC ***
"""
import logging
from pathlib import Path
from typing import List, Tuple
import fitz  # PyMuPDF
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
        self.debug_logger.info("--- Début du Rendu PDF (Mode PREUVE DIAGNOSTIC) ---")
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

            if current_y + block_height + 50 > page_height: # 50 de marge pour le texte de debug
                page = doc.new_page(width=page_width, height=page_height)
                current_y = 20

            debug_bbox = fitz.Rect(block.bbox[0], current_y, block.bbox[0] + (block.final_bbox[2] - block.final_bbox[0]), current_y + block_height)

            # --- PREUVE N°1 : DESSINER LA BOÎTE TROP PETITE ---
            page.draw_rect(debug_bbox, color=(1, 0, 0), width=0.5)

            # --- PREUVE N°2 : AFFICHER LES DONNÉES DE DIAGNOSTIC ---
            full_text = "".join([s.text for s in block.spans]) # Bug de concaténation
            font_path = self.font_manager.get_replacement_font_path(block.spans[0].font.name)
            
            bbox_width = debug_bbox.width
            bbox_height = debug_bbox.height
            
            diagnostic_text = (
                f"ID: {block.id}\n"
                f"Taille Calculée: {bbox_width:.1f}w x {bbox_height:.1f}h\n"
                f"Police Tentée: {font_path.name if font_path else 'Aucune'}\n"
                f"Contenu (Bug N°2): \"{full_text}\""
            )
            
            # On place le texte de diagnostic à côté de la boîte
            diag_pos = fitz.Point(debug_bbox.x1 + 5, debug_bbox.y0)
            page.insert_textbox(
                fitz.Rect(diag_pos, diag_pos + (200, 50)),
                diagnostic_text,
                fontsize=6,
                fontname="helv", # On utilise une police sûre
                color=(0, 0, 1) # En bleu pour bien le voir
            )
            
            # On tente d'insérer le texte dans la boîte rouge (ce qui va échouer)
            try:
                page.insert_textbox(debug_bbox, full_text, fontsize=block.spans[0].font.size, fontfile=str(font_path) if font_path else None)
            except Exception as e:
                self.debug_logger.error(f"Erreur d'insertion pour {block.id}: {e}")

            current_y += block_height + 50 # Marge plus grande pour la lisibilité

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"--- Rendu PDF de PREUVE terminé. Fichier: {output_path} ---")
