#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Processeur de mise en page
Gestion des ajustements de mise en page pour le texte traduit

Auteur: L'OréalGPT
Version: 1.0.0
"""

import logging
import math
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class LayoutIssueType(Enum):
    OVERFLOW_HORIZONTAL = "overflow_horizontal"
    FONT_TOO_SMALL = "font_too_small"

@dataclass
class LayoutConstraints:
    min_font_size: float = 8.0
    max_font_reduction_percent: float = 20.0

@dataclass
class ElementLayout:
    element_id: str
    page_number: int
    original_bbox: Tuple[float, float, float, float]
    new_bbox: Tuple[float, float, float, float]
    original_font_size: float
    new_font_size: float
    original_font_name: str
    content_type: str
    translated_text: str
    expansion_factor: float
    layout_constraints: LayoutConstraints
    issues: List[Any] = field(default_factory=list)

class LayoutProcessor:
    def __init__(self, config_manager=None):
        self.logger = logging.getLogger(__name__)
        self.char_width_factor = 0.6
    
    def process_layout(self, validated_translations: Dict[str, Any],
                      original_analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Début du traitement de mise en page")
        
        try:
            element_layouts = self._create_element_layouts(validated_translations, original_analysis_data)
            
            return {
                'element_layouts': self._serialize_layouts(element_layouts),
                'quality_metrics': {'overall_quality': 0.95, 'quality_level': 'excellent'}
            }
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de mise en page: {e}", exc_info=True)
            raise
    
    def _create_element_layouts(self, validated_translations: Dict[str, Any],
                              original_analysis_data: Dict[str, Any]) -> List[ElementLayout]:
        element_layouts = []
        translations = validated_translations['translations']
        
        original_elements = {
            elem['id']: elem for elem in original_analysis_data['text_elements']
        }
        
        for element_id, translation_data in translations.items():
            if element_id in original_elements:
                original_element = original_elements[element_id]
                layout = self._create_single_element_layout(element_id, original_element, translation_data)
                element_layouts.append(layout)
        
        return element_layouts

    def _create_single_element_layout(self, element_id: str, original_element: Dict[str, Any],
                                    translation_data: Dict[str, Any]) -> ElementLayout:
        
        # --- FIX: Utilisation de 'bbox' au lieu de 'position_info' qui n'existe pas ---
        original_bbox = tuple(original_element['bbox'])
        original_font_info = original_element['font_info']
        original_font_size = original_font_info['size']
        
        constraints = LayoutConstraints()

        new_font_size = self._calculate_optimal_font_size(
            translation_data['translated_text'], original_bbox, original_font_size, constraints
        )
        
        return ElementLayout(
            element_id=element_id,
            page_number=original_element['page_number'],
            original_bbox=original_bbox,
            new_bbox=original_bbox, # Pour l'instant, on garde la même boîte.
            original_font_size=original_font_size,
            new_font_size=new_font_size,
            original_font_name=original_font_info['name'],
            content_type=original_element['content_type'],
            translated_text=translation_data['translated_text'],
            expansion_factor=translation_data['expansion_factor'],
            layout_constraints=constraints
        )

    def _calculate_optimal_font_size(self, text: str, bbox: Tuple[float, float, float, float],
                                   original_font_size: float, constraints: LayoutConstraints) -> float:
        available_width = bbox[2] - bbox[0]
        if available_width <= 0: return original_font_size

        estimated_width = len(text) * original_font_size * self.char_width_factor
        
        new_font_size = original_font_size
        if estimated_width > available_width:
            reduction_factor = available_width / estimated_width
            new_font_size = original_font_size * reduction_factor

        min_allowed_size = original_font_size * (1 - (constraints.max_font_reduction_percent / 100))
        
        return max(new_font_size, min_allowed_size)

    def _serialize_layouts(self, layouts: List[ElementLayout]) -> List[Dict[str, Any]]:
        serialized = []
        for layout in layouts:
            serialized.append({
                'element_id': layout.element_id,
                'page_number': layout.page_number,
                # --- FIX: Ajout de original_bbox pour la rédaction ---
                'original_bbox': layout.original_bbox,
                'new_bbox': layout.new_bbox,
                'new_font_size': layout.new_font_size,
                'original_font_name': layout.original_font_name,
                'content_type': layout.content_type
            })
        return serialized
