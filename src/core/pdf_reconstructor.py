#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION DE DIAGNOSTIC - JALON 1.8 (Simplicité + Traces) ***
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
        self.font_object_cache: Dict[str, fitz.Font] = {}

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

    def _get_font(self, font_name: str) -> fitz.Font:
        if font_name in self.font_object_cache:
            return self.font_object_cache[font_name]
        
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if not (font_path and font_path.exists()):
            self.debug_logger.error(f"      !! _get_font: Chemin non trouvé pour '{font_name}'.")
            return None
        
        try:
            font = fitz.Font(fontfile=str(font_path))
            self.font_object_cache[font_name] = font
            return font
        except Exception as e:
            self.debug_logger.error(f"      !! _get_font: Erreur de chargement pour '{font_name}': {e}")
            return None

    def render_pages(self, pages: List[PageObject], output_path: Path):
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Jalon 1.8) ---")
        doc = fitz.open()
        self.font_object_cache.clear()

        for page_data in pages:
            self.debug_logger.info(f"Traitement de la Page {page_data.page_number}")
            page = doc.new_page(width=page_data.dimensions[0], height=page_data.dimensions[1])
            
            for block in page_data.text_blocks:
                self.debug_logger.info(f"  > Traitement du TextBlock ID: {block.id}")
                if not block.final_bbox or not block.spans: continue
                
                rect = fitz.Rect(block.final_bbox)
                if rect.is_empty: continue

                # On utilise un TextWriter juste pour le calcul du reflow
                writer = fitz.TextWriter(page.rect)
                for span in block.spans:
                    font = self._get_font(span.font.name)
                    if font:
                        writer.append(pos=(0,0), text=span.text, font=font, fontsize=span.font.size)
                
                try:
                    _, _, line_data = writer.fill_textbox(rect, text=None, align=block.alignment)
                except Exception as e:
                    self.debug_logger.error(f"    !! ERREUR dans writer.fill_textbox pour bloc {block.id}: {e}")
                    # Si fill_textbox échoue, nous ne pouvons pas continuer pour ce bloc
                    continue

                shape = page.new_shape()
                for line in line_data.get("lines", []):
                    for span_info in line.get("spans", []):
                        try:
                            point = span_info["bbox"].bl
                            text = span_info["text"]
                            fontname = span_info["font"]
                            fontsize = float(span_info["size"])
                            color_hex = span_info["color"]
                            color_rgb = self._hex_to_rgb(color_hex)
                            
                            # --- TRACES DE VALIDATION ---
                            is_inside = rect.contains(point)
                            self.debug_logger.info(f"    - Rendu du span : text='{text}', font='{fontname}', size={fontsize}, color={color_rgb}")
                            self.debug_logger.info(f"      -> Coordonnées : point={point}, rect={rect}")
                            self.debug_logger.info(f"      -> VÉRIFICATION : Le point est-il dans le rectangle ? {is_inside}")
                            if not is_inside:
                                self.debug_logger.warning("      !! ATTENTION : Le point de départ du texte est en dehors du rectangle de destination !")

                            shape.insert_text(
                                point,
                                text,
                                fontname=fontname,
                                fontsize=fontsize,
                                color=color_rgb
                            )
                        except Exception as e:
                            self.debug_logger.error(f"    !! ERREUR lors de l'appel à shape.insert_text : {e}")
                
                shape.commit()

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")
