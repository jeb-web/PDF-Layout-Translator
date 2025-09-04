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

@dataclass
class ReconstructionResult:
    success: bool
    output_path: Optional[Path]
    processing_time: float
    pages_processed: int
    elements_processed: int
    errors: List[str]
    warnings: List[str]

class PDFReconstructor:
    def __init__(self, config_manager=None, font_manager=None):
        self.logger = logging.getLogger(__name__)

    def reconstruct_pdf(self, original_pdf_path: Path, layout_data: Dict[str, Any],
                       validated_translations: Dict[str, Any], output_path: Path,
                       preserve_original: bool = True) -> ReconstructionResult:
        start_time = datetime.now()
        self.logger.info(f"Début de la reconstruction robuste: {original_pdf_path} -> {output_path}")
        
        errors, warnings = [], []
        pages_processed, elements_processed = 0, 0
        
        try:
            original_doc = fitz.open(original_pdf_path)
            output_doc = fitz.open()
            
            total_layouts = len(layout_data.get('element_layouts', []))
            self.logger.info(f"DEBUG: Le reconstructeur a reçu {total_layouts} éléments de mise en page au total.")

            for page_num in range(len(original_doc)):
                page_result = self._process_page(
                    original_doc, page_num, output_doc,
                    layout_data, validated_translations
                )
                pages_processed += 1
                elements_processed += page_result['elements_processed']
                warnings.extend(page_result['warnings'])

            if len(output_doc) == 0:
                warnings.append("Le document de sortie est vide car aucune page n'a été traitée.")
                self.logger.warning("Le document de sortie est vide.")
            else:
                output_doc.save(output_path, garbage=4, deflate=True, clean=True)

            original_doc.close()
            output_doc.close()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ReconstructionResult(
                success=True, output_path=output_path, processing_time=processing_time,
                pages_processed=pages_processed, elements_processed=elements_processed,
                errors=errors, warnings=warnings
            )
            
        except Exception as e:
            self.logger.error(f"Erreur critique lors de la reconstruction: {e}", exc_info=True)
            return ReconstructionResult(
                success=False, output_path=None, processing_time=0,
                pages_processed=0, elements_processed=0, errors=[str(e)], warnings=[]
            )

    def _process_page(self, original_doc, page_num: int, output_doc,
                     layout_data: Dict[str, Any], validated_translations: Dict[str, Any]) -> Dict[str, Any]:
        
        page_number = page_num + 1
        self.logger.info(f"Traitement de la page {page_number}...")

        # 1. Copier la page originale parfaitement dans le nouveau document
        output_doc.insert_pdf(original_doc, from_page=page_num, to_page=page_num)
        new_page = output_doc[page_num] # Récupérer la référence à la page copiée

        elements_on_page = self._get_page_text_elements(page_number, layout_data, validated_translations)
        
        # --- DÉBUT DE L'AMÉLIORATION DU DÉBOGAGE ---
        self.logger.info(f"DEBUG: Page {page_number}: {len(elements_on_page)} éléments traduits trouvés pour placement.")
        # --- FIN DE L'AMÉLIORATION DU DÉBOGAGE ---

        # 2. Effacer "chirurgicalement" l'ancien texte en utilisant la rédaction
        for element_layout in elements_on_page:
            original_bbox = fitz.Rect(element_layout['original_bbox'])
            new_page.add_redact_annot(original_bbox, fill=(1,1,1)) # Remplir avec du blanc

        # Appliquer toutes les rédactions sur la page en une seule fois (plus efficace)
        if elements_on_page:
            new_page.apply_redactions()

        # 3. Placer le nouveau texte traduit
        for element_layout in elements_on_page:
            try:
                self._place_translated_text(new_page, element_layout)
            except Exception as e:
                self.logger.warning(f"Erreur placement texte {element_layout.get('element_id', 'N/A')}: {e}")

        return {'elements_processed': len(elements_on_page), 'warnings': []}

    def _get_page_text_elements(self, page_number: int, layout_data: Dict[str, Any], validated_translations: Dict[str, Any]) -> List[Dict[str, Any]]:
        layouts = {elem['element_id']: elem for elem in layout_data.get('element_layouts', [])}
        elements_on_page = []
        for elem_id, layout_info in layouts.items():
            if layout_info.get('page_number') == page_number and elem_id in validated_translations['translations']:
                full_info = layout_info.copy()
                full_info.update(validated_translations['translations'][elem_id])
                elements_on_page.append(full_info)
        return elements_on_page
    
    def _place_translated_text(self, page, element_layout: Dict[str, Any]):
        translated_text = element_layout.get('translated_text', '')
        if not translated_text:
            return

        rect = fitz.Rect(element_layout['new_bbox'])
        font_size = element_layout['new_font_size']
        font_name = self._determine_font_for_element(element_layout)
        align = self._get_text_alignment(element_layout)
        
        self.logger.debug(f"Placement de '{translated_text[:30]}...' dans le rect {rect} avec police {font_name} et taille {font_size}")

        rc = page.insert_textbox(rect, translated_text, fontsize=font_size, fontname=font_name, align=align)
        if rc < 0:
            self.logger.warning(f"Le texte pour l'élément {element_layout['element_id']} a peut-être débordé. Code: {rc}")

    def _determine_font_for_element(self, element_layout: Dict[str, Any]) -> str:
        original_font = element_layout.get('original_font_name', 'helv').lower()
        if 'bold' in original_font and ('italic' in original_font or 'oblique' in original_font):
            return "helv-boit"
        if 'bold' in original_font:
            return "helv-bold"
        if 'italic' in original_font or 'oblique' in original_font:
            return "helv-it"
        return "helv"

    def _get_text_alignment(self, element_layout: Dict[str, Any]) -> int:
        content_type = element_layout.get('content_type', 'paragraph')
        if content_type in ['title', 'subtitle', 'header', 'footer']:
            return fitz.TEXT_ALIGN_CENTER
        return fitz.TEXT_ALIGN_LEFT

