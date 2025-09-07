#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** NOUVELLE VERSION v2.3 - Robuste et Structuré par Paragraphe ***
"""
import logging
from typing import List
import fitz
import copy
from core.data_model import PageObject, TextSpan, Paragraph
from utils.font_manager import FontManager

class LayoutProcessor:
    def __init__(self, font_manager: FontManager):
        # ... (init et _get_text_width restent identiques) ...
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager

    def _get_text_width(self, text: str, font_name: str, font_size: float) -> float:
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if font_path and font_path.exists():
            try:
                font_buffer = font_path.read_bytes()
                font = fitz.Font(fontbuffer=font_buffer)
                return font.text_length(text, fontsize=font_size)
            except Exception as e:
                self.debug_logger.error(f"Erreur de mesure Fitz pour la police {font_path}: {e}")
        return len(text) * font_size * 0.6

    def process_pages(self, pages: List[PageObject]) -> List[PageObject]:
        self.debug_logger.info("--- DÉMARRAGE LAYOUTPROCESSOR (v2.3 - Robuste) ---")
        for page in pages:
            self.debug_logger.info(f"  > Traitement de la Page {page.page_number}")
            for block in page.text_blocks:
                self.debug_logger.info(f"    -> Calcul du reflow pour le bloc {block.id}")
                
                all_new_spans_for_block = []
                # Le Y de départ est le haut du bloc. Chaque paragraphe le fera avancer.
                current_y = block.bbox[1]
                
                for para in block.paragraphs:
                    self.debug_logger.info(f"       - Traitement du paragraphe {para.id} (Liste: {para.is_list_item})")
                    if not para.spans:
                        continue

                    x_start = block.bbox[0]
                    block_width = block.bbox[2] - x_start
                    
                    x_text_start = x_start
                    max_font_size_in_line = para.spans[0].font.size
                    
                    content_spans = para.spans
                    
                    if para.is_list_item:
                        marker_span = para.spans[0]
                        marker_width = self._get_text_width(marker_span.text, marker_span.font.name, marker_span.font.size)
                        
                        new_marker_span = copy.deepcopy(marker_span)
                        new_marker_span.final_bbox = (x_start, current_y, x_start + marker_width, current_y + marker_span.font.size * 1.2)
                        all_new_spans_for_block.append(new_marker_span)
                        
                        x_text_start = para.text_indent
                        current_x = x_text_start
                        content_spans = para.spans[1:]
                        self.debug_logger.info(f"         > Item de liste. Marqueur: '{marker_span.text}'. Indentation du texte à X={x_text_start:.2f}")

                    else:
                        current_x = x_start
                    
                    # --- CORRECTION : Réinitialiser la liste de mots pour chaque paragraphe ---
                    all_words = []
                    for span in content_spans:
                        if span.text:
                            text_with_markers = span.text.replace('\n', ' <LINE_BREAK> ')
                            words = text_with_markers.split(' ')
                            for word in words:
                                all_words.append((word, span))

                    for word, span in all_words:
                        if not word: continue
                        if word == '<LINE_BREAK>':
                            current_y += max_font_size_in_line * 1.2
                            current_x = x_text_start
                            max_font_size_in_line = span.font.size
                            continue

                        word_with_space = word + ' '
                        word_width = self._get_text_width(word_with_space, span.font.name, span.font.size)
                        line_height = span.font.size * 1.2

                        if current_x + word_width > x_start + block_width and current_x > x_text_start:
                            current_y += max_font_size_in_line * 1.2
                            current_x = x_text_start
                            max_font_size_in_line = span.font.size

                        if span.font.size > max_font_size_in_line:
                            max_font_size_in_line = span.font.size
                        
                        new_span = copy.deepcopy(span)
                        new_span.text = word_with_space
                        new_span.final_bbox = (current_x, current_y, current_x + word_width, current_y + line_height)
                        all_new_spans_for_block.append(new_span)
                        current_x += word_width
                    
                    current_y += max_font_size_in_line * 1.2

                block.spans = all_new_spans_for_block
                final_height = (current_y - block.bbox[1]) if all_new_spans_for_block else 0
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + final_height)
                self.debug_logger.info(f"    <- Fin du bloc {block.id}. Nouvelle hauteur: {final_height:.2f}px.")

        self.debug_logger.info("--- FIN LAYOUTPROCESSOR ---")
        return pages
