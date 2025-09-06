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
    # [JALON 2] Ajout d'un drapeau pour marquer un saut de ligne forcé après ce span.
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
    final_bbox: Tuple[float, float, float, float] = None
    spans: List[TextSpan] = field(default_factory=list, repr=False)

@dataclass
class PageObject:
    page_number: int
    dimensions: Tuple[float, float]
    text_blocks: List[TextBlock] = field(default_factory=list)
