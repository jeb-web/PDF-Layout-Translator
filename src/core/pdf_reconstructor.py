#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION CORRIGÉE - JALON 2.2 (Logique de Reflow) ***
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
                # Utiliser fitz.Font pour la cohérence avec LayoutProcessor
                font_buffer = font_path.read_bytes()
                font = fitz.Font(fontbuffer=font_buffer)
                return font.text_length(text, fontsize=font_size)
            except Exception as e:
                self.debug_logger.error(f"Erreur de mesure Fitz pour la police {font_path}: {e}")
        # Fallback de sécurité
        return len(text) * font_size * 0.6

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Jalon 2.2 - Reflow Corrigé) ---")
        doc = fitz.open()

        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])

            # Enregistrer les polices nécessaires
            fonts_on_page = {span.font.name for block in page_data.text_blocks for span in block.spans}
            for font_name in fonts_on_page:
                font_path = self.font_manager.get_replacement_font_path(font_name)
                if font_path and font_path.exists():
                    try:
                        page.insert_font(fontname=font_name, fontfile=str(font_path))
                    except Exception as e:
                        self.debug_logger.error(f"  -> ERREUR enregistrement police '{font_name}': {e}")

            for block in page_data.text_blocks:
                self.debug_logger.info(f"  > Rendu du bloc {block.id} dans le Rect final : {block.final_bbox}")
                if not block.final_bbox or not block.spans:
                    continue

                block_width = block.final_bbox[2] - block.final_bbox[0]
                self.debug_logger.info(f"    Largeur disponible : {block_width:.2f}")

                # 1. Créer une liste de tous les mots avec leurs spans associés
                all_words = []
                for span in block.spans:
                    if span.text:
                        text_with_markers = span.text.replace('\n', ' <PARA_BREAK> ')
                        words = text_with_markers.split(' ')
                        for word in words:
                            if word:  # Ignorer les chaînes vides
                                all_words.append((word, span))
                
                if not all_words:
                    continue

                # 2. Initialiser les variables de rendu
                current_x = block.final_bbox[0]
                current_y = block.final_bbox[1]
                max_font_size_in_line = all_words[0][1].font.size
                
                shape = page.new_shape()

                # 3. Itérer sur les mots et les positionner
                for word, span in all_words:
                    self.debug_logger.info(f"      - Mot : '{word}', Police : {span.font.name}, Taille : {span.font.size}")

                    if word == '<PARA_BREAK>':
                        new_y = current_y + max_font_size_in_line * 1.2
                        self.debug_logger.warning(f"        !! SAUT DE PARAGRAPHE. Nouvelle ligne à y={new_y:.2f}")
                        current_x = block.final_bbox[0]
                        current_y = new_y
                        max_font_size_in_line = span.font.size
                        continue

                    word_with_space = word + ' '
                    word_width = self._get_text_width(word_with_space, span.font.name, span.font.size)
                    self.debug_logger.info(f"        Mesure : largeur={word_width:.2f}")

                    # Gérer le retour à la ligne
                    if current_x + word_width > block.final_bbox[2] and current_x > block.final_bbox[0]:
                        new_y = current_y + max_font_size_in_line * 1.2
                        self.debug_logger.warning(f"        !! RETOUR À LA LIGNE. Dépassement de {block.final_bbox[2]:.2f}. Nouvelle ligne à y={new_y:.2f}")
                        current_x = block.final_bbox[0]
                        current_y = new_y
                        max_font_size_in_line = span.font.size

                    # Mettre à jour la plus grande police de la ligne pour une hauteur de ligne correcte
                    if span.font.size > max_font_size_in_line:
                        max_font_size_in_line = span.font.size

                    # Créer le rectangle pour ce mot spécifique
                    word_rect = fitz.Rect(current_x, current_y, current_x + word_width, current_y + max_font_size_in_line * 1.5)
                    self.debug_logger.info(f"        Positionnement : x={current_x:.2f}, y={current_y:.2f}")
                    self.debug_logger.info(f"        -> DESSIN du mot '{word}' dans le Rect : {word_rect}")
                    
                    try:
                        # Dessiner uniquement le mot, pas l'espace
                        shape.insert_textbox(
                            word_rect,
                            word,
                            fontname=span.font.name,
                            fontsize=span.font.size,
                            color=self._hex_to_rgb(span.font.color),
                            align=fitz.TEXT_ALIGN_LEFT # Toujours aligner à gauche pour le rendu mot par mot
                        )
                    except Exception as e:
                        self.debug_logger.error(f"    !! ERREUR sur insert_textbox pour le mot '{word}': {e}")
                    
                    # Mettre à jour la position horizontale pour le mot suivant
                    current_x += word_width

                shape.commit()

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
