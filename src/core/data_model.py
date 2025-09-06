#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Modèle de Données
*** VERSION ÉTENDUE avec méthodes utilitaires ***
"""
from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class FontInfo:
    name: str
    size: float
    color: str
    is_bold: bool
    is_italic: bool
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour sérialisation"""
        return {
            'name': self.name,
            'size': self.size,
            'color': self.color,
            'is_bold': self.is_bold,
            'is_italic': self.is_italic
        }

@dataclass
class TextSpan:
    id: str
    text: str
    font: FontInfo
    bbox: Tuple[float, float, float, float]
    translated_text: str = ""
    forces_line_break: bool = False
    
    def get_effective_text(self) -> str:
        """Retourne le texte traduit si disponible, sinon le texte original"""
        return self.translated_text if self.translated_text.strip() else self.text

@dataclass
class Paragraph:
    id: str
    spans: List[TextSpan] = field(default_factory=list)
    
    def get_combined_text(self) -> str:
        """Combine le texte de tous les spans"""
        return " ".join(span.get_effective_text() for span in self.spans if span.get_effective_text().strip())
    
    def get_representative_font(self) -> FontInfo:
        """Retourne une police représentative du paragraphe"""
        if self.spans:
            return self.spans[0].font
        # Police par défaut si aucun span
        return FontInfo("Arial", 12.0, "#000000", False, False)

@dataclass
class TextBlock:
    id: str
    bbox: Tuple[float, float, float, float]
    paragraphs: List[Paragraph] = field(default_factory=list)
    alignment: int = 0
    final_bbox: Tuple[float, float, float, float] = None
    spans: List[TextSpan] = field(default_factory=list, repr=False)
    
    def get_original_dimensions(self) -> Tuple[float, float]:
        """Retourne largeur et hauteur originales"""
        return (self.bbox[2] - self.bbox[0], self.bbox[3] - self.bbox[1])
    
    def get_final_dimensions(self) -> Tuple[float, float]:
        """Retourne largeur et hauteur finales"""
        if self.final_bbox:
            return (self.final_bbox[2] - self.final_bbox[0], self.final_bbox[3] - self.final_bbox[1])
        return self.get_original_dimensions()

@dataclass
class PageObject:
    page_number: int
    dimensions: Tuple[float, float]
    text_blocks: List[TextBlock] = field(default_factory=list)
    
    def get_stats(self) -> dict:
        """Retourne des statistiques sur la page"""
        total_blocks = len(self.text_blocks)
        total_paragraphs = sum(len(block.paragraphs) for block in self.text_blocks)
        total_spans = sum(len(block.spans) for block in self.text_blocks)
        
        return {
            'page_number': self.page_number,
            'dimensions': self.dimensions,
            'total_blocks': total_blocks,
            'total_paragraphs': total_paragraphs,
            'total_spans': total_spans
        }
