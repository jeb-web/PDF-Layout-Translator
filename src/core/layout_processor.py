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
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class LayoutIssueType(Enum):
    OVERFLOW_HORIZONTAL = "overflow_horizontal"
    OVERFLOW_VERTICAL = "overflow_vertical"
    FONT_TOO_SMALL = "font_too_small"
    ELEMENT_COLLISION = "element_collision"

class SolutionType(Enum):
    REDUCE_FONT_SIZE = "reduce_font_size"
    EXPAND_CONTAINER = "expand_container"

@dataclass
class LayoutConstraints:
    min_font_size: float = 8.0
    max_font_reduction_percent: float = 20.0
    allow_container_expansion: bool = False

# --- FIX : Ajout de champs pour corriger les bugs anticipés ---
@dataclass
class ElementLayout:
    element_id: str
    page_number: int  # Champ ajouté
    original_bbox: Tuple[float, float, float, float]
    new_bbox: Tuple[float, float, float, float]
    original_font_size: float
    new_font_size: float
    original_font_name: str # Champ ajouté
    content_type: str       # Champ ajouté
    translated_text: str
    expansion_factor: float
    layout_constraints: LayoutConstraints
    issues: List['LayoutIssue'] = field(default_factory=list)
    solutions: List['LayoutSolution'] = field(default_factory=list)

@dataclass
class LayoutIssue:
    issue_type: LayoutIssueType
    severity: float
    description: str

@dataclass
class LayoutSolution:
    solution_type: SolutionType
    confidence: float
    parameters: Dict[str, Any]

class LayoutProcessor:
    def __init__(self, config_manager=None):
        self.logger = logging.getLogger(__name__)
        self.char_width_factor = 0.6
        self.line_height_factor = 1.2
    
    def process_layout(self, validated_translations: Dict[str, Any],
                      original_analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Début du traitement de mise en page")
        
        try:
            element_layouts = self._create_element_layouts(validated_translations, original_analysis_data)
            
            for layout in element_layouts:
                layout.issues = self._detect_layout_issues(layout)
            
            # (La logique de solutions peut être ajoutée ici plus tard)

            return {
                'element_layouts': self._serialize_layouts(element_layouts),
                'quality_metrics': self._calculate_quality_metrics(element_layouts)
            }
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de mise en page: {e}", exc_info=True)
            raise
    
    def _create_element_layouts(self, validated_translations: Dict[str, Any],
                              original_analysis_data: Dict[str, Any]) -> List[ElementLayout]:
        element_layouts = []
        translations = validated_translations['translations']
        
        # Utiliser la bonne clé : 'text_elements' depuis l'analyse complète
        original_elements = {
            elem['id']: elem for elem in original_analysis_data['text_elements']
        }
        
        for element_id, translation_data in translations.items():
            if element_id not in original_elements:
                continue
            
            original_element = original_elements[element_id]
            
            layout = self._create_single_element_layout(element_id, original_element, translation_data)
            element_layouts.append(layout)
        
        return element_layouts

    def _create_single_element_layout(self, element_id: str, original_element: Dict[str, Any],
                                    translation_data: Dict[str, Any]) -> ElementLayout:
        
        original_text = translation_data['original_text']
        translated_text = translation_data['translated_text']
        original_bbox = tuple(original_element['bbox']) # Clé corrigée
        original_font_info = original_element['font_info']
        original_font_size = original_font_info['size']
        
        constraints = LayoutConstraints() # Simplifié pour le moment

        new_font_size = self._calculate_optimal_font_size(
            translated_text, original_bbox, original_font_size, constraints
        )
        
        # --- FIX : Passer les informations complètes à ElementLayout ---
        return ElementLayout(
            element_id=element_id,
            page_number=original_element['page_number'],
            original_bbox=original_bbox,
            new_bbox=original_bbox, # Placeholder, sera ajusté plus tard
            original_font_size=original_font_size,
            new_font_size=new_font_size,
            original_font_name=original_font_info['name'],
            content_type=original_element['content_type'],
            translated_text=translated_text,
            expansion_factor=translation_data['expansion_factor'],
            layout_constraints=constraints
        )

    def _calculate_optimal_font_size(self, text: str, bbox: Tuple[float, float, float, float],
                                   original_font_size: float, constraints: LayoutConstraints) -> float:
        available_width = bbox[2] - bbox[0]
        estimated_width = len(text) * original_font_size * self.char_width_factor
        
        new_font_size = original_font_size
        if estimated_width > available_width and available_width > 0:
            reduction_factor = available_width / estimated_width
            new_font_size = original_font_size * reduction_factor

        max_reduction = original_font_size * (1 - (constraints.max_font_reduction_percent / 100))
        min_allowed_size = max(constraints.min_font_size, max_reduction)
        
        return max(new_font_size, min_allowed_size)

    def _detect_layout_issues(self, layout: ElementLayout) -> List[LayoutIssue]:
        issues = []
        if layout.new_font_size < layout.layout_constraints.min_font_size:
            issues.append(LayoutIssue(
                issue_type=LayoutIssueType.FONT_TOO_SMALL,
                severity=0.8,
                description=f"Police trop petite: {layout.new_font_size:.1f}pt"
            ))
        return issues

    def _serialize_layouts(self, layouts: List[ElementLayout]) -> List[Dict[str, Any]]:
        serialized = []
        for layout in layouts:
            # --- FIX : Inclure les champs supplémentaires dans les données sérialisées ---
            serialized.append({
                'element_id': layout.element_id,
                'page_number': layout.page_number,
                'new_bbox': layout.new_bbox,
                'new_font_size': layout.new_font_size,
                'original_font_name': layout.original_font_name,
                'content_type': layout.content_type
            })
        return serialized

    def _calculate_quality_metrics(self, layouts: List[ElementLayout]) -> Dict[str, Any]:
        # Logique de métriques simplifiée
        return {'overall_quality': 0.9, 'quality_level': 'good'}
