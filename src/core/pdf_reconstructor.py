#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Reconstructeur de PDF
Reconstruction du PDF final avec texte traduit et mise en page ajustée

Auteur: L'OréalGPT
Version: 1.0.0
"""

import logging
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import re

@dataclass
class ReconstructionResult:
    success: bool; output_path: Optional[Path]; processing_time: float; pages_processed: int
    elements_processed: int; errors: List[str]; warnings: List[str]

class PDFReconstructor:
    def __init__(self, config_manager=None, font_manager=None):
        self.logger = logging.getLogger(__name__)
        self.font_manager = font_manager # Essentiel pour la nouvelle logique

    def reconstruct_pdf(self, original_pdf_path: Path, layout_data: Dict[str, Any],
                       validated_translations: Dict[str, Any], output_path: Path,
                       preserve_original: bool = True) -> ReconstructionResult:
        start_time = datetime.now()
        try:
            original_doc = fitz.open(original_pdf_path)
            output_doc = fitz.open()
            
            for page_num in range(len(original_doc)):
                self._process_page(original_doc, page_num, output_doc, layout_data, validated_translations)

            if len(output_doc) > 0:
                output_doc.save(output_path, garbage=4, deflate=True, clean=True)

            original_doc.close(); output_doc.close()
            
            return ReconstructionResult(
                success=True, output_path=output_path, processing_time=(datetime.now() - start_time).total_seconds(),
                pages_processed=len(output_doc), elements_processed=len(layout_data.get('element_layouts', [])),
                errors=[], warnings=[]
            )
        except Exception as e:
            self.logger.error(f"Erreur critique lors de la reconstruction: {e}", exc_info=True)
            return ReconstructionResult(success=False, output_path=None, processing_time=0, pages_processed=0, elements_processed=0, errors=[str(e)], warnings=[])

    def _process_page(self, original_doc, page_num: int, output_doc,
                     layout_data: Dict[str, Any], validated_translations: Dict[str, Any]):
        
        page_number = page_num + 1
        output_doc.insert_pdf(original_doc, from_page=page_num, to_page=page_num)
        new_page = output_doc[page_num]

        elements_on_page = self._get_page_text_elements(page_number, layout_data, validated_translations)
        
        for element in elements_on_page:
            new_page.add_redact_annot(fitz.Rect(element['original_bbox']))
        if elements_on_page:
            new_page.apply_redactions()

        for element in elements_on_page:
            self._place_translated_text(new_page, element)

    def _get_page_text_elements(self, page_number: int, layout_data: Dict[str, Any], validated_translations: Dict[str, Any]) -> List[Dict[str, Any]]:
        layouts = {elem['element_id']: elem for elem in layout_data.get('element_layouts', [])}
        elements = []
        for elem_id, layout_info in layouts.items():
            if layout_info.get('page_number') == page_number and elem_id in validated_translations['translations']:
                full_info = layout_info.copy()
                full_info.update(validated_translations['translations'][elem_id])
                elements.append(full_info)
        return elements
    
    def _place_translated_text(self, page, element_layout: Dict[str, Any]):
        raw_translated_text = element_layout.get('translated_text', '')
        if not raw_translated_text: return

        # Nettoyer le Markdown pour l'affichage en texte brut
        text_to_render = re.sub(r'\*+', '', raw_translated_text)

        rect = fitz.Rect(element_layout['new_bbox'])
        font_size = element_layout['new_font_size']
        align = self._get_text_alignment(element_layout)
        
        # --- MODIFICATION MAJEURE : Utilisation de fontfile ---
        original_font_name = element_layout.get('original_font_name', 'Arial')
        font_path = self.font_manager.get_replacement_font_path(original_font_name)
        
        if font_path and font_path.exists():
            rc = page.insert_textbox(rect, text_to_render, 
                                     fontsize=font_size, 
                                     fontfile=str(font_path), 
                                     align=align)
        else:
            # Fallback sur une police de base si le fichier n'est pas trouvé
            font_name_fallback = self._get_fallback_fontname(original_font_name)
            rc = page.insert_textbox(rect, text_to_render, 
                                     fontsize=font_size, 
                                     fontname=font_name_fallback, 
                                     align=align)
        
        if rc < 0:
            self.logger.warning(f"Le texte pour l'élément {element_layout['element_id']} a peut-être débordé. Code: {rc}")

    def _get_fallback_fontname(self, original_font_name: str) -> str:
        """Détermine un nom de police PDF de base en fonction du style."""
        name_lower = original_font_name.lower()
        if 'bold' in name_lower and 'italic' in name_lower: return "helv-boit"
        if 'bold' in name_lower: return "helv-bold"
        if 'italic' in name_lower: return "helv-it"
        return "helv"

    def _get_text_alignment(self, element_layout: Dict[str, Any]) -> int:
        content_type = element_layout.get('content_type', 'paragraph')
        if content_type in ['title', 'subtitle', 'header', 'footer']:
            return fitz.TEXT_ALIGN_CENTER
        return fitz.TEXT_ALIGN_LEFT
