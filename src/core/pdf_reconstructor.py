#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION FINALE - JALON 1.5 (API Documentée) ***
Utilise page.insert_font() et page.insert_htmlbox() comme documenté.
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
        self.style_to_class_map: Dict[tuple, str] = {}

    def _get_css_for_styles(self, pages: List[PageObject]) -> str:
        """Génère une feuille de style CSS à partir de tous les styles de police uniques."""
        styles = {}
        for page in pages:
            for block in page.text_blocks:
                for span in block.spans:
                    font_info = span.font
                    style_key = (font_info.name, round(font_info.size, 2), font_info.color, font_info.is_bold, font_info.is_italic)
                    
                    if style_key not in styles:
                        font_path = self.font_manager.get_replacement_font_path(font_info.name)
                        if font_path and font_path.exists():
                            styles[style_key] = {
                                'font-family': f"'{font_info.name}'",
                                'font-size': f"{font_info.size}pt",
                                'color': font_info.color,
                                'font-weight': 'bold' if font_info.is_bold else 'normal',
                                'font-style': 'italic' if font_info.is_italic else 'normal'
                            }
                        else:
                            self.debug_logger.warning(f"  !! Police non trouvée pour le style CSS : {font_info.name}")

        css_string = ""
        self.style_to_class_map.clear()
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
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Moteur HTML v1.5) ---")
        doc = fitz.open()

        default_css = self._get_css_for_styles(pages)
        self.debug_logger.info(f"CSS généré pour le document :\n{default_css}")

        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number} / {len(pages)}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            # Enregistrer toutes les polices nécessaires pour CETTE page
            fonts_on_page = set()
            for block in page_data.text_blocks:
                for span in block.spans:
                    fonts_on_page.add(span.font.name)
            
            for font_name in fonts_on_page:
                font_path = self.font_manager.get_replacement_font_path(font_name)
                if font_path and font_path.exists():
                    try:
                        # La méthode correcte pour enregistrer une police pour une page
                        page.insert_font(fontname=font_name, fontfile=str(font_path))
                        self.debug_logger.info(f"  -> Police '{font_name}' enregistrée pour la page {page_data.page_number}")
                    except Exception as e:
                        self.debug_logger.error(f"  !! ERREUR lors de l'enregistrement de la police '{font_name}': {e}")
                else:
                    self.debug_logger.warning(f"  !! Chemin de police non trouvé pour '{font_name}'")

            for block in page_data.text_blocks:
                self.debug_logger.info(f"  > Traitement du TextBlock ID: {block.id}")

                if not block.final_bbox or not block.spans:
                    self.debug_logger.warning(f"    !! BLOC IGNORÉ : final_bbox manquant ou spans vides.")
                    continue
                
                rect = fitz.Rect(block.final_bbox)
                if rect.is_empty:
                    self.debug_logger.error(f"    !! BLOC IGNORÉ : Rectangle invalide.")
                    continue
                
                self.debug_logger.info(f"    - Rectangle de destination (final_bbox): {rect}")

                html_string = ""
                for span in block.spans:
                    class_name = self._get_class_for_span(span)
                    escaped_text = html.escape(span.text).replace("\n", "<br/>")
                    html_string += f'<span class="{class_name}">{escaped_text}</span>'
                
                alignment_style = ["left", "center", "right", "justify"][block.alignment]
                html_string = f'<div style="text-align: {alignment_style}; margin:0; padding:0; line-height: 1.2;">{html_string}</div>'
                
                self.debug_logger.info(f"    - HTML généré pour le bloc : {html_string[:250]}...")

                try:
                    res = page.insert_htmlbox(
                        rect,
                        html_string,
                        css=default_css
                    )
                    self.debug_logger.info(f"    -> Rendu HTML terminé. Texte restant (non inséré) : {res:.2f}")
                except Exception as e:
                    self.debug_logger.error(f"    !! ERREUR sur insert_htmlbox pour le bloc {block.id}: {e}")

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
