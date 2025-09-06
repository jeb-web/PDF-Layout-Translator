#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Modèle de Données
Définit la structure des objets utilisés pour représenter une page PDF.
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

@dataclass
class TextSpan:
    id: str
    text: str
    font: FontInfo
    bbox: Tuple[float, float, float, float]
    translated_text: str = ""
    forces_line_break: bool = False

@dataclass
class Paragraph:
    id: str
    spans: List[TextSpan] = field(default_factory=list)

@dataclass
class TextBlock:
    id: str
    bbox: Tuple[float, float, float, float]
    paragraphs: List[Paragraph] = field(default_factory=list)
    alignment: int = 0
    
    # Champ final pour la géométrie décidée par le LayoutProcessor
    final_bbox: Tuple[float, float, float, float] = None
    
    # Drapeau pour communiquer la décision du LayoutProcessor au Reconstructor
    is_vertically_extended: bool = False
    
    # Spans aplatis pour un accès facile (ne pas inclure dans la représentation)
    spans: List[TextSpan] = field(default_factory=list, repr=False)

@dataclass
class PageObject:
    page_number: int
    dimensions: Tuple[float, float]
    text_blocks: List[TextBlock] = field(default_factory=list)
