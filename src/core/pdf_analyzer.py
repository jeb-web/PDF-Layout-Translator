#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** VERSION FINALE ET STABILISÉE v2.8 - CORRECTION DES PARAGRAPHES VIDES ***
"""
import logging
import re
from typing import List
import fitz
import copy
from core.data_model import PageObject
from utils.font_manager import FontManager

class LayoutProcessor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager

    def _get_text_width(self, text: str, font_name: str, font_size: float) -> float:
        # ... (méthode inchangée)
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
        self.debug_logger.info("--- DÉMARRAGE LAYOUTPROCESSOR (v2.8 - Robuste) ---")
        for page in pages:
            self.debug_logger.info(f"  > Traitement de la Page {page.page_number}")
            for block in page.text_blocks:
                self.debug_logger.info(f"    -> Calcul du reflow pour le bloc {block.id}")
                
                all_new_spans_for_block = []
                current_y = block.bbox[1]
                
                max_ideal_width = 0
                original_block_width = block.bbox[2] - block.bbox[0]

                for para in block.paragraphs:
                    # --- DÉBUT CORRECTION v2.8 ---
                    # On ignore les paragraphes qui n'ont pas de spans pour éviter un crash
                    if not para.spans:
                        self.debug_logger.warning(f"       [Layout v2.8] Paragraphe {para.id} ignoré car il ne contient aucun span.")
                        continue
                    # --- FIN CORRECTION v2.8 ---
                        
                    full_para_text = "".join([span.text for span in para.spans])
                    lines = full_para_text.split('\n')
                    for line_text in lines:
                        if not line_text.strip(): continue
                        representative_span = para.spans[0]
                        line_width = self._get_text_width(line_text, representative_span.font.name, representative_span.font.size)
                        if line_width > max_ideal_width:
                            max_ideal_width = line_width
                
                max_available_width = block.available_width if block.available_width > 5 else original_block_width
                
                self.debug_logger.info(f"       [Layout - Évaluation Globale] Largeur originale={original_block_width:.1f}, "
                                       f"Largeur max requise={max_ideal_width:.1f}, "
                                       f"Largeur max disponible={max_available_width:.1f}")

                block_width_for_reflow = original_block_width
                if max_ideal_width > original_block_width:
                    if max_ideal_width <= (max_available_width + 1.0):
                        block_width_for_reflow = max_ideal_width
                        self.debug_logger.info(f"       [Layout Decision] DÉCISION GLOBALE : Expansion de la boîte à {block_width_for_reflow:.1f}px.")
                    else:
                        block_width_for_reflow = max_available_width
                        self.debug_logger.warning(f"       [Layout Decision] Expansion globale impossible. DÉCISION GLOBALE : Retour à la ligne forcé avec largeur max de {block_width_for_reflow:.1f}px.")
                else:
                    self.debug_logger.info("       [Layout Decision] Le texte tient dans la boîte originale. Pas de changement global.")

                for para in block.paragraphs:
                    # --- DÉBUT CORRECTION v2.8 ---
                    if not para.spans:
                        continue # On s'assure de l'ignorer également dans la boucle de rendu
                    # --- FIN CORRECTION v2.8 ---

                    self.debug_logger.info(f"       - Traitement du paragraphe {para.id} (Liste: {para.is_list_item})")
                    
                    all_words_info = []
                    for span in para.spans:
                        if span.text:
                            words_and_breaks = re.split(r'(\s+)', span.text)
                            for item in words_and_breaks:
                                if item:
                                    all_words_info.append((item, span))

                    x_start = block.bbox[0]
                    current_x = x_start
                    x_text_start = x_start
                    max_font_size_in_line = para.spans[0].font.size

                    is_first_word_of_line = True
                    for i, (word, span) in enumerate(all_words_info):
                        
                        if '\n' in word:
                            current_y += max_font_size_in_line * 1.2
                            current_x = x_text_start
                            is_first_word_of_line = True
                            word = word.replace('\n', '')
                            if not word: continue

                        word_with_space = word
                        word_width = self._get_text_width(word_with_space, span.font.name, span.font.size)
                        line_height = span.font.size * 1.2
                        
                        if current_x + word_width > x_start + block_width_for_reflow and not is_first_word_of_line:
                            current_y += max_font_size_in_line * 1.2
                            current_x = x_text_start
                            max_font_size_in_line = span.font.size
                            is_first_word_of_line = True

                        if span.font.size > max_font_size_in_line:
                            max_font_size_in_line = span.font.size
                        
                        new_span = copy.deepcopy(span)
                        new_span.text = word_with_space
                        new_span.final_bbox = (current_x, current_y, current_x + word_width, current_y + line_height)
                        all_new_spans_for_block.append(new_span)
                        
                        current_x += word_width
                        is_first_word_of_line = False if word.strip() else is_first_word_of_line
                    
                    current_y += max_font_size_in_line * 1.2

                block.spans = all_new_spans_for_block
                final_height = (current_y - block.bbox[1]) if all_new_spans_for_block else 0
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + final_height)

        self.debug_logger.info("--- FIN LAYOUTPROCESSOR ---")
        return pages
