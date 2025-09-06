#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION FINALE - Jalon 2.7 (Gestion Correcte de la Position Verticale) ***
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
        self.font_cache: Dict[str, fitz.Font] = {}

    def _get_font(self, font_name: str) -> fitz.Font:
        """Charge une police et la met en cache pour éviter les relectures disque."""
        if font_name in self.font_cache:
            return self.font_cache[font_name]
        
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if font_path and font_path.exists():
            try:
                font_buffer = font_path.read_bytes()
                font = fitz.Font(fontbuffer=font_buffer)
                self.font_cache[font_name] = font
                return font
            except Exception as e:
                self.debug_logger.error(f"Erreur de chargement de la police {font_path}: {e}")
        
        return fitz.Font()


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
        font = self._get_font(font_name)
        return font.text_length(text, fontsize=font_size)

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Jalon 2.7 - Finale) ---")
        doc = fitz.open()
        self.font_cache.clear()

        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            fonts_on_page = {span.font.name for block in page_data.text_blocks for span in block.spans}
            for font_name in fonts_on_page:
                self._get_font(font_name)
                font_path = self.font_manager.get_replacement_font_path(font_name)
                if font_path and font_path.exists():
                    try:
                        page.insert_font(fontname=font_name, fontfile=str(font_path))
                    except Exception as e:
                        self.debug_logger.error(f"  -> ERREUR enregistrement police '{font_name}': {e}")

            for block in page_data.text_blocks:
                if not block.final_bbox or not block.paragraphs:
                    continue

                start_x = block.final_bbox[0]
                current_y = block.final_bbox[1]
                block_width = block.bbox[2] - block.bbox[0]
                
                self.debug_logger.info(f"  > Rendu du bloc {block.id} (Largeur: {block_width:.2f}) à y={current_y:.2f}")

                shape = page.new_shape()
                
                for i, para in enumerate(block.paragraphs):
                    if not para.spans:
                        continue
                    
                    self.debug_logger.info(f"    -> Traitement du Paragraphe {para.id}")

                    # PASSE 1: Organiser les mots en lignes
                    lines = []
                    current_line_words = []
                    current_x_layout = start_x
                    para_words = []
                    for span in para.spans:
                        text_with_markers = span.text.replace('\n', ' <PARA_BREAK> ')
                        words = text_with_markers.split(' ')
                        for word in words:
                            if word:
                                para_words.append((word, span))
                    
                    if not para_words: continue

                    for word, span in para_words:
                        width_with_space = self._get_text_width(word + ' ', span.font.name, span.font.size)
                        if current_line_words and current_x_layout + width_with_space > start_x + block_width:
                            lines.append(current_line_words)
                            current_line_words = []
                            current_x_layout = start_x
                        
                        current_line_words.append((word, span))
                        current_x_layout += width_with_space
                    
                    if current_line_words:
                        lines.append(current_line_words)

                    # PASSE 2: Dessiner chaque ligne avec un alignement par ligne de base
                    y_line_start = current_y # Position de départ pour la première ligne de CE paragraphe

                    for line_words in lines:
                        max_ascender = 0
                        max_line_height = 0

                        for word, span in line_words:
                            font = self._get_font(span.font.name)
                            ascender = font.ascender * span.font.size
                            descender = abs(font.descender * span.font.size)
                            if ascender > max_ascender:
                                max_ascender = ascender
                            if (ascender + descender) > max_line_height:
                                max_line_height = ascender + descender
                        
                        if not max_line_height: continue

                        y_baseline = y_line_start + max_ascender
                        self.debug_logger.info(f"      Ligne à y={y_line_start:.2f}, Baseline calculée à y={y_baseline:.2f}, Hauteur de ligne: {max_line_height:.2f}")
                        
                        current_x_draw = start_x
                        for word, span in line_words:
                            font = self._get_font(span.font.name)
                            word_ascender = font.ascender * span.font.size
                            y0 = y_baseline - word_ascender

                            width_with_space = self._get_text_width(word + ' ', span.font.name, span.font.size)
                            word_width_only = self._get_text_width(word, span.font.name, span.font.size)

                            if word_width_only <= 0: continue

                            word_rect = fitz.Rect(current_x_draw, y0, current_x_draw + word_width_only, y0 + max_line_height)
                            
                            shape.insert_textbox(
                                word_rect, word,
                                fontname=span.font.name,
                                fontsize=span.font.size,
                                color=self._hex_to_rgb(span.font.color),
                                align=fitz.TEXT_ALIGN_LEFT
                            )
                            current_x_draw += width_with_space
                        
                        # Mettre à jour la position pour la prochaine ligne DANS ce paragraphe
                        y_line_start += max_line_height * 1.2
                    
                    # Mettre à jour la position verticale principale pour le PROCHAIN paragraphe
                    current_y = y_line_start
                
                shape.commit()

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
