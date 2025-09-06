#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Moteur de Rendu PDF
*** VERSION CORRIGÉE - Gestion avancée du reflow et débordements ***
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
        if len(hex_color) == 3: 
            hex_color = "".join([c * 2 for c in hex_color])
        if len(hex_color) != 6: 
            return (0, 0, 0)
        try:
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            return (r, g, b)
        except ValueError: 
            return (0, 0, 0)

    def _get_text_width(self, text: str, font_name: str, font_size: float) -> float:
        """Calcule la largeur réelle d'un texte"""
        font_path = self.font_manager.get_replacement_font_path(font_name)
        if font_path and font_path.exists():
            try:
                font_buffer = font_path.read_bytes()
                font = fitz.Font(fontbuffer=font_buffer)
                return font.text_length(text, fontsize=font_size)
            except Exception as e:
                self.debug_logger.error(f"Erreur de mesure Fitz pour la police {font_path}: {e}")
        return len(text) * font_size * 0.6

    def _split_text_to_fit(self, text: str, max_width: float, font_name: str, font_size: float) -> List[str]:
        """Divise le texte en lignes qui s'adaptent à la largeur maximale"""
        if not text.strip():
            return [""]
        
        words = text.split()
        if not words:
            return [""]
        
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            test_width = self._get_text_width(test_line, font_name, font_size)
            
            if test_width <= max_width or not current_line:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]

    def _render_text_block_advanced(self, page, block, paragraph_translations: Dict[str, str]):
        """Rendu avancé d'un bloc de texte avec gestion du reflow"""
        if not block.final_bbox or not block.paragraphs:
            return
        
        self.debug_logger.info(f"  > Rendu avancé du TextBlock ID: {block.id}")
        
        # Dimensions du bloc final
        block_x = block.final_bbox[0]
        block_y = block.final_bbox[1] 
        block_width = block.final_bbox[2] - block.final_bbox[0]
        block_height = block.final_bbox[3] - block.final_bbox[1]
        
        current_y = block_y
        shape = page.new_shape()
        
        for paragraph in block.paragraphs:
            # Récupérer la traduction du paragraphe
            para_translation = paragraph_translations.get(paragraph.id, "")
            
            if para_translation and para_translation.strip():
                # Parser le HTML traduit pour extraire le texte avec styles
                text_segments = self._parse_translated_html(para_translation, paragraph.spans)
            else:
                # Utiliser le texte original
                text_segments = [(span.text, span.font) for span in paragraph.spans if span.text.strip()]
            
            # Rendu de chaque segment de texte
            for text, font_info in text_segments:
                if not text.strip():
                    continue
                
                # Calculer la largeur disponible (avec marge de sécurité)
                available_width = block_width * 0.95
                
                # Diviser le texte en lignes
                text_lines = self._split_text_to_fit(text, available_width, font_info.name, font_info.size)
                
                for line in text_lines:
                    if not line.strip():
                        continue
                    
                    # Vérifier si on a assez d'espace vertical
                    line_height = font_info.size * 1.3
                    if current_y + line_height > block_y + block_height:
                        self.debug_logger.warning(f"    Débordement vertical détecté, troncature du texte")
                        break
                    
                    # Créer le rectangle pour cette ligne
                    line_rect = fitz.Rect(
                        block_x,
                        current_y,
                        block_x + block_width,
                        current_y + line_height
                    )
                    
                    # Rendu de la ligne
                    color_rgb = self._hex_to_rgb(font_info.color)
                    
                    try:
                        rc = shape.insert_textbox(
                            line_rect,
                            line,
                            fontname=font_info.name,
                            fontsize=font_info.size,
                            color=color_rgb,
                            align=block.alignment
                        )
                        
                        self.debug_logger.info(f"    -> Ligne rendue: '{line[:50]}...' (surplus: {rc:.2f})")
                        
                        if rc < 0:
                            self.debug_logger.warning(f"    -> Débordement horizontal détecté")
                    
                    except Exception as e:
                        self.debug_logger.error(f"    -> Erreur de rendu: {e}")
                    
                    current_y += line_height
                
                # Espacement entre segments
                current_y += font_info.size * 0.2
            
            # Espacement entre paragraphes
            current_y += 8
        
        shape.commit()

    def _parse_translated_html(self, html_content: str, original_spans) -> List[Tuple[str, object]]:
        """Parse le HTML traduit pour extraire le texte et les styles"""
        # Version simplifiée - à améliorer pour un parsing HTML complet
        from lxml import etree
        
        try:
            if html_content.strip().startswith('<![CDATA['):
                html_content = html_content.strip()[9:-3]
            
            parser = etree.HTMLParser()
            root = etree.fromstring(f"<div>{html_content.strip()}</div>", parser)
            
            segments = []
            default_font = original_spans[0].font if original_spans else None
            
            # Extraire le texte de tous les éléments
            for elem in root.iter():
                if elem.text:
                    segments.append((elem.text, default_font))
                if elem.tail:
                    segments.append((elem.tail, default_font))
            
            return segments if segments else [(html_content, default_font)]
        
        except Exception as e:
            self.debug_logger.error(f"Erreur de parsing HTML: {e}")
            # Fallback : utiliser le texte brut avec la première police
            default_font = original_spans[0].font if original_spans else None
            return [(html_content, default_font)]

    def render_pages(self, pages: List[PageObject], output_path: Path):
        """Rendu principal des pages avec algorithme avancé"""
        self.debug_logger.info("--- DÉMARRAGE PDFRECONSTRUCTOR (Version Corrigée) ---")
        doc = fitz.open()

        # Charger les traductions si disponibles
        paragraph_translations = self._load_translations_if_available(output_path)

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

            # Rendu avancé de chaque bloc
            for block in page_data.text_blocks:
                self._render_text_block_advanced(page, block, paragraph_translations)

        self.debug_logger.info(f"Sauvegarde du PDF final vers : {output_path}")
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        self.debug_logger.info("--- FIN PDFRECONSTRUCTOR ---")

    def _load_translations_if_available(self, output_path: Path) -> Dict[str, str]:
        """Charge les traductions depuis le fichier de session si disponible"""
        try:
            # Essayer de charger depuis le répertoire parent (session)
            session_dir = output_path.parent.parent / "sessions"
            if session_dir.exists():
                for session_subdir in session_dir.iterdir():
                    if session_subdir.is_dir():
                        translations_file = session_subdir / "4_parsed_translations.json"
                        if translations_file.exists():
                            import json
                            with open(translations_file, 'r', encoding='utf-8') as f:
                                return json.load(f)
        except Exception as e:
            self.debug_logger.error(f"Impossible de charger les traductions: {e}")
        
        return {}
