#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION CORRIGÉE - JALON 1.1 (Correction API) ***
Utilise insert_textbox(html=True) pour le rendu multi-styles.
"""
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import fitz
import html # Pour échapper le texte
from core.data_model import PageObject
from utils.font_manager import FontManager

class PDFReconstructor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager
        # NOTE : Le cache des polices n'est plus géré ici car insert_textbox le gère en interne.

    def _get_css_for_styles(self, pages: List[PageObject]) -> str:
        """Génère une feuille de style CSS à partir de tous les styles de police uniques."""
        styles = {}
        for page in pages:
            for block in page.text_blocks:
                for span in block.spans:
                    font_info = span.font
                    # Utiliser un identifiant stable pour chaque style unique
                    style_key = (font_info.name, round(font_info.size, 2), font_info.color, font_info.is_bold, font_info.is_italic)
                    if style_key not in styles:
                        styles[style_key] = {
                            'name': font_info.name,
                            'font-family': font_info.name,
                            'font-size': f"{font_info.size}pt",
                            'color': font_info.color,
                            'font-weight': 'bold' if font_info.is_bold else 'normal',
                            'font-style': 'italic' if font_info.is_italic else 'normal'
                        }
        
        # Créer les classes CSS
        css_string = ""
        self.style_to_class_map = {}
        for i, (style_key, style_attrs) in enumerate(styles.items()):
            class_name = f"style_{i}"
            self.style_to_class_map[style_key] = class_name
            css_string += f".{class_name} {{ "
            for attr, value in style_attrs.items():
                css_string += f"{attr}: {value}; "
            css_string += "}\n"
        
        return css_string

    def _get_class_for_span(self, span) -> str:
        """Récupère le nom de la classe CSS pour un span donné."""
        font_info = span.font
        style_key = (font_info.name, round(font_info.size, 2), font_info.color, font_info.is_bold, font_info.is_italic)
        return self.style_to_class_map.get(style_key, "")

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Moteur HTML) ---")
        doc = fitz.open()

        # Enregistrer toutes les polices nécessaires au document
        for page in pages:
            for block in page.text_blocks:
                for span in block.spans:
                    font_path = self.font_manager.get_replacement_font_path(span.font.name)
                    if font_path and font_path.exists():
                        # Cette étape est cruciale pour que PyMuPDF connaisse la police
                        doc.add_font(fontname=span.font.name, fontfile=str(font_path))

        # Générer une feuille de style CSS unique pour tout le document
        default_css = self._get_css_for_styles(pages)
        self.debug_logger.info(f"CSS généré pour le document :\n{default_css}")

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

                # NOUVELLE LOGIQUE : Construire une chaîne HTML à partir des spans
                html_string = ""
                for span in block.spans:
                    class_name = self._get_class_for_span(span)
                    # Échapper le texte pour éviter les problèmes avec des caractères comme < > &
                    escaped_text = html.escape(span.text)
                    html_string += f'<span class="{class_name}">{escaped_text}</span>'
                
                # Encapsuler dans une balise de paragraphe pour que l'alignement fonctionne
                # L'alignement CSS est plus fiable
                alignment_style = ["left", "center", "right", "justify"][block.alignment]
                html_string = f'<p style="text-align: {alignment_style}; margin:0; padding:0;">{html_string}</p>'
                
                self.debug_logger.info(f"    - HTML généré pour le bloc : {html_string[:200]}...")

                # Utiliser insert_textbox avec l'option html=True
                res = page.insert_textbox(
                    rect,
                    html_string,
                    html=True,
                    css=default_css
                )
                self.debug_logger.info(f"    -> Rendu HTML terminé. Texte restant (non inséré) : {res:.2f} (plus c'est proche de 0, mieux c'est)")

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
