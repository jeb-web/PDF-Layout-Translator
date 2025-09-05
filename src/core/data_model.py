#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Layout Translator - Modèle de Données
Définit la structure des objets utilisés pour représenter une page PDF.

Auteur: L'OréalGPT
Version: 2.0.1 (Correction de la syntaxe)
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
    # CORRECTION : Les arguments sans valeur par défaut sont maintenant au début.
    id: str
    text: str
    font: FontInfo
    bbox: Tuple[float, float, float, float]
    translated_text: str = "" # L'argument avec valeur par défaut est à la fin.

@dataclass
class TextBlock:
    """Représente un bloc de texte qui peut contenir plusieurs styles."""
    id: str
    bbox: Tuple[float, float, float, float]
    # Les arguments avec valeur par défaut sont bien à la fin.
    final_bbox: Tuple[float, float, float, float] = None
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
    dimensions: Tuple[float, float]
    # Les arguments avec valeur par défaut sont bien à la fin.
    text_blocks: List[TextBlock] = field(default_factory=list)
    image_blocks: List[ImageBlock] = field(default_factory=list)
