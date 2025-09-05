#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Modèle de Données
Définit la structure des objets utilisés pour représenter une page PDF.

Auteur: L'OréalGPT
Version: 2.0.0
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any

@dataclass
class FontInfo:
    """Représente les attributs de style d'un segment de texte."""
    name: str
    size: float
    color: str  # Format hexadécimal, ex: "#000000"
    is_bold: bool
    is_italic: bool

@dataclass
class TextSpan:
    """Représente un segment de texte continu avec un style unique."""
    id: str
    text: str
    translated_text: str = ""
    font: FontInfo
    bbox: Tuple[float, float, float, float] # Bbox spécifique au span

@dataclass
class TextBlock:
    """Représente un bloc de texte qui peut contenir plusieurs styles."""
    id: str
    bbox: Tuple[float, float, float, float] # Bbox globale du bloc
    final_bbox: Tuple[float, float, float, float] = None # Bbox après reflow
    spans: List[TextSpan] = field(default_factory=list)

@dataclass
class ImageBlock:
    """Représente une image sur la page."""
    id: str
    bbox: Tuple[float, float, float, float]
    data: bytes

@dataclass
class PageObject:
    """Représente la structure complète d'une seule page."""
    page_number: int
    dimensions: Tuple[float, float] # (width, height)
    text_blocks: List[TextBlock] = field(default_factory=list)
    image_blocks: List[ImageBlock] = field(default_factory=list)
