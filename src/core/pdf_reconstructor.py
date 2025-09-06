#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION FINALE ET COHÉRENTE ***
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
        self.font_archive_data: Dict[str, bytes] = {}

    def _get_css_for_styles(self, pages: List[PageObject]) -> str:
        """Génère une feuille de style CSS et prépare les données des polices."""
        styles = {}
        self.font_archive_data.clear()

        for page in pages:
            for block in page.text_blocks:
                for span in block.spans:
                    font_info = span.font
                    style_key = (font_info.name, round(font_info.size, 2), font_info.color, font_info.is_bold, font_info.is_italic)
                    
                    if style_key not in styles:
                        font_path = self.font_manager.get_replacement_font_path(font_info.name)
                        if font_path and font_path.exists():
                            font_name_in_css = font_info.name
                            if font_name_in_css not in self.font_archive_data:
                                try:
                                    self.font_archive_data[font_name_in_css] = font_path.read_bytes()
                                except Exception as e:
                                    self.debug_logger.error(f"!! ERREUR LECTURE FICHIER POLICE {font_path}: {e}")
                                    continue
                            
                            styles[style_key] = {
                                'font-family': f"'{font_name_in_css}'",
                                'font-size': f"{font_info.size}pt",
                                'color': font_info.color, # Cette valeur est déjà une chaîne hexadécimale
                                'font-weight': 'bold' if font_info.is_bold else 'normal',
                                'font-style': 'italic' if font_info.is_italic else 'normal'
                            }

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
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Version finale) ---")
        doc = fitz.open()

        default_css = self._get_css_for_styles(pages)

        archive = fitz.Archive()
        for font_name, font_data in self.font_archive_data.items():
            archive.insert_file(arcname=font_name, buffer=font_data)

        for page_data in pages:
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            for block in page_data.text_blocks:
                if not block.final_bbox or not block.spans:
                    continue
                
                rect = fitz.Rect(block.final_bbox)
                if rect.is_empty:
                    continue
                
                html_string = ""
                for span in block.spans:
                    class_name = self._get_class_for_span(span)
                    escaped_text = html.escape(span.text).replace("\n", "<br/>")
                    html_string += f'<span class="{class_name}">{escaped_text}</span>'
                
                alignment_style = ["left", "center", "right", "justify"][block.alignment]
                html_string = f'<div style="text-align: {alignment_style}; margin:0; padding:0; line-height: 1.2;">{html_string}</div>'
                
                page.insert_htmlbox(
                    rect,
                    html_string,
                    css=default_css,
                    archive=archive
                )

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"--- PDF sauvegardé avec succès : {output_path} ---")
