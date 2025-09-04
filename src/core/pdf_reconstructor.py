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
        translated_md = element_layout.get('translated_text', '')
        if not translated_md: return

        rect = fitz.Rect(element_layout['new_bbox'])
        font_size = element_layout['new_font_size']
        
        # --- MODIFICATION MAJEURE : Appel au FontManager pour obtenir la police ---
        original_font_name = element_layout.get('original_font_name', 'Arial')
        font_path = self.font_manager.get_replacement_font_path(original_font_name)
        
        if font_path:
            # Enregistrer la police personnalisée pour cette page
            font_ref = page.insert_font(fontfile=str(font_path), fontname=font_path.stem)
            fontname_for_html = font_path.stem
        else:
            # Fallback sur les polices PDF de base
            fontname_for_html = 'helv' 

        html_content = self._markdown_to_html(translated_md)
        css = f"p {{ font-family: '{fontname_for_html}'; font-size: {font_size}pt; text-align: left; margin: 0; padding: 0; }}"
        
        page.insert_htmlbox(rect, f"<p>{html_content}</p>", css=css)

    def _markdown_to_html(self, md_text: str) -> str:
        text = md_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        return text.replace('\n', '<br>')
