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

    def reconstruct_pdf(self, original_pdf_path: Path, layout_data: Dict[str, Any],
                       validated_translations: Dict[str, Any], output_path: Path,
                       preserve_original: bool = True) -> ReconstructionResult:
        start_time = datetime.now()
        self.logger.info(f"Début de la reconstruction robuste: {original_pdf_path} -> {output_path}")
        
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
        self.logger.info(f"DEBUG: Page {page_number}: {len(elements_on_page)} éléments à traiter.")

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
        font_name = self._determine_font_family(element_layout)
        
        # --- FIX: Conversion de Markdown en HTML simple et utilisation de insert_htmlbox ---
        html_content = self._markdown_to_html(translated_md)
        
        # Définir un CSS de base pour contrôler l'apparence
        css = f"""
        p {{
            font-family: '{font_name}';
            font-size: {font_size}pt;
            text-align: left;
            margin: 0;
            padding: 0;
        }}
        b, strong {{ font-weight: bold; }}
        i, em {{ font-style: italic; }}
        """

        page.insert_htmlbox(rect, f"<p>{html_content}</p>", css=css)

    def _markdown_to_html(self, md_text: str) -> str:
        """Convertit un Markdown simple en HTML simple."""
        text = md_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<b><i>\1</i></b>', text)
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        text = text.replace('\n', '<br>')
        return text

    def _determine_font_family(self, element_layout: Dict[str, Any]) -> str:
        """Détermine une famille de police de base."""
        font_name = element_layout.get('original_font_name', '').lower()
        if 'times' in font_name or 'serif' in font_name:
            return 'times'
        if 'courier' in font_name or 'mono' in font_name:
            return 'cour'
        return 'helv' # Helvetica est une police sans-serif sûre
