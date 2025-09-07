#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Mise en Page
*** VERSION FINALE ET STABILISÉE v2.7 - MISE EN PAGE STRUCTURÉE (Gestion des <br>) ***
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
        self.debug_logger.info("--- DÉMARRAGE LAYOUTPROCESSOR (v2.7 - Mise en Page Structurée) ---")
        for page in pages:
            self.debug_logger.info(f"  > Traitement de la Page {page.page_number}")
            for block in page.text_blocks:
                self.debug_logger.info(f"    -> Calcul du reflow pour le bloc {block.id}")
                
                all_new_spans_for_block = []
                current_y = block.bbox[1]
                
                # --- ÉTAPE 1 (v2.7) : DÉCISION DE LARGEUR GLOBALE POUR LE BLOC ---
                # On calcule la largeur maximale requise par le paragraphe le plus exigeant.
                max_ideal_width = 0
                original_block_width = block.bbox[2] - block.bbox[0]

                for para in block.paragraphs:
                    full_para_text = "".join([span.text for span in para.spans])
                    lines = full_para_text.split('\n')
                    for line_text in lines:
                        if not para.spans or not line_text.strip(): continue
                        # On mesure la largeur avec la police du premier span du paragraphe comme référence
                        representative_span = para.spans[0]
                        line_width = self._get_text_width(line_text, representative_span.font.name, representative_span.font.size)
                        if line_width > max_ideal_width:
                            max_ideal_width = line_width
                
                max_available_width = block.available_width if block.available_width > 5 else original_block_width
                
                self.debug_logger.info(f"       [Layout v2.7 - Évaluation Globale] Largeur originale={original_block_width:.1f}, "
                                       f"Largeur maximale requise={max_ideal_width:.1f}, "
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

                # --- ÉTAPE 2 (v2.7) : MISE EN PAGE PARAGRAPHE PAR PARAGRAPHE ---
                for para in block.paragraphs:
                    self.debug_logger.info(f"       - Traitement du paragraphe {para.id} (Liste: {para.is_list_item})")
                    if not para.spans:
                        continue
                    
                    # On regroupe tous les mots et spans du paragraphe
                    all_words_info = []
                    for span in para.spans:
                        if span.text:
                            # On scinde par les espaces ET les retours à la ligne pour préserver leur position
                            words_and_breaks = re.split(r'(\s+)', span.text)
                            for item in words_and_breaks:
                                if item:
                                    all_words_info.append((item, span))

                    # On traite les mots ligne par ligne, en se basant sur les '\n'
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
                            # Si le mot contient du texte en plus du \n, on le traite après le saut
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
                        # On ne considère plus les espaces comme séparateurs de mots pour cette logique
                        is_first_word_of_line = False if word.strip() else is_first_word_of_line
                    
                    # On ajoute un espacement après chaque paragraphe (qui peut contenir plusieurs lignes via \n)
                    current_y += max_font_size_in_line * 1.2

                block.spans = all_new_spans_for_block
                final_height = (current_y - block.bbox[1]) if all_new_spans_for_block else 0
                block.final_bbox = (block.bbox[0], block.bbox[1], block.bbox[2], block.bbox[1] + final_height)

        self.debug_logger.info("--- FIN LAYOUTPROCESSOR ---")
        return pages
