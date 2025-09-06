#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION CORRIGÉE - JALON 1 ***
Utilise TextWriter pour gérer correctement les paragraphes multi-styles.
"""
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import fitz
from core.data_model import PageObject, TextSpan, FontInfo
from utils.font_manager import FontManager

class PDFReconstructor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager
        # Le cache doit stocker les objets fitz.Font, pas les buffers
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
        """Charge une police depuis le cache ou le disque."""
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if not (font_path and font_path.exists()):
            self.logger.warning(f"Police non trouvée, impossible de la charger : {font_name}")
            return None
        
        if font_path in self.font_object_cache:
            return self.font_object_cache[font_path]
        
        try:
            # Charger et mettre en cache l'objet fitz.Font
            font = fitz.Font(fontfile=str(font_path))
            self.font_object_cache[font_path] = font
            return font
        except Exception as e:
            self.logger.error(f"Impossible de charger la police {font_path}: {e}")
            return None

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- Démarrage de PDFReconstructor (Moteur Corrigé) ---")
        doc = fitz.open()
        self.font_object_cache.clear()

        for page_data in pages:
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            for block in page_data.text_blocks:
                if not block.final_bbox or not block.spans:
                    continue

                # Créer le rectangle (la "grande boîte") pour le paragraphe entier
                rect = fitz.Rect(block.final_bbox)
                
                # NOUVELLE LOGIQUE : Utiliser TextWriter pour assembler le paragraphe
                # TextWriter est conçu pour gérer des fragments de texte avec des styles différents.
                writer = fitz.TextWriter(page.rect)
                
                # On assemble le texte stylé à l'intérieur du writer
                for span in block.spans:
                    font = self._get_font(span.font.name)
                    if not font:
                        self.debug_logger.error(f"Police introuvable pour le span {span.id}, le texte '{span.text}' ne sera pas rendu.")
                        continue
                    
                    # On ajoute chaque span au writer avec son propre style.
                    # Le writer gère le positionnement et le retour à la ligne.
                    writer.append(
                        (0, 0),  # La position est gérée par fill_textbox
                        span.text,
                        font=font,
                        fontsize=span.font.size,
                        color=self._hex_to_rgb(span.font.color)
                    )

                # On écrit le contenu assemblé par le writer dans la "grande boîte"
                # L'alignement est appliqué à l'ensemble du bloc.
                try:
                    writer.fill_textbox(
                        rect,
                        align=block.alignment
                    )
                except Exception as e:
                    self.debug_logger.error(f"Erreur lors de l'écriture du bloc {block.id}: {e}")


        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- Fin de PDFReconstructor ---")
