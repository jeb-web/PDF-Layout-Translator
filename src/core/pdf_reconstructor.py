#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION FINALE ET STABLE ***
Utilise une méthode de rendu TextWriter éprouvée et compatible.
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
        """Charge une police depuis le cache ou le disque."""
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if not (font_path and font_path.exists()):
            self.debug_logger.error(f"        !! Police non trouvée pour '{font_name}'")
            return None
        
        if font_path in self.font_object_cache:
            return self.font_object_cache[font_path]
        
        try:
            font = fitz.Font(fontfile=str(font_path))
            self.font_object_cache[font_path] = font
            return font
        except Exception as e:
            self.debug_logger.error(f"        !! ERREUR CHARGEMENT POLICE {font_path}: {e}")
            return None

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Moteur TextWriter Stable) ---")
        doc = fitz.open()
        self.font_object_cache.clear()

        for page_data in pages:
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            for block in page_data.text_blocks:
                self.debug_logger.info(f"  > Traitement du TextBlock ID: {block.id}")

                if not block.final_bbox or not block.spans:
                    self.debug_logger.warning(f"    !! BLOC IGNORÉ : final_bbox manquant ou spans vides.")
                    continue
                
                rect = fitz.Rect(block.final_bbox)
                if rect.is_empty:
                    self.debug_logger.error(f"    !! BLOC IGNORÉ : Rectangle invalide.")
                    continue
                
                # LA BONNE MÉTHODE : Utiliser TextWriter pour assembler, puis écrire.
                # On ne peut pas utiliser fill_textbox pour du texte multi-style.
                # On doit insérer le texte manuellement.
                
                # On utilise un shape pour dessiner le texte afin de pouvoir le "clipper"
                # au rectangle, évitant ainsi les débordements.
                shape = page.new_shape()

                # On assemble tout le texte dans un seul grand TextWriter
                full_text = ""
                for span in block.spans:
                    full_text += span.text

                # On utilise fill_textbox sur le TextWriter pour calculer le reflow
                # mais on ne l'écrit pas directement.
                temp_writer = fitz.TextWriter(page.rect)
                
                for span in block.spans:
                    font_object = self._get_font(span.font.name)
                    if font_object:
                        temp_writer.append(
                            (0,0), # La position est factice, on ne s'en sert pas
                            span.text,
                            font=font_object,
                            fontsize=span.font.size
                        )

                # Maintenant, on utilise fill_textbox pour simuler le rendu et obtenir les lignes
                # C'est une astuce pour laisser PyMuPDF faire le calcul complexe du reflow.
                # La valeur "text" est None car on utilise le buffer du writer.
                _, _, line_data = temp_writer.fill_textbox(rect, text=None, align=block.alignment, morph=None)

                # Enfin, on dessine le texte ligne par ligne avec les bons styles
                for line in line_data["lines"]:
                    for span_info in line["spans"]:
                        font = self._get_font(span_info["font"])
                        if font:
                            shape.insert_text(
                                span_info["bbox"].bl, # Position du point de base
                                span_info["text"],
                                fontname=font.name,
                                fontsize=span_info["size"],
                                color=self._hex_to_rgb(span_info["color"])
                            )

                shape.commit()


        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
