#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
Dessine le DOM finalisé dans un nouveau fichier PDF.
*** VERSION DE DÉBOGAGE VISUEL ***
"""
import logging
from pathlib import Path
from typing import List, Tuple
import fitz  # PyMuPDF
from core.data_model import PageObject
from utils.font_manager import FontManager

class PDFReconstructor:
    def __init__(self, font_manager: FontManager):
        self.logger = logging.getLogger(__name__)
        self.debug_logger = logging.getLogger('debug_trace')
        self.font_manager = font_manager

    def _hex_to_rgb(self, hex_color: str) -> Tuple[float, float, float]:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3: hex_color = "".join([c*2 for c in hex_color])
        if len(hex_color) != 6: return (0, 0, 0)
        try:
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError:
            return (0, 0, 0)

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- Début du Rendu PDF (Mode Débogage Visuel) ---")
        doc = fitz.open()
        
        if not pages:
            self.logger.warning("Aucune page à rendre.")
            doc.new_page() # Crée un document vide
            doc.save(output_path)
            doc.close()
            return

        # Utiliser les dimensions de la première page pour toutes les pages générées
        page_width, page_height = pages[0].dimensions
        page = doc.new_page(width=page_width, height=page_height)
        
        # Initialisation du "curseur" vertical
        current_y = 20  # Marge supérieure
        margin = 15     # Marge entre les blocs

        all_blocks = [block for page_data in pages for block in page_data.text_blocks]

        for block in all_blocks:
            if not block.final_bbox: 
                self.debug_logger.warning(f"  - Bloc {block.id} ignoré : pas de Bbox finale.")
                continue
            
            if not block.spans:
                continue

            block_height = block.final_bbox[3] - block.final_bbox[1]
            if block_height <= 0:
                self.debug_logger.warning(f"  - Bloc {block.id} a une hauteur nulle ou négative ({block_height}). Ignoré.")
                continue

            # --- Gestion des sauts de page ---
            if current_y + block_height + margin > page_height:
                self.debug_logger.info("Saut de page : plus d'espace sur la page actuelle.")
                page = doc.new_page(width=page_width, height=page_height)
                current_y = 20  # Réinitialiser le curseur en haut de la nouvelle page

            # --- Création de la Bbox de débogage ---
            # On utilise les coordonnées X originales mais la position Y séquentielle
            debug_bbox = fitz.Rect(
                block.final_bbox[0], 
                current_y, 
                block.final_bbox[2], 
                current_y + block_height
            )

            full_text = "".join([s.text for s in block.spans])
            self.debug_logger.info(f"  -> Rendu du bloc {block.id} à y={current_y:.2f} avec texte: '{full_text[:70]}...'")

            # --- Ajout des aides visuelles de débogage ---
            # Dessiner un cadre rouge autour de la bbox calculée
            page.draw_rect(debug_bbox, color=(1, 0, 0), width=0.5)
            # Écrire l'ID du bloc pour l'identifier
            info_pos = debug_bbox.top_left - (0, 5) # Un peu au-dessus du coin
            page.insert_text(info_pos, f"ID: {block.id}", fontsize=6, color=(0.5, 0.5, 0.5))
            
            # --- Insertion du texte ---
            main_span = block.spans[0]
            font_path = self.font_manager.get_replacement_font_path(main_span.font.name)
            color_rgb = self._hex_to_rgb(main_span.font.color)

            if font_path and font_path.exists():
                font_internal_name = f"F-{font_path.stem.replace(' ', '')}"
                try:
                    page.insert_textbox(debug_bbox, full_text, fontsize=main_span.font.size,
                                        fontname=font_internal_name, fontfile=str(font_path), color=color_rgb)
                    self.debug_logger.info(f"     Bloc inséré avec police '{font_path.name}'.")
                except Exception as e:
                     self.logger.error(f"Erreur d'insertion texte bloc {block.id}: {e}")
                     self.debug_logger.error(f"     ERREUR d'insertion texte bloc {block.id}: {e}")
            else:
                fallback_font = "helv"
                self.logger.warning(f"Police de remplacement non trouvée pour '{main_span.font.name}', utilisant {fallback_font}.")
                self.debug_logger.warning(f"     Police non trouvée pour '{main_span.font.name}', utilisant {fallback_font}.")
                page.insert_textbox(debug_bbox, full_text, fontsize=main_span.font.size,
                                    fontname=fallback_font, color=color_rgb)

            # --- Mise à jour de la position pour le bloc suivant ---
            current_y += block_height + margin
        
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"--- Rendu PDF (Mode Débogage) Terminé. Fichier sauvegardé: {output_path} ---")
