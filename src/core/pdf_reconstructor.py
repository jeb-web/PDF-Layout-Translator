#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION CORRIGÉE - Jalon 2.3 (Reflow par Paragraphe) ***
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

    def _get_text_width(self, text: str, font_name: str, font_size: float) -> float:
        """Calcule la largeur du texte avec une police spécifique, comme dans LayoutProcessor."""
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if font_path and font_path.exists():
            try:
                font_buffer = font_path.read_bytes()
                font = fitz.Font(fontbuffer=font_buffer)
                return font.text_length(text, fontsize=font_size)
            except Exception as e:
                self.debug_logger.error(f"Erreur de mesure Fitz pour la police {font_path}: {e}")
        return len(text) * font_size * 0.6

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Jalon 2.3 - Reflow par Paragraphe) ---")
        doc = fitz.open()

        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            fonts_on_page = {span.font.name for block in page_data.text_blocks for span in block.spans}
            for font_name in fonts_on_page:
                font_path = self.font_manager.get_replacement_font_path(font_name)
                if font_path and font_path.exists():
                    try:
                        page.insert_font(fontname=font_name, fontfile=str(font_path))
                    except Exception as e:
                        self.debug_logger.error(f"  -> ERREUR enregistrement police '{font_name}': {e}")

            for block in page_data.text_blocks:
                if not block.final_bbox or not block.paragraphs:
                    continue

                # Utiliser la position de départ du final_bbox, mais la largeur originale du bloc
                start_x = block.final_bbox[0]
                current_y = block.final_bbox[1]
                block_width = block.bbox[2] - block.bbox[0]
                
                self.debug_logger.info(f"  > Rendu du bloc {block.id} (Largeur: {block_width:.2f}) à y={current_y:.2f}")

                shape = page.new_shape()
                
                max_font_size_in_line = 0
                
                # Itérer sur les paragraphes pour respecter la structure
                for i, para in enumerate(block.paragraphs):
                    if not para.spans:
                        continue
                    
                    self.debug_logger.info(f"    -> Traitement du Paragraphe {para.id}")

                    # Ajouter un espacement vertical avant le nouveau paragraphe (sauf le premier)
                    if i > 0 and max_font_size_in_line > 0:
                        current_y += max_font_size_in_line * 0.4 

                    current_x = start_x
                    max_font_size_in_line = para.spans[0].font.size

                    # Créer la liste de mots pour ce paragraphe
                    para_words = []
                    for span in para.spans:
                        words = span.text.replace('\n', ' <PARA_BREAK> ').split(' ')
                        for word in words:
                            if word:
                                para_words.append((word, span))
                    
                    # Rendu mot par mot du paragraphe
                    for word, span in para_words:
                        if span.font.size > max_font_size_in_line:
                            max_font_size_in_line = span.font.size

                        if word == '<PARA_BREAK>':
                            current_y += max_font_size_in_line * 1.2
                            current_x = start_x
                            max_font_size_in_line = span.font.size # Réinitialiser pour la nouvelle ligne
                            continue

                        word_width = self._get_text_width(word, span.font.name, span.font.size)
                        space_width = self._get_text_width(' ', span.font.name, span.font.size)

                        if current_x + word_width > start_x + block_width and current_x > start_x:
                            current_y += max_font_size_in_line * 1.2
                            current_x = start_x
                            # La taille de la police pour la nouvelle ligne sera mise à jour par le mot actuel
                            max_font_size_in_line = span.font.size

                        word_rect = fitz.Rect(current_x, current_y, current_x + word_width, current_y + max_font_size_in_line * 1.5)
                        
                        self.debug_logger.info(f"      - Mot '{word}' dans {word_rect}")
                        
                        rc = shape.insert_textbox(
                            word_rect,
                            word,
                            fontname=span.font.name,
                            fontsize=span.font.size,
                            color=self._hex_to_rgb(span.font.color),
                            align=fitz.TEXT_ALIGN_LEFT
                        )
                        if rc < 0 :
                             self.debug_logger.warning(f"        !! Le mot '{word}' a débordé de sa boîte de {abs(rc):.2f} unités.")

                        current_x += word_width + space_width
                
                shape.commit()

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
