#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION CORRIGÉE - JALON 1.3 (Correction API PyMuPDF) ***
Utilise la méthode de rendu compatible avec la version PyMuPDF du projet.
"""
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import fitz
import html 
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
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Moteur Corrigé v1.3) ---")
        doc = fitz.open()

        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number} / {len(pages)}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            for block in page_data.text_blocks:
                self.debug_logger.info(f"  > Traitement du TextBlock ID: {block.id}")

                if not block.final_bbox or not block.spans:
                    self.debug_logger.warning(f"    !! BLOC IGNORÉ : final_bbox manquant ou spans vides.")
                    continue
                
                rect = fitz.Rect(block.final_bbox)
                if rect.is_empty or rect.width <= 0 or rect.height <= 0:
                    self.debug_logger.error(f"    !! BLOC IGNORÉ : Rectangle invalide. Coordonnées: {block.final_bbox}")
                    continue
                
                self.debug_logger.info(f"    - Rectangle de destination (final_bbox): {rect}")

                # CORRECTION API : Nous n'utilisons plus insert_textbox avec html=True,
                # mais nous revenons à un TextWriter plus contrôlé, qui est compatible.
                writer = fitz.TextWriter(page.rect, color=(0,0,0))
                
                current_pos = fitz.Point(rect.x0, rect.y0 + block.spans[0].font.size) # Position de départ
                
                for span in block.spans:
                    font_path = self.font_manager.get_replacement_font_path(span.font.name)
                    if not font_path or not font_path.exists():
                        self.debug_logger.error(f"      !! Police non trouvée pour le span {span.id}, le texte '{span.text}' sera ignoré.")
                        continue
                        
                    try:
                        font = fitz.Font(fontfile=str(font_path))
                    except Exception as e:
                        self.debug_logger.error(f"      !! ERREUR CHARGEMENT POLICE pour le span {span.id}: {e}")
                        continue

                    # On remplace le marqueur de saut de paragraphe par un vrai saut de ligne
                    text_to_write = span.text.replace('<PARA_BREAK>', '\n')
                    
                    # On remplit la boîte avec le TextWriter, qui gère le reflow
                    writer.fill_textbox(
                        rect,
                        text_to_write,
                        pos=current_pos, # On ne spécifie pas de position initiale pour laisser fill_textbox gérer
                        font=font,
                        fontsize=span.font.size,
                        color=self._hex_to_rgb(span.font.color),
                        align=block.alignment
                    )
                
                self.debug_logger.info(f"    - Écriture du bloc {block.id} dans le PDF...")
                writer.write_text(page)
                self.debug_logger.info("    -> Écriture terminée.")

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
