#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION FINALE CORRIGÉE ET ROBUSTE ***
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
        # --- AJOUT D'UN CACHE DE POLICES ---
        # C'est la clé de la performance. On ne charge chaque police qu'une seule fois.
        self.font_cache: Dict[Path, fitz.Font] = {}

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
        self.debug_logger.info("--- Début du Rendu PDF (Version Corrigée et Robuste) ---")
        doc = fitz.open()
        
        # Vider le cache au début de chaque rendu pour éviter les problèmes de mémoire
        self.font_cache.clear()

        for page_data in pages:
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            for block in page_data.text_blocks:
                if not block.final_bbox or not block.spans:
                    continue
                
                shape = page.new_shape()
                
                block_bbox = fitz.Rect(block.final_bbox)
                
                if not block.spans: continue
                
                max_font_size_in_line = block.spans[0].font.size
                current_pos = fitz.Point(block_bbox.x0, block_bbox.y0 + max_font_size_in_line)

                for span in block.spans:
                    if not span.text: continue
                    
                    font_path = self.font_manager.get_replacement_font_path(span.font.name)
                    if not (font_path and font_path.exists()):
                        self.logger.warning(f"Police non trouvée pour '{span.font.name}', rendu ignoré.")
                        continue
                    
                    words = span.text.strip().split(' ')
                    for i, word in enumerate(words):
                        word_to_draw = word + (' ' if i < len(words) - 1 else '')
                        
                        # --- BLOC DE CORRECTION MAJEUR ---
                        # La seule méthode correcte et validée pour mesurer la largeur du texte
                        # avec une police externe est d'utiliser un objet fitz.Font.
                        if font_path not in self.font_cache:
                            try:
                                # Opération coûteuse, effectuée une seule fois par police grâce au cache.
                                self.font_cache[font_path] = fitz.Font(fontfile=str(font_path))
                                self.debug_logger.info(f"Police '{font_path.name}' chargée et mise en cache.")
                            except Exception as e:
                                self.logger.error(f"Impossible de charger la police {font_path}: {e}. Le texte utilisant cette police sera ignoré.")
                                # On place un objet None dans le cache pour ne pas retenter
                                self.font_cache[font_path] = None 
                                continue
                        
                        font = self.font_cache[font_path]
                        if font is None: # Si le chargement a échoué précédemment
                            continue

                        word_width = font.text_length(word_to_draw, fontsize=span.font.size)
                        # --- FIN DU BLOC DE CORRECTION ---
                        
                        if current_pos.x + word_width > block_bbox.x1 and current_pos.x > block_bbox.x0:
                            current_pos.x = block_bbox.x0
                            current_pos.y += max_font_size_in_line * 1.2
                            max_font_size_in_line = span.font.size
                        
                        if span.font.size > max_font_size_in_line:
                            max_font_size_in_line = span.font.size

                        if current_pos.y > block_bbox.y1 + 5:
                            break

                        # insert_text UTILISE 'fontfile', ce qui était déjà correct.
                        shape.insert_text(
                            current_pos,
                            word_to_draw,
                            fontfile=str(font_path),
                            fontsize=span.font.size,
                            color=self._hex_to_rgb(span.font.color)
                        )
                        current_pos.x += word_width
                    
                    if current_pos.y > block_bbox.y1 + 5: break
                
                shape.commit()

        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info(f"--- Rendu PDF (Version Corrigée et Robuste) Terminé. ---")
