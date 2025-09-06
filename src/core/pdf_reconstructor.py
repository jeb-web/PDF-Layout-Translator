#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION DE TEST - Jalon 2.5 (Correction Formatage via Reflow Data) ***
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
        self.font_object_cache: Dict[str, fitz.Font] = {}

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

    def _get_font(self, font_name: str) -> fitz.Font:
        if font_name in self.font_object_cache:
            return self.font_object_cache[font_name]
        
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if not (font_path and font_path.exists()):
            self.debug_logger.error(f"      !! _get_font: Chemin non trouvé pour la police '{font_name}'.")
            return None
        
        try:
            font = fitz.Font(fontfile=str(font_path))
            self.font_object_cache[font_name] = font
            return font
        except Exception as e:
            self.debug_logger.error(f"      !! _get_font: Erreur de chargement pour la police '{font_name}' depuis '{font_path}': {e}")
            return None

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Jalon 2.5) ---")
        doc = fitz.open()
        self.font_object_cache.clear()

        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            for block in page_data.text_blocks:
                self.debug_logger.info(f"  > Traitement du TextBlock ID: {block.id}")
                if not block.final_bbox or not block.spans: continue
                
                rect = fitz.Rect(block.final_bbox)
                if rect.is_empty: continue

                # Étape 1 : Utiliser un TextWriter pour calculer le reflow et obtenir les données de positionnement
                writer = fitz.TextWriter(page.rect)
                for span in block.spans:
                    font = self._get_font(span.font.name)
                    if font:
                        # Remplir le buffer du writer avec le texte et les styles
                        writer.append(
                            pos=(0,0), # Position factice, sera recalculée
                            text=span.text, 
                            font=font, 
                            fontsize=span.font.size,
                            color=self._hex_to_rgb(span.font.color) # Couleur nécessaire pour les données de ligne
                        )

                try:
                    # 'morph=None' force la fonction à ne rien dessiner, seulement à calculer les positions.
                    # C'est l'étape de "calcul du plan de rendu".
                    _, _, line_data = writer.fill_textbox(rect, text=None, align=block.alignment, morph=None)
                    self.debug_logger.info(f"    - Calcul du reflow pour le bloc {block.id} réussi.")
                except Exception as e:
                    self.debug_logger.error(f"    !! ERREUR dans writer.fill_textbox pour bloc {block.id}: {e}")
                    continue

                # Étape 2 : Dessiner le texte en utilisant le plan de rendu calculé
                shape = page.new_shape()
                for line in line_data.get("lines", []):
                    for span_info in line.get("spans", []):
                        try:
                            # Utiliser le BBOX calculé par le reflow pour chaque span
                            span_rect = span_info["bbox"]
                            text = span_info["text"]
                            font_name = span_info["font"]
                            fontsize = float(span_info["size"])
                            color_rgb = span_info["color"]
                            
                            self.debug_logger.info(f"    - Rendu du span : text='{text}'")
                            self.debug_logger.info(f"      -> DANS RECTANGLE : {span_rect}")
                            self.debug_logger.info(f"      -> AVEC STYLE : font='{font_name}', size={fontsize}, color={color_rgb}")

                            # Insérer le texte dans son propre rectangle précis
                            rc = shape.insert_textbox(
                                span_rect,
                                text,
                                fontname=font_name,
                                fontsize=fontsize,
                                color=color_rgb,
                                align=fitz.TEXT_ALIGN_LEFT # L'alignement global est déjà géré par les coordonnées
                            )
                            if rc < 0:
                                self.debug_logger.warning(f"      -> Surplus de texte de {rc:.2f} pour le span '{text}'")

                        except Exception as e:
                            self.debug_logger.error(f"    !! ERREUR lors de l'appel à shape.insert_textbox : {e}")
                
                shape.commit()
                self.debug_logger.info(f"    -> Bloc {block.id} dessiné.")

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
