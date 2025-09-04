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
import shutil

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
        self.font_manager = font_manager # Nécessaire pour les polices

    def reconstruct_pdf(self, original_pdf_path: Path, layout_data: Dict[str, Any],
                       validated_translations: Dict[str, Any], output_path: Path,
                       preserve_original: bool = True) -> ReconstructionResult:
        start_time = datetime.now()
        self.logger.info(f"Début de la reconstruction: {original_pdf_path} -> {output_path}")
        
        errors, warnings = [], []
        pages_processed, elements_processed = 0, 0
        
        try:
            original_doc = fitz.open(original_pdf_path)
            output_doc = fitz.open()
            
            for page_num in range(len(original_doc)):
                page_result = self._process_page(
                    original_doc[page_num], output_doc, page_num + 1,
                    layout_data, validated_translations
                )
                pages_processed += 1
                elements_processed += page_result['elements_processed']
                warnings.extend(page_result['warnings'])

            output_doc.save(output_path, garbage=4, deflate=True)
            original_doc.close()
            output_doc.close()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ReconstructionResult(
                success=True, output_path=output_path, processing_time=processing_time,
                pages_processed=pages_processed, elements_processed=elements_processed,
                errors=errors, warnings=warnings
            )
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la reconstruction: {e}", exc_info=True)
            return ReconstructionResult(
                success=False, output_path=None, processing_time=0,
                pages_processed=0, elements_processed=0, errors=[str(e)], warnings=[]
            )

    def _process_page(self, original_page, output_doc, page_number: int,
                     layout_data: Dict[str, Any], validated_translations: Dict[str, Any]) -> Dict[str, Any]:
        
        new_page = output_doc.new_page(width=original_page.rect.width, height=original_page.rect.height)
        
        # Copie des images (simplifié, peut être amélioré)
        for img in original_page.get_images(full=True):
            xref = img[0]
            if xref > 0:
                rects = original_page.get_image_rects(xref)
                for rect in rects:
                    try:
                        new_page.insert_image(rect, stream=original_page.parent.extract_image(xref)["image"])
                    except:
                        self.logger.warning(f"Impossible de copier une image sur la page {page_number}")


        elements_on_page = self._get_page_text_elements(page_number, layout_data)
        
        for element_layout in elements_on_page:
            try:
                self._place_translated_text(new_page, element_layout, validated_translations)
            except Exception as e:
                self.logger.warning(f"Erreur placement texte {element_layout['element_id']}: {e}")

        return {'elements_processed': len(elements_on_page), 'warnings': []}

    def _get_page_text_elements(self, page_number: int, layout_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # --- FIX : Logique corrigée pour filtrer les éléments par page ---
        return [
            elem for elem in layout_data.get('element_layouts', [])
            if elem.get('page_number') == page_number
        ]
    
    def _place_translated_text(self, page, element_layout: Dict[str, Any], 
                             validated_translations: Dict[str, Any]):
        element_id = element_layout['element_id']
        translation_data = validated_translations['translations'].get(element_id)
        if not translation_data:
            return

        translated_text = translation_data['translated_text']
        bbox = element_layout['new_bbox']
        font_size = element_layout['new_font_size']
        rect = fitz.Rect(bbox)

        # --- FIX : Utiliser les informations de police et de type de contenu ---
        font_name = self._determine_font_for_element(element_layout)
        align = self._get_text_alignment(element_layout)

        page.insert_textbox(
            rect,
            translated_text,
            fontsize=font_size,
            fontname=font_name,
            align=align
        )

    def _determine_font_for_element(self, element_layout: Dict[str, Any]) -> str:
        # --- FIX : Logique corrigée pour trouver une police de remplacement ---
        original_font = element_layout.get('original_font_name', 'helv')
        
        # Logique de base : essayer de trouver une police système commune
        if 'bold' in original_font.lower():
            return "helv-bold"
        if 'italic' in original_font.lower():
            return "helv-it"
        return "helv" # Helvetica de base

    def _get_text_alignment(self, element_layout: Dict[str, Any]) -> int:
        # --- FIX : Logique corrigée pour déterminer l'alignement ---
        content_type = element_layout.get('content_type', 'paragraph')
        if content_type in ['title', 'subtitle']:
            return fitz.TEXT_ALIGN_CENTER
        return fitz.TEXT_ALIGN_LEFT
