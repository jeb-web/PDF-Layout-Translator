#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION DE DÉBOGAGE INSTRUMENTÉE - JALON 1.0 (DIAGNOSTIC) ***
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
        self.font_object_cache: Dict[Path, fitz.Font] = {}

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
        self.debug_logger.info(f"        Font lookup for: '{font_name}'")
        font_path = self.font_manager.get_replacement_font_path(font_name)
        
        if not (font_path and font_path.exists()):
            self.debug_logger.error(f"        !! ÉCHEC: Police non trouvée ou chemin invalide pour '{font_name}'. Path: {font_path}")
            return None
        
        self.debug_logger.info(f"        -> Chemin de police trouvé : {font_path}")

        if font_path in self.font_object_cache:
            self.debug_logger.info("        -> Police trouvée dans le cache.")
            return self.font_object_cache[font_path]
        
        try:
            self.debug_logger.info(f"        -> Tentative de chargement de la police depuis le fichier...")
            font = fitz.Font(fontfile=str(font_path))
            self.font_object_cache[font_path] = font
            self.debug_logger.info("        -> Police chargée et mise en cache avec succès.")
            return font
        except Exception as e:
            self.debug_logger.error(f"        !! ERREUR FATALE: Impossible de charger l'objet police depuis {font_path}: {e}")
            return None

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (MODE DIAGNOSTIC) ---")
        doc = fitz.open()
        self.font_object_cache.clear()

        if not pages:
            self.debug_logger.warning("Aucune page à traiter. Le document sera vide.")
        
        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number} / {len(pages)}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            if not page_data.text_blocks:
                self.debug_logger.info("  -> Cette page ne contient aucun bloc de texte.")
                continue

            for block in page_data.text_blocks:
                self.debug_logger.info(f"  > Traitement du TextBlock ID: {block.id}")

                if not block.final_bbox or not block.spans:
                    self.debug_logger.warning(f"    !! BLOC IGNORÉ : final_bbox manquant ou spans vides. final_bbox: {block.final_bbox}, Spans: {len(block.spans)}")
                    continue
                
                rect = fitz.Rect(block.final_bbox)
                if rect.is_empty or rect.width <= 0 or rect.height <= 0:
                    self.debug_logger.error(f"    !! BLOC IGNORÉ : Le rectangle final_bbox est invalide ou de taille nulle. Coordonnées: {block.final_bbox}")
                    continue

                self.debug_logger.info(f"    - Rectangle de destination (final_bbox): {rect}")
                writer = fitz.TextWriter(page.rect)
                span_count = len(block.spans)

                for i, span in enumerate(block.spans):
                    self.debug_logger.info(f"      - Traitement du Span {i+1}/{span_count} (ID: {span.id}), Texte: '{span.text}'")
                    
                    font = self._get_font(span.font.name)
                    if not font:
                        self.debug_logger.error(f"      !! Police non chargée pour le span {span.id}. Ce fragment de texte sera ignoré.")
                        continue
                    
                    writer.append(
                        (0, 0),
                        span.text,
                        font=font,
                        fontsize=span.font.size,
                        color=self._hex_to_rgb(span.font.color)
                    )
                    self.debug_logger.info("      -> Span ajouté au buffer du TextWriter.")

                if writer.buffer and writer.buffer.text.strip():
                    self.debug_logger.info(f"    - Écriture du bloc {block.id} dans le PDF...")
                    writer.fill_textbox(rect, align=block.alignment)
                    self.debug_logger.info("    -> Écriture terminée.")
                else:
                    self.debug_logger.warning(f"    !! Le buffer du TextWriter est vide pour le bloc {block.id}. Rien à écrire.")

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
