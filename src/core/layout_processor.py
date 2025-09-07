#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** NOUVELLE VERSION v2.2 - GESTION DU HANGING INDENT POUR LES LISTES ***
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
        self.debug_logger.info("--- DÉMARRAGE LAYOUTPROCESSOR (v2.2 - Hanging Indent) ---")
        for page in pages:
            self.debug_logger.info(f"  > Traitement de la Page {page.page_number}")
            for block in page.text_blocks:
                self.debug_logger.info(f"    -> Calcul du reflow pour le bloc {block.id}")
                
                # --- NOUVELLE LOGIQUE PAR PARAGRAPHE ---
                all_new_spans_for_block = []
                current_y = block.bbox[1] # Y vertical pour le bloc entier
                
                for para in block.paragraphs:
                    self.debug_logger.info(f"       - Traitement du paragraphe {para.id} (Est-ce une liste? {para.is_list_item})")
                    if not para.spans:
                        continue

                    x_start = block.bbox[0]
                    block_width = block.bbox[2] - x_start
                    
                    x_text_start = x_start  # Par défaut, le texte commence au début du bloc
                    max_font_size_in_line = para.spans[0].font.size if para.spans else 10.0
                    
                    # Si c'est un item de liste, on gère la puce et l'indentation
                    if para.is_list_item:
                        marker_span = para.spans[0]
                        marker_width = self._get_text_width(marker_span.text, marker_span.font.name, marker_span.font.size)
                        
                        # Placer la puce
                        new_marker_span = copy.deepcopy(marker_span)
                        new_marker_span.final_bbox = (x_start, current_y, x_start + marker_width, current_y + marker_span.font.size * 1.2)
                        all_new_spans_for_block.append(new_marker_span)
                        
                        # L'indentation du texte est relative au début du bloc
                        x_text_start = para.text_indent 
                        current_x = x_text_start
                        
                        # Le reste des spans constitue le contenu de l'item de liste
                        content_spans = para.spans[1:]
                        self.debug_logger.info(f"         > Item de liste détecté. Marqueur: '{marker_span.text}'. Indentation du texte à X={x_text_start:.2f}")

                    else:
                        # Paragraphe normal
                        current_x = x_start
                        content_spans = para.spans
                    
                    # Traitement des mots du contenu
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
                            current_x = x_text_start # Retour à la ligne indenté
                            max_font_size_in_line = span.font.size
                            continue

                        word_with_space = word + ' '
                        word_width = self._get_text_width(word_with_space, span.font.name, span.font.size)
                        line_height = span.font.size * 1.2

                        if current_x + word_width > x_start + block_width and current_x > x_text_start:
                            current_y += max_font_size_in_line * 1.2
                            current_x = x_text_start # Retour à la ligne indenté
                            max_font_size_in_line = span.font.size

                        if span.font.size > max_font_size_in_line:
                            max_font_size_in_line = span.font.size
                        
                        new_span = copy.deepcopy(span)
                        new_span.text = word_with_space
                        new_span.final_bbox = (current_x, current_y, current_x + word_width, current_y + line_height)
                        all_new_spans_for_block.append(new_span)
                        current_x += word_width
                    
                    # Avancer le Y pour le prochain paragraphe
                    current_y += max_font_size_in_line * 1.2

                block.spans = all_new_spans_for_block
                final_height = current_y - block.bbox[1] if all_new_spans_for_block else 0
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + final_height)
                self.debug_logger.info(f"    <- Fin du bloc {block.id}. Nouvelle hauteur: {final_height:.2f}px.")

        self.debug_logger.info("--- FIN LAYOUTPROCESSOR ---")
        return pages
