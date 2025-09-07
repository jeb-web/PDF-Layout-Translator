#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Modèle de Données
*** VERSION FINALE ET STABILISÉE v1.3 ***
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

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
    final_bbox: Optional[Tuple[float, float, float, float]] = None

@dataclass
class Paragraph:
    id: str
    spans: List[TextSpan] = field(default_factory=list)
    is_list_item: bool = False
    list_marker_text: str = ""
    text_indent: float = 0.0

@dataclass
class TextBlock:
    id: str
    bbox: Tuple[float, float, float, float]
    paragraphs: List[Paragraph] = field(default_factory=list)
    alignment: int = 0
    final_bbox: Tuple[float, float, float, float] = None
    spans: List[TextSpan] = field(default_factory=list, repr=False)
    available_width: float = 0.0  # NOUVEAU v2.2 : Largeur max disponible calculée par l'analyseur

@dataclass
class PageObject:
    page_number: int
    dimensions: Tuple[float, float]
    text_blocks: List[TextBlock] = field(default_factory=list)
